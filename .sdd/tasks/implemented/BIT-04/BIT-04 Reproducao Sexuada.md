# Spec — BIT-04: Reprodução sexuada (colisão de ADULTs com Action_Mate)

**Linear:** N/A (ver memória `bibitinhos-workflow-sem-linear`)
**Risco:** medium
**Camada(s):** Backend (Simulação)

---

## Demanda

Quando duas criaturas `ADULT` colidem fisicamente e ambas têm a saída `Action_Mate` do cérebro ativa, gerar uma nova criatura (`EGG`) via `organic_crossover` + `mutate_genome` (já existentes desde BIT-00) dos genomas dos pais. Hoje nenhum collision handler de reprodução existe — este é o único caminho de criação de novas criaturas além do "Jardim do Éden" (respawn quando população chega a zero).

**Bloqueada por BIT-02** (precisa de `creature.action_mate`/`creature.genome`/`creature.config`, introduzidos lá) — só pode ser implementada depois do merge da BIT-02. Reaproveita o padrão de collision handler introduzido em BIT-03 (não é bloqueante, mas fica mais consistente vir depois).

## Abordagem técnica

Registrar `space.on_collision(COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_CREATURE, begin=...)` em `engine.py`. No callback, validar as condições de acasalamento (ambas ADULT, ambas com `action_mate=True`, sem cooldown ativo, energia mínima), debitar energia dos pais, aplicar cooldown, e instanciar `Creature(engine, x, y, genome=child_genome)` no ponto médio entre os pais — reaproveitando o parâmetro `genome` que BIT-02 adiciona ao `__init__`.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | Novo atributo `self.mate_cooldown = 0.0` no `__init__`; decremento em `update()` |
| `backend/simulation/engine.py` | modificar | Registrar segundo handler `space.on_collision(COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_CREATURE, begin=...)` com a lógica de reprodução |
| `backend/tests/test_reproduction.py` | criar | Testes do collision handler: reprodução ocorre só com condições satisfeitas, filho nasce como EGG, energia dos pais é debitada, cooldown impede reprodução repetida |

## Passos de implementação

> Passo 1 é independente; passo 2 depende de 1 e das mudanças de BIT-02/BIT-03 já mergeadas.

1. **`creature.py`** — no `__init__`, junto dos outros atributos de estado: `self.mate_cooldown = 0.0`. No início de `update(self, dt, engine)` (ou junto do bloco de energia): `self.mate_cooldown = max(0.0, self.mate_cooldown - dt)`.

2. **`engine.py`** — no `__init__`, após o handler de comida (BIT-03):
   ```python
   REPRODUCTION_ENERGY_COST = 30.0
   REPRODUCTION_COOLDOWN = 10.0
   MIN_ENERGY_TO_MATE = 50.0

   def _on_creature_creature_collision(arbiter, space, data):
       shape_a, shape_b = arbiter.shapes
       c1, c2 = shape_a.owner, shape_b.owner
       if not (c1.is_alive and c2.is_alive):
           return True
       if c1.life_stage != LifeStage.ADULT or c2.life_stage != LifeStage.ADULT:
           return True
       if c1.mate_cooldown > 0 or c2.mate_cooldown > 0:
           return True
       if not (c1.action_mate and c2.action_mate):
           return True
       if c1.energy < MIN_ENERGY_TO_MATE or c2.energy < MIN_ENERGY_TO_MATE:
           return True

       c1.energy -= REPRODUCTION_ENERGY_COST
       c2.energy -= REPRODUCTION_ENERGY_COST
       c1.mate_cooldown = REPRODUCTION_COOLDOWN
       c2.mate_cooldown = REPRODUCTION_COOLDOWN

       child_id = self.next_genome_id()
       child_genome = organic_crossover(c1.genome, c2.genome, child_id, c1.config)
       mutate_genome(child_genome, c1.config)

       child_x = (c1.body.position.x + c2.body.position.x) / 2
       child_y = (c1.body.position.y + c2.body.position.y) / 2
       child = Creature(self, child_x, child_y, genome=child_genome)
       self.add_creature(child)
       return True

   self.physics.space.on_collision(
       COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_CREATURE,
       begin=_on_creature_creature_collision,
   )
   ```
   Imports novos no topo de `engine.py`: `from simulation.rtneat_wrapper import organic_crossover, mutate_genome` e `from simulation.creature import LifeStage` (já importa `Creature`).
   Nota: `self` dentro do closure se refere à `SimulationEngine` (a função é definida dentro de `__init__`, fechando sobre `self`) — não precisa passar `engine` como parâmetro extra.
   Validado ao vivo (pymunk 7.2.0): instanciar um novo `Body`/`Shape` e chamar `space.add()` dentro de um callback `begin` funciona sem erro, mesmo com o `space.step()` em andamento.

3. **`backend/tests/test_reproduction.py`**: instanciar `SimulationEngine`, criar duas `Creature` ADULT (`life_stage = LifeStage.ADULT` manualmente no teste) na mesma posição (colidindo), com `action_mate = True` e `energy` suficiente em ambas; chamar `engine.step(dt)` e verificar:
   - `len(engine.creatures)` aumenta em 1 após o step.
   - O novo filho tem `life_stage == LifeStage.EGG`.
   - `energy` de ambos os pais caiu em `REPRODUCTION_ENERGY_COST`.
   - `mate_cooldown` de ambos os pais é `> 0` após o step.
   - Caso negativo: uma das criaturas com `action_mate = False` → nenhum filho nasce.
   - Caso negativo: uma das criaturas `JUVENILE` (não ADULT) → nenhum filho nasce.
   - Caso negativo: `energy < MIN_ENERGY_TO_MATE` em um dos pais → nenhum filho nasce.

## Contratos técnicos

### Backend (Simulação)
- `Creature.mate_cooldown: float` — novo atributo, segundos restantes até poder acasalar de novo.
- Handler `space.on_collision(COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_CREATURE, ...)` — reprodução só ocorre via colisão física real entre duas ADULTs elegíveis.
- Reaproveita `Creature(engine, x, y, genome=...)` do contrato definido em BIT-02.

## Critérios de aceite

- [ ] Duas criaturas ADULT com `action_mate=True`, sem cooldown e com energia suficiente, geram um novo `Creature` em `engine.creatures` ao colidir.
- [ ] O filho nasce com `life_stage == LifeStage.EGG` e um genoma resultante de `organic_crossover` + `mutate_genome` dos pais (não um genoma zero novo).
- [ ] Energia de ambos os pais é debitada em `REPRODUCTION_ENERGY_COST`; nenhum pai fica com energia negativa por causa da reprodução (checar `MIN_ENERGY_TO_MATE` antes de debitar).
- [ ] Cooldown impede reprodução repetida da mesma dupla em colisões consecutivas.
- [ ] Criaturas não-ADULT ou sem `action_mate=True` não reproduzem ao colidir.
- [ ] Simulação completa roda sem erro por alguns segundos com o handler ativo (`manager.py` → Start Tudo).
- [ ] `pytest backend/tests/test_reproduction.py` 100% verde.
- [ ] Nenhuma regressão: `pytest backend/tests/` continua 100% verde.

## Rollback

Remover `self.mate_cooldown`/decremento de `creature.py`; remover o segundo `space.on_collision` e a função `_on_creature_creature_collision` de `engine.py`; deletar `backend/tests/test_reproduction.py`. Sem estado persistente envolvido.
