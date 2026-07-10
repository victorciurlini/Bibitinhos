# Evidência — BIT-01: Módulo de Visão (Sensor Tick a 10 FPS)

**Data de conclusão:** 2026-07-10
**Linear:** N/A

## Demanda atendida

Implementado o `SensorModule` de visão: `compute_vision()` calcula 9 cones binários ao redor de cada `Creature` via `space.bb_query()` + `numpy.arctan2`, atualizados por um brain tick a 10 FPS dissociado do tick de física (30 FPS). Conectar a visão a um `FeedForwardNetwork` real e trocar a locomoção pelos outputs do cérebro fica para a próxima task (BIT-02), conforme escopo definido na spec.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/sensors.py` | criado | `VISION_RADIUS=200.0`, `NUM_VISION_SECTORS=9`, `compute_vision(creature, engine) -> list[float]` |
| `backend/simulation/creature.py` | modificado | `__init__`: `self.vision = [0.0] * 9`; `to_dict()`: chave `"vision"` adicionada (retrocompatível) |
| `backend/simulation/engine.py` | modificado | `BRAIN_TICK_INTERVAL = 1/10.0`, acumulador `self._brain_accumulator`; `step(dt)` dispara `compute_vision()` por criatura viva quando o acumulador atinge o intervalo (sem reset a zero, usa subtração para não acumular drift) |
| `backend/tests/test_sensors.py` | criado | 6 testes: sem vizinhos, comida à frente (cone 0), criatura atrás (cone 4/5), vizinho fora do raio, auto-exclusão, gating do brain tick via monkeypatch |

## Resultados dos gates de qualidade

- `pytest backend/tests/test_sensors.py -v`: **6 passed**
- `pytest backend/tests/ -v` (suíte completa): **14 passed** (8 anteriores de BIT-00 + 6 novos, sem regressão)
- Smoke test manual: `SimulationEngine` com 5 criaturas rodando 20 steps a 1/30s sem erro; `to_dict()["vision"]` presente e com 9 elementos

## Critérios de aceite (da spec)

- [x] `compute_vision` sempre retorna 9 floats, cada um `0.0` ou `1.0`
- [x] Vizinho diretamente à frente ativa só o cone 0
- [x] Vizinho fora de `VISION_RADIUS` não ativa nenhum cone
- [x] Sem vizinhos, todos os 9 cones ficam `0.0`
- [x] A criatura nunca detecta a si mesma
- [x] `step()` só recalcula visão quando o acumulador atinge `1/10s` (verificado via monkeypatch contando chamadas)
- [x] `pytest backend/tests/test_sensors.py` 100% verde
- [x] Nenhuma regressão em `pytest backend/tests/`

## Como validar

```powershell
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Ou manualmente, inspecionando o campo `vision` transmitido no WebSocket (`state_update` → `creatures[i].vision`) enquanto o backend roda.
