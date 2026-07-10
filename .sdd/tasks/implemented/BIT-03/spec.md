# Spec — BIT-03: Comer (colisão criatura×comida)

**Linear:** N/A (ver memória `bibitinhos-workflow-sem-linear`)
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

Hoje nada chama `Food.consume()` — criaturas só perdem energia e morrem, comida nunca é "comida" de fato. Implementar o collision handler Pymunk entre `Creature` e `Food`: quando os shapes se tocam, a criatura ganha `food.energy_value` (com cap em `max_energy`) e a comida é consumida (removida do space + marcada inativa).

## Abordagem técnica

Registrar `space.on_collision(COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD, begin=...)` (API real do pymunk 7.2.0 instalado — não existe `add_collision_handler` nesta versão). Isso exige que `Creature.shape` e `Food.shape` tenham `collision_type` definido (hoje só têm `categories`) e uma back-reference (`shape.owner`) para o callback conseguir voltar do `Arbiter` ao objeto Python.

**Independente de BIT-01/BIT-02** — não depende de visão nem de atuadores, pode ser implementada e mergeada a qualquer momento (só toca `creature.py`, `food.py`, `engine.py`, sem sobrepor as áreas que BIT-01/02 mexem além de imports simples).

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | `shape.collision_type = COLLISION_CATEGORY_CREATURE` + `shape.owner = self` no `__init__` |
| `backend/simulation/food.py` | modificar | `shape.collision_type = COLLISION_CATEGORY_FOOD` (usar constante de `physics.py` em vez do número mágico `2` já presente) + `shape.owner = self` no `__init__` |
| `backend/simulation/engine.py` | modificar | `__init__`: registrar `space.on_collision(...)` com callback que transfere energia e consome a comida |
| `backend/tests/test_feeding.py` | criar | Testes do collision handler: colisão transfere energia, comida some do `engine.foods`, cap em `max_energy` respeitado |

## Passos de implementação

> Passo 1 e 2 são independentes entre si; passo 3 depende de 1 e 2.

1. **`creature.py`** — no `__init__`, logo após `self.shape.filter = ...`:
   ```python
   from simulation.physics import COLLISION_CATEGORY_CREATURE  # topo do arquivo
   ...
   self.shape.collision_type = COLLISION_CATEGORY_CREATURE
   self.shape.owner = self
   ```

2. **`food.py`** — no `__init__`, logo após `self.shape.filter = ...`:
   ```python
   from simulation.physics import COLLISION_CATEGORY_FOOD  # topo do arquivo, substitui o numero magico 2
   ...
   self.shape.filter = pymunk.ShapeFilter(categories=COLLISION_CATEGORY_FOOD)
   self.shape.collision_type = COLLISION_CATEGORY_FOOD
   self.shape.owner = self
   ```

3. **`engine.py`** — no `__init__`, após `self.physics = PhysicsEngine()`:
   ```python
   from simulation.physics import COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD

   def _on_creature_food_collision(arbiter, space, data):
       creature_shape, food_shape = arbiter.shapes
       creature = creature_shape.owner
       food = food_shape.owner
       if food.is_active and creature.is_alive:
           creature.energy = min(creature.energy + food.energy_value, creature.max_energy)
           food.consume()
       return True  # deixa a resolucao fisica normal acontecer (elasticity ja configurada nos shapes)

   self.physics.space.on_collision(
       COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD,
       begin=_on_creature_food_collision,
   )
   ```
   Nota: `arbiter.shapes` retorna as shapes na ordem `(collision_type_a, collision_type_b)` conforme registradas — aqui `COLLISION_CATEGORY_CREATURE` é `a`, `COLLISION_CATEGORY_FOOD` é `b`, então `arbiter.shapes[0]` é sempre a criatura e `[1]` sempre a comida.
   `food.consume()` já remove do `space` (com try/except defensivo pré-existente) — validado que `space.remove()` funciona dentro do callback `begin` nesta versão do pymunk (não precisa de `add_post_step_callback`).

4. **`backend/tests/test_feeding.py`**: instanciar `SimulationEngine` real, criar uma `Creature` e uma `Food` na mesma posição (ou posições que se sobrepõem no raio dos shapes), chamar `engine.step(dt)` uma vez e verificar:
   - `creature.energy` aumentou (ou permanece em `max_energy` se já estava no teto).
   - A `Food` some de `engine.foods` após o step (lista já filtra por `is_active`, que `consume()` seta).
   - Cap: criar `Creature` com `energy` próximo de `max_energy` e `Food` com `energy_value` grande — `creature.energy` nunca ultrapassa `max_energy`.
   - Caso negativo: `Creature` e `Food` longe uma da outra — nenhuma mudança de energia, `Food` continua em `engine.foods`.

## Contratos técnicos

### Backend (Simulação)
- `Creature.shape.collision_type = COLLISION_CATEGORY_CREATURE`, `Food.shape.collision_type = COLLISION_CATEGORY_FOOD` (reaproveita constantes de `physics.py`, sem criar novas).
- `Creature.shape.owner -> Creature`, `Food.shape.owner -> Food` (back-reference, usado só internamente pelo handler).
- Nenhuma mudança de contrato público/serialização — `to_dict()` de ambos não muda.

## Critérios de aceite

- [ ] Criatura que colide com comida ganha `food.energy_value` de energia, respeitando o teto `max_energy`.
- [ ] Comida consumida desaparece de `engine.foods` (via `is_active=False` já filtrado em `engine.step()`) e do `space` do Pymunk.
- [ ] Nenhum erro/exceção ao rodar a simulação completa (`manager.py` → Start Tudo) por alguns segundos com o handler registrado.
- [ ] `pytest backend/tests/test_feeding.py` 100% verde.
- [ ] Nenhuma regressão: `pytest backend/tests/` continua 100% verde.

## Rollback

Remover as 2 linhas (`collision_type`/`owner`) de `creature.py` e `food.py`; remover o registro `space.on_collision(...)` e a função `_on_creature_food_collision` de `engine.py`; deletar `backend/tests/test_feeding.py`. Sem estado persistente envolvido.
