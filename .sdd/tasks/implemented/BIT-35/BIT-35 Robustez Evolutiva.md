# Spec — BIT-35: Robustez Evolutiva

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação)

---

## Demanda

Bibites se extinguem com muita frequência e a evolução avança lentamente. A investigação
do codebase e pesquisa em literatura de ALife identificou três causas raiz:

1. **Ecossistema hostil demais**: oásis curtos (TTL 15-40s), comida escassa (cap 110),
   metabolismo alto (ADULT 0.8 E/s + idle penalty 1.2 E/s) → população colapsa antes de
   conseguir se reproduzir.

2. **Reprodução sexuada rara**: raio 150px em mapa 1400×1400, custo 30 E/pai, cooldown 10s,
   fertilidade exige energy ≥ 60. Muitas barreiras simultâneas para um evento que deveria
   ser frequente.

3. **Rede de segurança fraca**: Eden só ativa com pop < 10 (tarde demais); Hall of Fame tem
   12 slots e pontuação ignora habilidade de caçar comida; respawn gera apenas 10 clones.

---

## Abordagem técnica

Três clusters de mudanças independentes, todos dentro de `backend/simulation/`:

- **Cluster A — Rebalancear ecossistema**: ajustar constantes de energia, metabolismo, oásis
  e reprodução nos arquivos `creature.py`, `oasis.py` e `engine.py`; sincronizar defaults
  em `params.py` (nota: `get_params()` não é chamado em `step()`, só em `get_state()` —
  as constantes hardcoded são o que de fato governa a simulação).

- **Cluster B — Fortalecer rede de segurança**: aumentar Hall of Fame (12→20), ampliar
  respawn do Eden (10→15 clones), antecipar o gatilho (pop < 15), incluir `food_eaten`
  na pontuação do HoF.

- **Cluster C — Pressão adaptativa de população**: novo mecanismo em `engine.step()` que
  multiplica `OASIS_FOOD_SPAWN_CHANCE` por um fator baseado no tamanho da população atual,
  criando homeostase ecológica (pop baixa → comida abundante; pop alta → seleção natural).

Sem alterações no contrato de I/O do NEAT, no protocolo WebSocket ou em frontend.

---

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | Ajustar STARTING_ENERGY, IDLE_PENALTY_RATE, FERTILITY_ENERGY_THRESHOLD, METABOLISM_RATE_BY_STAGE[ADULT] |
| `backend/simulation/oasis.py` | modificar | Ajustar OASIS_TTL_MIN/MAX, MAX_TOTAL_FOOD, OASIS_FOOD_SPAWN_CHANCE, EDEN_POPULATION_THRESHOLD |
| `backend/simulation/engine.py` | modificar | Ajustar HALL_OF_FAME_SIZE, MATING_RADIUS, REPRODUCTION_ENERGY_COST, REPRODUCTION_COOLDOWN; adicionar adaptive food multiplier; adicionar food_eaten ao HoF score; ampliar respawn Eden |
| `backend/simulation/params.py` | modificar | Sincronizar defaults dos parâmetros que possuem espelho em params.py |
| `backend/tests/test_ecosystem_balance.py` | criar | Testes dos novos limiares e mecanismo adaptativo |

---

## Passos de implementação

### Passo 1 — Ajustes em `creature.py`

Alterar as seguintes constantes no topo do arquivo:

```python
# Antes:
STARTING_ENERGY = 75.0
IDLE_PENALTY_RATE = 1.2
FERTILITY_ENERGY_THRESHOLD = 60.0
METABOLISM_RATE_BY_STAGE = {
    LifeStage.EGG: 0.0,
    LifeStage.JUVENILE: 0.3,
    LifeStage.ADULT: 0.8,
    LifeStage.ELDER: 2.0,
}

# Depois:
STARTING_ENERGY = 85.0       # +10 E de margem para encontrar a primeira comida
IDLE_PENALTY_RATE = 0.8      # era 1.2: menos punitivo, ainda desfavorece ficar parada
FERTILITY_ENERGY_THRESHOLD = 50.0  # era 60.0: mais criaturas alcançam o limiar de fertilidade
METABOLISM_RATE_BY_STAGE = {
    LifeStage.EGG: 0.0,
    LifeStage.JUVENILE: 0.3,
    LifeStage.ADULT: 0.5,    # era 0.8: adulto sobrevive mais tempo sem comida
    LifeStage.ELDER: 2.0,    # inalterado: velhice continua sendo pressão real
}
```

### Passo 2 — Ajustes em `oasis.py`

```python
# Antes:
MAX_ACTIVE_OASES = 6
OASIS_TTL_MIN = 15.0
OASIS_TTL_MAX = 40.0
OASIS_FOOD_SPAWN_CHANCE = 0.18
MAX_TOTAL_FOOD = 110
EDEN_POPULATION_THRESHOLD = 10

# Depois:
MAX_ACTIVE_OASES = 6                # inalterado
OASIS_TTL_MIN = 25.0               # era 15.0: oásis duram mais
OASIS_TTL_MAX = 60.0               # era 40.0: oásis mais persistentes
OASIS_FOOD_SPAWN_CHANCE = 0.22     # era 0.18: ligeiro aumento de densidade
MAX_TOTAL_FOOD = 150               # era 110: mais comida no mapa
EDEN_POPULATION_THRESHOLD = 15     # era 10: seguro ativa mais cedo
```

