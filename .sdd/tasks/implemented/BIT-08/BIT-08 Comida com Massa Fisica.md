# Spec — BIT-08: Comida com Massa Física

**Linear:** N/A
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

`Food` hoje é um corpo `STATIC` do Pymunk (massa infinita) — na prática se comporta como uma parede: uma criatura que colide com ela sofre a resposta física normal, mas a comida nunca é deslocada, sem troca real de momento. O developer quer física de ação-reação de verdade, com a comida tendo massa proporcional a 1% da massa da criatura.

## Abordagem técnica

Trocar `Food.body` de `STATIC` para um corpo `DYNAMIC` leve (`mass = 1% da massa da Creature`), extraindo a massa da `Creature` como constante de módulo (`CREATURE_MASS`) para expressar essa relação de forma explícita e sem número mágico duplicado. Nenhuma outra parte do código assume que a posição da comida é fixa entre steps (verificado em `engine.py`/`test_oasis.py`/`test_feeding.py` — ver `research/simulation-core.md`).

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | Extrair `CREATURE_MASS = 1.0` como constante de módulo; usar no `__init__` |
| `backend/simulation/food.py` | modificar | `Food.body` passa a ser `DYNAMIC` com `FOOD_MASS = CREATURE_MASS * 0.01` |
| `backend/tests/test_food_physics.py` | criar | Testes: massa da comida é 1% da da criatura; comida é deslocada ao ser colidida (não fica parada como parede); comida sem nenhuma força permanece parada |

## Passos de implementação

1. **`creature.py`** — no topo do módulo, junto das outras constantes:
   ```python
   CREATURE_MASS = 1.0
   ```
   No `__init__`, trocar `mass = 1.0` por `mass = CREATURE_MASS`.

2. **`food.py`**:
   ```python
   import pymunk

   from simulation.physics import COLLISION_CATEGORY_FOOD
   from simulation.creature import CREATURE_MASS

   FOOD_RADIUS = 5.0
   FOOD_MASS = CREATURE_MASS * 0.01  # 1% da massa da Creature: acao-reacao real, nao se comporta como parede

   class Food:
       def __init__(self, engine, x, y, energy_value=20.0):
           self.engine = engine
           self.energy_value = energy_value
           self.is_active = True

           moment = pymunk.moment_for_circle(FOOD_MASS, 0, FOOD_RADIUS)
           self.body = pymunk.Body(FOOD_MASS, moment)
           self.body.position = (x, y)

           self.shape = pymunk.Circle(self.body, FOOD_RADIUS)
           self.shape.elasticity = 0.5
           self.shape.friction = 0.5
           self.shape.filter = pymunk.ShapeFilter(categories=COLLISION_CATEGORY_FOOD)
           self.shape.collision_type = COLLISION_CATEGORY_FOOD
           self.shape.owner = self

           if hasattr(engine, 'physics') and engine.physics is not None:
               engine.physics.space.add(self.body, self.shape)
       # consume() e to_dict() inalterados
   ```
   Import de `creature.py` em `food.py` não cria ciclo (`creature.py` não importa `food.py`).

3. **`backend/tests/test_food_physics.py`** (criar):
   - `FOOD_MASS == pytest.approx(CREATURE_MASS * 0.01)`.
   - Uma `Creature` com velocidade alta colidindo com uma `Food` parada (via `engine.step()`) faz a comida sair da posição original (`food.body.position` muda além de uma tolerância pequena) — comida não se comporta mais como parede.
   - Uma `Food` isolada (sem nenhuma criatura no engine), após vários `engine.step()`, permanece exatamente na posição de spawn (sem força, sem movimento — comportamento herdado, não regressão).
   - Smoke test: `SimulationEngine` real com criaturas + comida próximas, várias dezenas de steps, sem exceção.

4. Rodar a suíte completa (`backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`) e confirmar 100% verde (hoje 53 testes + novos).

## Contratos técnicos

### Backend (Simulação)
- Nova constante em `creature.py`: `CREATURE_MASS: float = 1.0`.
- Novas constantes em `food.py`: `FOOD_RADIUS: float = 5.0`, `FOOD_MASS: float = CREATURE_MASS * 0.01`.
- `Food.body` passa de `pymunk.Body(body_type=STATIC)` para `pymunk.Body(FOOD_MASS, moment)` (dinâmico). Nenhuma mudança de assinatura pública (`Food.__init__`, `consume()`, `to_dict()` inalterados).

## Critérios de aceite

- [ ] `FOOD_MASS` é exatamente 1% de `CREATURE_MASS`.
- [ ] Comida colidida por uma criatura em movimento é fisicamente deslocada (não fica mais "grudada" como parede).
- [ ] Comida sem nenhuma criatura por perto permanece parada (sem regressão de comportamento em repouso).
- [ ] Consumo de energia ao colidir continua funcionando exatamente como antes (BIT-03 intocado).
- [ ] `pytest backend/tests/test_food_physics.py` 100% verde.
- [ ] Nenhuma regressão: suíte completa 100% verde.

## Rollback

Reverter `food.py` para `pymunk.Body(body_type=pymunk.Body.STATIC)` sem massa/moment; remover `CREATURE_MASS` de `creature.py` (voltar a `mass = 1.0` inline); deletar `backend/tests/test_food_physics.py`.
