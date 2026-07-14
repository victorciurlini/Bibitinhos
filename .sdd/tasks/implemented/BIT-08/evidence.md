# Evidência — BIT-08: Comida com Massa Física

**Data de conclusão:** 2026-07-14

## Demanda atendida

`Food` deixou de ser um corpo `STATIC` (massa infinita, comportamento de parede) e passou a ser um corpo `DYNAMIC` com massa igual a 1% da massa da `Creature` (`FOOD_MASS = CREATURE_MASS * 0.01`), permitindo troca real de momento (ação-reação) ao ser colidida.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | Extraída constante de módulo `CREATURE_MASS = 1.0`; `__init__` usa `mass = CREATURE_MASS` em vez do literal `1.0` |
| `backend/simulation/food.py` | modificado | Novas constantes `FOOD_RADIUS = 5.0` e `FOOD_MASS = CREATURE_MASS * 0.01`; `Food.body` trocado de `pymunk.Body(body_type=STATIC)` para `pymunk.Body(FOOD_MASS, moment)` (dinâmico), com `moment` calculado via `pymunk.moment_for_circle`. Assinaturas públicas (`__init__`, `consume()`, `to_dict()`) inalteradas |
| `backend/tests/test_food_physics.py` | criado | 4 testes: massa da comida é 1% da criatura; comida é deslocada ao colidir com criatura em movimento; comida isolada permanece parada sem força; smoke test de simulação completa com comida dinâmica |

## Resultados dos gates de qualidade

- `import main`: OK — `OK - app importa`
- `pytest backend/tests/`: **57 passed**, 0 failed (53 anteriores + 4 novos de `test_food_physics.py`)
- `npm run test` / `npm run build`: N/A — mudança é 100% backend (`simulation/`), frontend não tocado

## Validação funcional

Backend real subido via `uvicorn main:app --port 8001` (equivalente ao que `manager.py` dispara), com 10 criaturas iniciais e loop de simulação a 30 FPS ativo. Observado por ~13 segundos direto no `backend.log`: nenhum traceback, servidor respondeu `GET /` com `200 OK` normalmente durante a execução. Processo encerrado ao final da validação.

O comportamento físico específico (comida deslocada ao ser colidida vs. comida parada em repouso) é coberto de forma determinística e precisa pelos testes dedicados em `test_food_physics.py`, que rodam o `engine.step()` real (não mocks).

## Como validar

1. `cd backend && venv\Scripts\python.exe -m pytest tests/test_food_physics.py -v` — confirma os 4 testes específicos da feature.
2. Via `manager.py` → "Start Tudo" → abrir o frontend (`http://localhost:5173`) → observar visualmente que, ao uma criatura colidir com um item de comida, o item **se move** com o impacto (não fica "grudado" no lugar como antes).
3. Comida sem nenhuma criatura por perto deve continuar parada normalmente (sem regressão de repouso).