### Passo 3 — Ajustes em `engine.py` (constantes)

```python
# Antes:
MATING_RADIUS = 150.0
REPRODUCTION_ENERGY_COST = 30.0
REPRODUCTION_COOLDOWN = 10.0
HALL_OF_FAME_SIZE = 12

# Depois:
MATING_RADIUS = 200.0             # era 150: encontros mais frequentes
REPRODUCTION_ENERGY_COST = 20.0  # era 30: mais oportunidades pós-parto
REPRODUCTION_COOLDOWN = 6.0      # era 10: menos tempo entre acasalamentos
HALL_OF_FAME_SIZE = 20           # era 12: mais diversidade genética preservada
```

### Passo 4 — Hall of Fame com food_eaten (engine.py)

Atualizar `_record_in_hall_of_fame()` para incluir `food_eaten` na pontuação.
Adicionar nova constante:

```python
HALL_OF_FAME_FOOD_WEIGHT = 1.0  # peso por comida ingerida (equivale a ~2s de vida)
```

Alterar o cálculo do score:
```python
# Antes:
score = creature.age + HALL_OF_FAME_CHILDREN_WEIGHT * creature.children_count

# Depois:
score = (creature.age
         + HALL_OF_FAME_CHILDREN_WEIGHT * creature.children_count
         + HALL_OF_FAME_FOOD_WEIGHT * creature.food_eaten)
```

### Passo 5 — Respawn do Eden ampliado (engine.py)

No bloco `if len(self.creatures) == 0:` (extinção total), mudar de 10 para 15 clones:

```python
# Antes:
if self.hall_of_fame:
    for child in self._spawn_from_hall_of_fame(10):
        ...
else:
    for _ in range(10):
        ...

# Depois:
if self.hall_of_fame:
    for child in self._spawn_from_hall_of_fame(15):
        ...
else:
    for _ in range(15):
        ...
```

### Passo 6 — Pressão adaptativa de população (engine.py — novo mecanismo)

Adicionar constantes após as constantes existentes do engine:

```python
# Pressão adaptativa de população (BIT-35): multiplica food spawn chance pela população atual.
# pop < LOW_POP_THRESHOLD  → comida abundante (suporte à recuperação pós-extinção)
# pop > HIGH_POP_THRESHOLD → comida escassa (seleção natural mais intensa)
LOW_POP_FOOD_THRESHOLD = 15   # criaturas
HIGH_POP_FOOD_THRESHOLD = 50  # criaturas
FOOD_MULTIPLIER_LOW_POP = 1.5
FOOD_MULTIPLIER_HIGH_POP = 0.75
```

Na função `step()`, antes do loop de spawn de comida (atualmente linha ~303),
adicionar o cálculo do multiplicador e usá-lo no `random.random()`:

```python
# Multiplicador adaptativo de comida baseado na população
pop = len(self.creatures)
if pop < LOW_POP_FOOD_THRESHOLD:
    _food_mult = FOOD_MULTIPLIER_LOW_POP
elif pop > HIGH_POP_FOOD_THRESHOLD:
    _food_mult = FOOD_MULTIPLIER_HIGH_POP
else:
    _food_mult = 1.0

if len(self.foods) < MAX_TOTAL_FOOD:
    for oasis in self.oases:
        food_in_oasis = sum(
            1 for f in self.foods
            if (f.body.position.x - oasis.x) ** 2 + (f.body.position.y - oasis.y) ** 2
               <= oasis.radius ** 2
        )
        if food_in_oasis < oasis.food_cap and random.random() < OASIS_FOOD_SPAWN_CHANCE * _food_mult:
            fx, fy = oasis.random_point_inside()
            fx = max(0, min(self.width, fx))
            fy = max(0, min(self.height, fy))
            self.add_food(Food(self, fx, fy))
            if len(self.foods) >= MAX_TOTAL_FOOD:
                break
```

### Passo 7 — Sincronizar `params.py`

Atualizar os defaults dos parâmetros que têm espelho em `params.py` para refletir os novos
valores (cosmético: a simulação usa as constantes hardcoded, mas a UI deve mostrar os valores
corretos como ponto de partida para tuning):

| Parâmetro em params.py | Valor anterior | Novo valor |
|---|---|---|
| `idle_penalty_rate` | 1.2 | 0.8 |
| `fertility_energy_threshold` | 60.0 | 50.0 |
| `metabolism_adult` | 0.8 | 0.5 |
| `oasis_food_spawn_chance` | 0.18 | 0.22 |
| `oasis_ttl_min` | 15.0 | 25.0 |
| `oasis_ttl_max` | 40.0 | 60.0 |
| `max_total_food` | 110 | 150 |
| `mating_radius` | 150.0 | 200.0 |
| `reproduction_energy_cost` | 30.0 | 20.0 |
| `reproduction_cooldown` | 10.0 | 6.0 |

