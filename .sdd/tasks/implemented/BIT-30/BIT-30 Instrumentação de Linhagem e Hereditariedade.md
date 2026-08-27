# Spec — BIT-30: Instrumentação de Linhagem & Hereditariedade

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação) — expõe campos aditivos no payload (API), sem novo endpoint nem mensagem

---

## Demanda

Tornar a evolução **mensurável**. Hoje é impossível saber se as linhagens de bibites de fato
persistem e acumulam aprendizado ao longo de gerações ou se a população só reseta a cada extinção
(o Éden re-semeia genomas zero). Esta task adiciona os rastros mínimos de **hereditariedade** —
profundidade de linhagem, comidas ingeridas e filhos gerados por indivíduo — e os agregados que
revelam a dinâmica evolutiva (`max_generation`, `avg_generation`, `extinctions_total`,
`avg_lifespan`). É o **pré-requisito de medição** antes de qualquer tuning evolutivo (mutação,
gradiente de fitness, hall of fame — BIT-31).

## Abordagem técnica

Cada `Creature` passa a carregar sua **geração** (profundidade de linhagem: `max(gerações dos pais)+1`;
0 para Gen 0 e para a re-semeadura do Éden), além de contadores de `food_eaten` e `children_count`.
O `engine` calcula a geração no nascimento (nos dois ramos de reprodução), incrementa os contadores
nos eventos que já existem (colisão com comida, reprodução, morte) e acumula `extinctions_total` e a
soma de tempos de vida. Os agregados entram estendendo o `compute_metrics()` do **BIT-26** (do qual
esta task depende); nada muda no protocolo — os campos são aditivos no `state_update` e no `to_dict()`.

**Dependência:** BIT-26 (cria `metrics.py`, `compute_metrics()`, `births_total`/`deaths_total`,
`metrics_history`). Se BIT-26 não estiver em `develop` na hora de implementar, criar os campos no
mesmo módulo/pontos previstos por ele, sem duplicar. **Habilita:** BIT-31 (hall of fame usa
`children_count` + geração como proxy de fitness).

**Fora de escopo:** visualização no frontend (o painel de métricas do BIT-26 já existe e pode ganhar
os novos números depois); `%` de indivíduos que chegam a ADULT e taxa de caça bem-sucedida (exigem
cohort tracking — mapeados como refinamento futuro).

## Arquivos a tocar

| Arquivo (path relativo à raiz) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | atributos `generation`/`food_eaten`/`children_count`; param `generation` no `__init__`; campos no `to_dict()` |
| `backend/simulation/engine.py` | modificar | geração no nascimento + `children_count` dos pais; `food_eaten` na colisão; `extinctions_total`; `_lifespan_sum` na morte |
| `backend/simulation/metrics.py` | modificar | estender `compute_metrics()` com os 4 agregados de linhagem (arquivo criado pelo BIT-26) |
| `backend/main.py` | modificar | Gen 0 inicial criada com `generation=0` (explícito; já é o default, garantir na chamada) |
| `backend/tests/test_lineage.py` | criar | testes de geração no nascimento, incrementos e agregados |

## Passos de implementação

1. **`Creature.__init__` (creature.py):** adicionar parâmetro `generation=0` na assinatura
   (`def __init__(self, engine, x=None, y=None, genome=None, generation=0)`) e, junto dos demais
   atributos de estado (perto da linha 148):
   ```python
   self.generation = generation      # profundidade de linhagem (0 = Gen 0 / re-semeadura)
   self.food_eaten = 0               # comidas ingeridas na vida
   self.children_count = 0           # filhos gerados (sexuado + assexuado)
   ```

2. **`Creature.to_dict` (creature.py):** acrescentar ao dict retornado (campos aditivos):
   ```python
   "generation": self.generation,
   "food_eaten": self.food_eaten,
   "children_count": self.children_count,
   ```

3. **`_on_creature_food_collision` (engine.py:54-57):** dentro do `if food.is_active and creature.is_alive:`,
   junto do ganho de energia, `creature.food_eaten += 1`.

4. **Reprodução sexuada (engine.py, bloco ~182-197):** ao criar o filho, calcular a geração e
   incrementar os pais:
   ```python
   a.children_count += 1
   b.children_count += 1
   child_gen = max(a.generation, b.generation) + 1
   ...
   sexual_children.append(Creature(self, cx, cy, genome=child_genome, generation=child_gen))
   ```

