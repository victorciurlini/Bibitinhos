# Evidência — BIT-14: Cone de Visão Frontal

**Data de conclusão:** 2026-07-14

## Demanda atendida

A visão das criaturas deixou de cobrir 360° com raio 200 e passou a ser um cone frontal de 120° com raio 80, alinhado à "cabeça" (direção) da criatura — conforme feedback direto do developer sobre o resultado visual do BIT-12/BIT-13.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/sensors.py` | modificado | `VISION_RADIUS` 200→80; nova `VISION_FOV_DEGREES = 120`; `compute_vision()` descarta tudo fora do cone frontal (`abs(relative_angle) > FOV/2`); setor central (índice 4) é o eixo "para frente" |
| `backend/simulation/rtneat_wrapper.py` | modificado | Docstring de `Visual_Sectors` atualizada para descrever o cone de 120°/setor central |
| `backend/simulation/engine.py` | modificado | `get_state()` inclui `vision_fov_degrees` (ao lado do `vision_radius` já existente) |
| `frontend/src/components/SimulationCanvas.jsx` | modificado | Leque de setores desenhado só dentro do cone frontal (`data.vision_fov_degrees`), não mais 360° |
| `backend/tests/test_sensors.py` | modificado | Setor central (índice 4) substitui índice 0 como "para frente"; testes de detecção "atrás" viraram testes de "fora do cone, sem sinal"; novo teste de borda do FOV (70° fora dos ±60°) |

## Resultados dos gates de qualidade

- `pytest backend/tests/`: **63 passed**, 0 failed
- `npm run build`: OK
- `npm run test`: 1 passed
- Backend real subido via `uvicorn` em porta isolada (8098), ~8s sem traceback no log, encerrado ao final

## Como validar

1. `cd backend && venv\Scripts\python.exe -m pytest tests/test_sensors.py -v` — confirma a nova geometria (cone de 120°, setor central, exclusão total do que está atrás/fora do cone).
2. Via `manager.py` → Start Tudo → abrir o frontend → cada bibite deve mostrar um cone verde claro bem mais curto e estreito, só na frente dele (não mais um leque completo ao redor).