### Passo 8 — Testes em `backend/tests/test_ecosystem_balance.py`

Criar arquivo com testes para os novos comportamentos:

```python
# Teste 1: Eden ativa com pop < 15
# Teste 2: Eden NÃO ativa com pop == 15
# Teste 3: HoF preserva 20 entradas (não 12)
# Teste 4: score do HoF inclui food_eaten
# Teste 5: multiplicador LOW_POP (pop=10) → multiplier=1.5
# Teste 6: multiplicador HIGH_POP (pop=60) → multiplier=0.75
# Teste 7: multiplicador neutro (pop=30) → multiplier=1.0
# Teste 8: respawn do Eden gera 15 criaturas (não 10)
# Teste 9: STARTING_ENERGY == 85.0 em nova criatura
# Teste 10: FERTILITY_ENERGY_THRESHOLD == 50.0 (criatura vira fértil com 51 E)
```

Para os testes de multiplicador, como o multiplicador é calculado inline em `step()`,
a abordagem mais limpa é extrair uma função pura:

```python
# Em engine.py — adicionar função pura testável:
def _compute_food_multiplier(population: int) -> float:
    if population < LOW_POP_FOOD_THRESHOLD:
        return FOOD_MULTIPLIER_LOW_POP
    elif population > HIGH_POP_FOOD_THRESHOLD:
        return FOOD_MULTIPLIER_HIGH_POP
    return 1.0
```

E usar `_compute_food_multiplier(pop)` em `step()` em vez do bloco if/elif inline.

---

## Contratos técnicos

### Backend (Simulação)

**Constantes alteradas em `creature.py`:**
- `STARTING_ENERGY`: 75.0 → 85.0
- `IDLE_PENALTY_RATE`: 1.2 → 0.8
- `FERTILITY_ENERGY_THRESHOLD`: 60.0 → 50.0
- `METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]`: 0.8 → 0.5

**Constantes alteradas em `oasis.py`:**
- `OASIS_TTL_MIN`: 15.0 → 25.0
- `OASIS_TTL_MAX`: 40.0 → 60.0
- `OASIS_FOOD_SPAWN_CHANCE`: 0.18 → 0.22
- `MAX_TOTAL_FOOD`: 110 → 150
- `EDEN_POPULATION_THRESHOLD`: 10 → 15

**Constantes alteradas em `engine.py`:**
- `MATING_RADIUS`: 150.0 → 200.0
- `REPRODUCTION_ENERGY_COST`: 30.0 → 20.0
- `REPRODUCTION_COOLDOWN`: 10.0 → 6.0
- `HALL_OF_FAME_SIZE`: 12 → 20

**Constantes novas em `engine.py`:**
- `HALL_OF_FAME_FOOD_WEIGHT = 1.0`
- `LOW_POP_FOOD_THRESHOLD = 15`
- `HIGH_POP_FOOD_THRESHOLD = 50`
- `FOOD_MULTIPLIER_LOW_POP = 1.5`
- `FOOD_MULTIPLIER_HIGH_POP = 0.75`

**Função nova em `engine.py`:**
```python
def _compute_food_multiplier(population: int) -> float: ...
```

**Score do Hall of Fame (engine.py `_record_in_hall_of_fame`):**
```
score = age + HALL_OF_FAME_CHILDREN_WEIGHT * children_count + HALL_OF_FAME_FOOD_WEIGHT * food_eaten
```

**Respawn Eden (engine.py `step`):**
- Extinção total: spawn de 15 criaturas (era 10)

---

## Critérios de aceite

- [ ] `STARTING_ENERGY == 85.0` em `creature.py`
- [ ] `IDLE_PENALTY_RATE == 0.8` em `creature.py`
- [ ] `FERTILITY_ENERGY_THRESHOLD == 50.0` em `creature.py`
- [ ] `METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] == 0.5` em `creature.py`
- [ ] `OASIS_TTL_MIN == 25.0`, `OASIS_TTL_MAX == 60.0` em `oasis.py`
- [ ] `MAX_TOTAL_FOOD == 150` em `oasis.py`
- [ ] `EDEN_POPULATION_THRESHOLD == 15` em `oasis.py`
- [ ] `MATING_RADIUS == 200.0`, `REPRODUCTION_ENERGY_COST == 20.0`, `REPRODUCTION_COOLDOWN == 6.0` em `engine.py`
- [ ] `HALL_OF_FAME_SIZE == 20` em `engine.py`
- [ ] `_compute_food_multiplier(10) == 1.5` (ou 1.5 no inline, testável)
- [ ] `_compute_food_multiplier(60) == 0.75`
- [ ] `_compute_food_multiplier(30) == 1.0`
- [ ] Score do HoF inclui `food_eaten × HALL_OF_FAME_FOOD_WEIGHT`
- [ ] Eden respawn gera 15 criaturas
- [ ] `pytest tests/` 100% verde (sem quebrar testes existentes)

---

## Rollback

Reverter os valores das constantes alteradas nos 4 arquivos para os valores anteriores.
Não há schema de banco de dados nem migração — o estado da simulação é em memória e
reinicia automaticamente.
