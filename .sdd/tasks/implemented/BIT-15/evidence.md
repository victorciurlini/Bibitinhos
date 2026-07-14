# Evidência — BIT-15: Gradiente de Cor Contínuo na Fase Adulta

**Data de conclusão:** 2026-07-14

## Demanda atendida

A cor da criatura deixou de ficar fixa em verde (`#22c55e`) durante toda a fase `ADULT` (idade 10-30) e agora deriva continuamente para cinza (`#6b7280`) ao longo dessa faixa, tornando o tempo passando visualmente perceptível.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | `compute_life_color()`: `elif age <= 30: rgb = LIFE_COLOR_MATURE` (valor fixo) virou interpolação contínua `_lerp_rgb(LIFE_COLOR_MATURE, LIFE_COLOR_ELDER_START, t)`; docstring atualizada |
| `backend/tests/test_creature_life_visuals.py` | modificado | `test_mature_plateau_stays_green_between_ten_and_thirty` (codificava o bug) substituído por `test_mature_to_elder_color_changes_continuously_between_ten_and_thirty` |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest backend/tests/`: **85 passed**, 0 failed (sem regressão)
- `npm run test` / `npm run build`: N/A — frontend não tocado (campo `color` continua sendo hex string, contrato inalterado)
- Backend real subido via `uvicorn` (porta isolada 8096), ~8s sem traceback, encerrado ao final

## Validação numérica (motor real, sem mocks)

```
age=10 -> #22c55e   (ponto de partida, inalterado)
age=12 -> #29bd61
age=14 -> #31b465
age=16 -> #38ac68
age=18 -> #3fa46c
age=20 -> #469c6f
age=22 -> #4e9372
age=24 -> #558b76
age=26 -> #5c8379
age=28 -> #647a7d
age=30 -> #6b7280   (fim do ramo ADULT)
age=31 -> #6b7280   (ramo ELDER, energia cheia — sem salto na fronteira)
```

## Como validar

1. `cd backend && venv\Scripts\python.exe -m pytest tests/test_creature_life_visuals.py -v` — confirma a variação contínua.
2. Via `manager.py` → Start Tudo → abrir o frontend → observar uma criatura por alguns minutos: a cor deve derivar perceptivelmente de verde para acinzentado ao longo da fase adulta, não só mudar de repente perto da morte.