5. **Reprodução assexuada (engine.py, bloco ~220-228):** análogo:
   ```python
   creature.children_count += 1
   ...
   asexual_children.append(
       Creature(self, creature.body.position.x, creature.body.position.y,
                genome=child_genome, generation=creature.generation + 1)
   )
   ```

6. **`SimulationEngine.__init__` (engine.py):** novos atributos:
   ```python
   self.extinctions_total = 0
   self._lifespan_sum = 0.0   # soma das idades finais dos mortos; média = _lifespan_sum / deaths_total
   ```

7. **Morte (engine.py, laço de remoção ~279-286):** ao mover uma criatura morta para fora da lista,
   acumular seu tempo de vida: `self._lifespan_sum += c.age` (no ramo `else:` que já chama `c.die()`).
   > Nota: `deaths_total` (contador do BIT-26) é o denominador; garantir que ambos incrementam no mesmo
   > ponto para não divergirem. Se o BIT-26 já conta mortes aqui, apenas somar `c.age` no mesmo laço.

8. **Extinção (engine.py:293):** no ramo `if len(self.creatures) == 0:`, antes/depois de re-semear,
   `self.extinctions_total += 1`. A re-semeadura continua com `Creature(self)` (geração 0) — a
   preservação do genoma é do BIT-31.

9. **`compute_metrics()` (metrics.py, do BIT-26):** acrescentar ao dict retornado:
   ```python
   "max_generation": max((c.generation for c in creatures), default=0),
   "avg_generation": (sum(c.generation for c in creatures) / n) if n else 0.0,
   "extinctions_total": engine.extinctions_total,
   "avg_lifespan": (engine._lifespan_sum / engine.deaths_total) if engine.deaths_total else 0.0,
   ```

10. **`backend/main.py`:** onde a Gen 0 é criada, passar `generation=0` explicitamente (documenta a
    intenção; é o default, então é só clareza — não altera comportamento).

11. **Testes (`backend/tests/test_lineage.py`):** importar constantes/estado dos módulos, nunca hardcodar:
    - `Creature` nova nasce com `generation=0`, `food_eaten=0`, `children_count=0`.
    - Forçar reprodução sexuada (padrão dos testes de reprodução existentes: dois adultos férteis,
      `action_mate`, próximos) → filho com `generation == max(pais)+1` e `children_count` dos pais = 1.
    - Forçar reprodução assexuada → filho com `generation == pai+1`.
    - Colisão com comida (ou chamar o handler) incrementa `food_eaten`.
    - Após uma morte (energia 0 + `step`), `avg_lifespan` > 0 e `_lifespan_sum` reflete a idade do morto.
    - Forçar extinção (esvaziar `engine.creatures` + `step`) incrementa `extinctions_total` e re-semeia 10.
    - `compute_metrics()` inclui os 4 campos novos e continua JSON-serializável (`json.dumps`).

## Contratos técnicos

### Backend (Simulação)
- `Creature.__init__(self, engine, x=None, y=None, genome=None, generation=0)`.
- `Creature`: atributos novos `generation: int`, `food_eaten: int`, `children_count: int`.
- `SimulationEngine`: atributos novos `extinctions_total: int`, `_lifespan_sum: float`.
- `compute_metrics(engine)` ganha as chaves `max_generation: int`, `avg_generation: float`,
  `extinctions_total: int`, `avg_lifespan: float`.

### API/WebSocket
- `state_update` → `metrics` (do BIT-26) ganha os 4 campos acima; e cada item de `creatures[]`
  (`to_dict()`) ganha `generation`, `food_eaten`, `children_count`. **Aditivo — cliente antigo não quebra.**

## Critérios de aceite

- [ ] Filho sexuado nasce com `generation == max(pais)+1`; assexuado com `pai+1`; Gen 0 e re-semeadura do Éden com `0`.
- [ ] `children_count` incrementa nos dois pais (sexuado) e no clonador (assexuado); `food_eaten` incrementa ao comer.
- [ ] `compute_metrics()` reporta `max_generation`, `avg_generation`, `extinctions_total`, `avg_lifespan` coerentes.
- [ ] `to_dict()` expõe `generation`/`food_eaten`/`children_count`; payload segue JSON-serializável.
- [ ] `extinctions_total` incrementa a cada vez que a população zera.
- [ ] `python -c "import main"` OK e `pytest backend/tests/` verde (baseline + novos).

## Rollback

Reverter a branch BIT-30: deletar `backend/tests/test_lineage.py`; restaurar `creature.py`,
`engine.py`, `metrics.py`, `main.py` ao estado anterior. Nenhum contrato público é removido de
terceiros (campos eram aditivos).
