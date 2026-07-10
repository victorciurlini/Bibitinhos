## Status
CONCLUIDO

## Passos executados
1. Li `spec.md`, `creature.py`, `food.py`, `engine.py`, `physics.py` (estado atual antes de editar).
2. Confirmei na instalação real (`backend/venv/Lib/site-packages/pymunk`, versão 7.2.0) que:
   - `Space.on_collision(...)` existe (não há `add_collision_handler`).
   - `Arbiter.shapes` documenta e retorna as shapes "in the order that they were defined in the collision handler associated with this arbiter" — confirma que `arbiter.shapes[0]` é sempre a criatura (`collision_type_a`) e `[1]` sempre a comida (`collision_type_b`), como a spec assumia.
   - `pymunk.Shape` não tem `__slots__`, então `shape.owner = self` funciona normalmente.
3. Rodei a suíte de testes antes de qualquer edição: 21 passed.
4. Editei `creature.py`: import de `COLLISION_CATEGORY_CREATURE` de `simulation.physics` + `self.shape.collision_type` / `self.shape.owner` no `__init__`, logo após `self.shape.filter = ...`.
5. Editei `food.py`: import de `COLLISION_CATEGORY_FOOD` de `simulation.physics`, troquei o número mágico `2` do `ShapeFilter` pela constante, + `self.shape.collision_type` / `self.shape.owner` no `__init__`.
6. Editei `engine.py`: import de `COLLISION_CATEGORY_CREATURE`/`COLLISION_CATEGORY_FOOD`; registrei `self.physics.space.on_collision(...)` no `__init__` com a função `_on_creature_food_collision` (definida como closure dentro do `__init__`, igual ao código validado na spec) que transfere energia (com cap em `max_energy`) e chama `food.consume()`.
7. Criei `backend/tests/test_feeding.py` com 4 testes: transferência de energia + comida some de `engine.foods`, cap em `max_energy`, caso negativo (longe, nada muda), smoke test (20 criaturas... na verdade 10 criaturas + 15 comidas aglomeradas, 20 steps, sem exceção).
8. Rodei a suíte completa: 25 passed (21 antigos + 4 novos), 0 falhas.
9. Smoke test manual adicional (script inline fora do pytest): `SimulationEngine` real, 20 criaturas + 30 comidas aglomeradas em (1000,1000), 200 steps de `engine.step(1/30)` sem exceção; confirmei que `foods` diminuiu (comida sendo consumida) e que as energias das criaturas variaram (ganho por comida líquido do custo de motor), e que a contagem de bodies/shapes no space ficou consistente (sem vazamento de shapes órfãs).

## Arquivos modificados
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\simulation\creature.py` — import de `COLLISION_CATEGORY_CREATURE`; `self.shape.collision_type` e `self.shape.owner` adicionados no `__init__`.
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\simulation\food.py` — import de `COLLISION_CATEGORY_FOOD`; número mágico `2` do `ShapeFilter` substituído pela constante; `self.shape.collision_type` e `self.shape.owner` adicionados no `__init__`.
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\simulation\engine.py` — import das duas constantes de `physics.py`; registro de `space.on_collision(...)` com handler `_on_creature_food_collision` no `__init__` de `SimulationEngine`.
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\tests\test_feeding.py` (novo) — 4 testes do collision handler.

## Resultado dos testes
```
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
...
backend/tests/test_feeding.py::test_collision_transfers_energy_and_consumes_food PASSED
backend/tests/test_feeding.py::test_energy_gain_capped_at_max_energy PASSED
backend/tests/test_feeding.py::test_far_apart_creature_and_food_do_not_interact PASSED
backend/tests/test_feeding.py::test_smoke_full_simulation_runs_without_exception_with_feeding_active PASSED
...
======================= 25 passed, 6 warnings in 0.44s ========================
```
Todos os 21 testes pré-existentes continuam verdes; os 4 novos testes de `test_feeding.py` também passam. Warnings são pré-existentes (DeprecationWarning do `neat.config`, não relacionados a esta mudança).

Smoke test manual adicional (fora do pytest, script inline): 20 criaturas + 30 comidas aglomeradas, 200 steps — sem exceção, `foods` reduziu de 30 para 7 (consumo real acontecendo), energias das criaturas variaram de forma consistente com ganho por comida e custo de motor, contagem de bodies/shapes no `space` consistente.

## Problemas encontrados
Nenhum bloqueio. Um único ponto de decisão (não-bloqueante): a spec mostrava a função `_on_creature_food_collision` como closure definida dentro do `__init__` de `SimulationEngine` — segui exatamente essa estrutura (em vez de extrair a função para o nível de módulo, que também funcionaria) para não divergir da implementação já validada na spec.

## Próximos passos (se BLOQUEADO)
N/A — task concluída.
