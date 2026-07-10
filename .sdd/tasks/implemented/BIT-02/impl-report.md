## Status
CONCLUIDO

## Passos executados
1. Localizei o spec real em `.sdd/tasks/implementer/BIT-02/BIT-02 Atuadores NEAT.md` (o caminho `spec.md` citado no prompt não existe nesta task) e li o conteúdo completo.
2. Li `backend/simulation/creature.py`, `backend/simulation/engine.py`, `backend/simulation/rtneat_wrapper.py`, `backend/simulation/sensors.py` e os testes existentes (`test_rtneat_wrapper.py`, `test_sensors.py`, `test_simulation.py`) para confirmar o estado atual do código (BIT-00/BIT-01 já mergeados: `load_neat_config`/`create_zero_genome` e `creature.vision`/brain-tick accumulator já presentes).
3. Editei `backend/simulation/creature.py`:
   - `__init__` ganhou parâmetro `genome=None`.
   - Novos atributos: `self.config`, `self.genome`, `self.net` (via `load_neat_config()` + `create_zero_genome(engine.next_genome_id(), self.config)` quando `genome is None`, senão usa o genoma injetado), `self.motor_forward=0.0`, `self.motor_torque=0.0`, `self.action_grab_drop=False`, `self.action_mate=False`, `self.is_holding=False`.
   - Novo método `think(self, engine)`: monta os 16 inputs (9 vision + energy_level + age_degradation + hormonal_level placeholder 0.0 + biological_clock placeholder 0.0 + load_sensor + kinetic_feedback linear + kinetic_feedback angular) e chama `self.net.activate(inputs)`, cacheando os 4 outputs.
   - `update(self, dt, engine)` reescrito: aplica `motor_forward`/`motor_torque` cacheados (impulso + torque) em vez do impulso fixo antigo; custo de energia agora proporcional a `abs(motor_forward)`/`abs(motor_torque)`.
   - Constantes `AGE_DEGRADATION_SCALE=60.0`, `MOTOR_TORQUE_SCALE=20.0`, `KINETIC_LINEAR_NORM=200.0`, `KINETIC_ANGULAR_NORM=10.0` adicionadas no topo do módulo.
4. Editei `backend/simulation/engine.py`:
   - `__init__` ganhou `self._next_genome_id = 0`.
   - Novo método `next_genome_id(self)`: contador monotônico começando em 1.
   - No bloco de brain tick existente (`if self._brain_accumulator >= BRAIN_TICK_INTERVAL:`), adicionada a chamada `creature.think(self)` logo após `creature.vision = compute_vision(creature, self)`.
5. Criei `backend/tests/test_creature_think.py` com 6 testes cobrindo: `think()` roda sem exceção; motor_forward/motor_torque dentro de `[-1,1]`; action_grab_drop/action_mate são `bool`; `update()` após `think()` nunca aumenta energia; custo de energia proporcional à magnitude do motor (comparação entre criatura parada vs. com motores em 1.0); e um teste de integração via `engine.step()` rodando 20 frames com 5 criaturas.
6. Rodei `pytest backend/tests/ -v` — 20 passed (14 pré-existentes + 6 novos), 0 falhas.
7. Smoke test manual: instanciei `SimulationEngine`, adicionei 10 criaturas, rodei 20x `step(1/30.0)` — sem exceções, motores dentro do range esperado, energia decrescendo, action flags booleanas.

## Arquivos modificados
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\simulation\creature.py` — `__init__` com `genome=None` e inicialização do cérebro NEAT; novo método `think()`; `update()` reescrito para usar outputs cacheados da rede em vez de impulso fixo.
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\simulation\engine.py` — `_next_genome_id` + `next_genome_id()`; chamada a `creature.think(self)` no brain tick.
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\tests\test_creature_think.py` — criado (6 testes novos).

## Resultado dos testes
```
20 passed, 6 warnings in 0.43s
```
Todos os testes pré-existentes (`test_rtneat_wrapper.py` 7, `test_sensors.py` 6, `test_simulation.py` 1) continuam verdes, sem regressão. Os 6 novos testes de `test_creature_think.py` passam. Os warnings são `DeprecationWarning` internos do `neat-python` sobre valores default de config (`no_fitness_termination`, `bias_init_type`, etc.), pré-existentes e não relacionados a esta mudança.

Smoke test manual (`SimulationEngine` + 10 criaturas + 20 steps de `1/30.0`): rodou sem exceção, motores em `[-1,1]`, energia decrescendo, `action_grab_drop`/`action_mate` booleanos.

## Problemas encontrados
- O caminho do spec citado no prompt (`.sdd/tasks/implementer/BIT-02/spec.md`) não existe; o arquivo real é `.sdd/tasks/implementer/BIT-02/BIT-02 Atuadores NEAT.md`. Usei esse arquivo como fonte de verdade — conteúdo idêntico ao resumo passado no prompt, sem divergências relevantes.
- Nenhuma outra divergência: implementação seguiu exatamente os trechos de código sugeridos na spec (inputs, `think()`, `update()`, constantes, `next_genome_id()`).
- `main.py` não precisou de alteração, conforme previsto na spec (`Creature(engine)` com `genome=None` continua funcionando).

## Próximos passos (se BLOQUEADO)
N/A — task concluída sem bloqueios.
