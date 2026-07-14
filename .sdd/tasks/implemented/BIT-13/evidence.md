# Evidência — BIT-13: Visão Ponderada por Fome e Energia

**Data de conclusão:** 2026-07-14

## Demanda atendida

Os 9 cones de visão (`compute_vision()`) deixaram de ser binários (0.0/1.0, sem tipo) e passaram a carregar sinal com prioridade instintiva: positivo para comida (magnitude = fome da própria criatura), negativo para outra criatura (magnitude = energia, só se a observadora for `ADULT`), zero para vazio. A distinção usa `shape.collision_type`, o que também corrige de graça um bug latente em que paredes do mapa ativavam cones perto das bordas. Nenhuma mudança de topologia do NEAT (`num_inputs` continua 16).

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/sensors.py` | modificado | `compute_vision()` reescrita: filtra shapes por `shape.collision_type` (`COLLISION_CATEGORY_FOOD`/`COLLISION_CATEGORY_CREATURE`, ignorando paredes/shapes sem tipo), calcula `hunger = 1 - energy/max_energy` e `mate_drive = energy/max_energy` (só se `life_stage == ADULT`), e retorna sinal `[-1.0, 1.0]` por setor com comida tendo precedência sobre criatura no mesmo setor. |
| `backend/simulation/rtneat_wrapper.py` | modificado | Docstring do contrato de I/O atualizada: linha `0-8 Visual_Sectors` agora descreve a nova semântica de sinal (positivo=comida/fome, negativo=criatura/energia se ADULT, 0=vazio). `num_inputs`/`num_outputs` e `neat_config.ini` não foram tocados. |
| `backend/tests/test_sensors.py` | modificado | Testes atualizados para a nova semântica: `test_food_directly_ahead_activates_cone_zero` agora seta `energy = 0.0` (fome=1.0); novo `test_food_directly_ahead_but_creature_full_energy_gives_no_signal` (saciada = sem sinal); `test_creature_directly_behind_activates_opposite_cone` agora seta `ADULT` + `energy=100.0` (sinal `-1.0`); novo `test_creature_directly_behind_but_not_adult_gives_no_signal`; novo `test_food_and_creature_same_sector_food_wins` (precedência); novo `test_wall_near_map_edge_does_not_activate_any_cone` (regressão do bug de paredes). Testes de raio/self-detection/tick-rate mantidos inalterados na estrutura. |

## Resultados dos gates de qualidade

- `import main`: OK — "OK - app importa"
- `pytest tests/`: **61 passed**, 0 failed (6 warnings de depreciação do neat-python, pré-existentes, não relacionados a esta mudança)
- `neat_config.ini`: confirmado intocado (`num_inputs = 16`)
- Frontend: não tocado por esta task (nenhum `npm run test`/`build` executado, conforme instrução)

## Validação funcional

Backend subido isoladamente via `uvicorn main:app --port 8099` (porta 8001 já estava ocupada por outra sessão paralela ativa no repositório — não foi tocada). Confirmado:
- `GET /` respondeu `200 {"status":"Bibitinhos Backend is Running!"}`.
- `simulation_loop()` (que roda `engine.step()` a 30 FPS chamando `compute_vision()` para as 10 criaturas iniciais, independente de conexão websocket) rodou por ~13s sem nenhum traceback no log de erro — o `except Exception` em `main.py` que faz `traceback.print_exc()` não disparou nenhuma vez.
- Processo próprio derrubado ao final (`Stop-Process`); processo de outra sessão na porta 8001 não foi tocado.

## Como validar

1. `cd backend && venv\Scripts\python.exe -m pytest tests/test_sensors.py -v` — conferir os 11 casos, incluindo os novos de precedência comida/criatura e parede.
2. Manualmente: com `manager.py`, iniciar a simulação e observar via `backend.log` que não há tracebacks contínuos vindos de `compute_vision`/`engine.step`.
3. Interativo (REPL): criar uma `Creature` com `energy=0.0`, posicionar `Food` à frente (`angle=0`, `dx=+50,dy=0`) e chamar `compute_vision(creature, engine)` — esperar `vision[0] ≈ 1.0`. Repetir com `energy=100.0` — esperar `vision[0] == 0.0` (saciada não "vê" comida como prioridade).
