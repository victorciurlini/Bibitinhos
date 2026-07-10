## Arquivos relevantes

- `backend/simulation/creature.py` (134 linhas) — `Creature.update()`, `LifeStage` enum, custo de energia atual
- `backend/simulation/engine.py` (141 linhas) — `SimulationEngine.step()`, handlers de colisão (comer BIT-03, reprodução BIT-04)
- `backend/simulation/food.py` — `Food.energy_value` default 20.0
- `backend/tests/test_creature_think.py`, `backend/tests/test_reproduction.py`, `backend/tests/test_feeding.py` — suíte atual (32 testes, todos verdes em `develop`)

## Conteúdo relevante para a demanda

### Estado atual de energia/vida (`creature.py`, pós-BIT-04)

```python
def update(self, dt, engine):
    if not self.is_alive:
        return
    self.age += dt
    self.mate_cooldown = max(0.0, self.mate_cooldown - dt)

    if self.age > 30:
        self.life_stage = LifeStage.ELDER
    elif self.age > 10:
        self.life_stage = LifeStage.ADULT
    elif self.age > 2:
        self.life_stage = LifeStage.JUVENILE

    motor_cost = 0.0
    if self.life_stage != LifeStage.EGG:
        forward_impulse = (self.motor_forward * self.speed * dt, 0)
        self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
        self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE
        motor_cost = abs(self.motor_forward) * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05

    self.energy -= dt * motor_cost
    if self.energy <= 0:
        self.is_alive = False
```

**Gap confirmado**: a ÚNICA fonte de gasto de energia é `motor_cost`, proporcional à magnitude de `motor_forward`/`motor_torque` (saída da rede NEAT, `think()`, BIT-02). Se a rede de uma criatura convergir para saídas próximas de zero, `motor_cost ≈ 0` e a criatura **nunca perde energia por estar viva** — não há metabolismo basal. Isso significa que "comer" (BIT-03) hoje só é relevante para criaturas que efetivamente se movem; uma criatura passiva pode ser tecnicamente imortal sem nunca comer. Não há pressão evolutiva real para aprender a comer.

Também não há nenhuma noção de teto de idade/expectativa de vida — `LifeStage` é só cosmético além do efeito em `motor_cost`/movimento (EGG não move).

### Thresholds de `LifeStage` (idade em segundos simulados, `self.age` acumulado por `dt`)
- `EGG`: `age <= 2`
- `JUVENILE`: `2 < age <= 10` (8s de duração)
- `ADULT`: `10 < age <= 30` (20s de duração)
- `ELDER`: `age > 30` (sem teto — dura enquanto tiver energia)

### `Food.energy_value` (`food.py`)
Default `20.0` por refeição (`Food(engine, x, y, energy_value=20.0)`). `Creature.max_energy = 100.0` (mockado, igual para todas). O handler de colisão criatura×comida (BIT-03, `engine.py`) já transfere isso corretamente, com cap em `max_energy`.

### Onde plugar o metabolismo passivo

`self.life_stage` já é recalculado no início de `update()`, antes do bloco de `motor_cost` — um novo custo por `LifeStage` pode ser somado ao `motor_cost` existente na mesma linha `self.energy -= dt * (...)`, sem tocar em `engine.py`, `think()`, nem no contrato de I/O do NEAT (o input `Energy_Level` em `think()` já lê `self.energy/self.max_energy`, então a rede já vai "sentir" o dreno mais rápido automaticamente — nenhuma mudança necessária lá).

### Impacto em testes existentes — LEVANTAMENTO CRÍTICO

Um metabolismo passivo não-zero para `JUVENILE`/`ADULT`/`ELDER` **quebra 5 asserções de igualdade exata** que hoje assumem que uma criatura parada (motor em zero) não perde energia num único `update()`/`step()`:

1. `backend/tests/test_creature_think.py::test_update_energy_cost_proportional_to_motor_magnitude` — cria uma criatura `ADULT` "quiet" (`motor_forward=motor_torque=0.0`) e afirma `quiet_cost == 0.0` após um `update(1/30.0, engine)`. Com metabolismo ADULT > 0, `quiet_cost` passa a ser `dt * METABOLISM_RATE_BY_STAGE[ADULT]`, não mais zero.
2. `backend/tests/test_reproduction.py::test_adult_pair_with_action_mate_reproduces_on_collision` — `assert c1.energy == 100.0 - REPRODUCTION_ENERGY_COST` após 1 `engine.step(1/30.0)` com ambas `ADULT`. Passa a faltar o termo de metabolismo do step.
3. `test_reproduction.py::test_action_mate_false_prevents_reproduction` — `assert c1.energy == 100.0` / `c2.energy == 100.0` após 1 step, ambas `ADULT`.
4. `test_reproduction.py::test_juvenile_prevents_reproduction` — mesmo padrão (`c1` fica `ADULT`, `c2` vira `JUVENILE`), `assert c1.energy == 100.0` e `assert c2.energy == 100.0`.
5. `test_reproduction.py::test_low_energy_prevents_reproduction` — `assert c1.energy == 100.0` (ADULT) e `assert c2.energy == MIN_ENERGY_TO_MATE - 1.0` (ADULT) após 1 step.

`test_feeding.py` (3 testes com asserção exata de energia) **não é afetado**: todas as `Creature` nesses testes ficam em `LifeStage.EGG` (idade 0, um único step de `1/30s` não cruza o limiar de 2s) — se `EGG` continuar com custo/metabolismo zero (precedente já estabelecido em BIT-02 para `motor_cost`), esses testes seguem passando sem alteração.

## O que precisa ser feito

1. **`backend/simulation/creature.py`**: adicionar uma constante `METABOLISM_RATE_BY_STAGE` (dict `LifeStage -> float`, energia/segundo) e somar `metabolism_cost = METABOLISM_RATE_BY_STAGE[self.life_stage]` ao `motor_cost` existente antes de `self.energy -= dt * (...)`. `EGG` mantém custo total zero (motor + metabolismo), preservando o comportamento já testado de BIT-02/BIT-03.
2. **Atualizar as 5 asserções listadas acima** para contabilizar o termo de metabolismo (usar `pytest.approx` para evitar brittleness de ponto flutuante ao combinar `dt * taxa` calculado independentemente no teste).
3. **Novos testes** cobrindo: metabolismo passivo mesmo com motor zerado, taxa cresce por estágio (`ELDER > ADULT > JUVENILE > EGG == 0`), e que comer (handler já existente de BIT-03) compensa/estende a sobrevivência de uma criatura que só perde energia por metabolismo (teste de integração simples via `engine.step()`).
4. **Nenhuma mudança em `engine.py`, `food.py`, `rtneat_wrapper.py`, frontend** — escopo fica inteiramente em `creature.py` + testes, conforme decisão do developer (sem UI nova nesta task).

## Perguntas em aberto

Nenhuma — decisões de mecânica (metabolismo passivo por `LifeStage`, `ELDER` com degradação acelerada, sem UI nova) já confirmadas com o developer antes desta pesquisa.
