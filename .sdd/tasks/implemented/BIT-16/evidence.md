# Evidência — BIT-16: Rebalanceamento Energético da Reprodução

**Data de conclusão:** 2026-07-14

## Demanda atendida

Criaturas agora nascem com 75% de energia (era 100%), precisam de 100% para se reproduzir (era 50%) e a reprodução custa 50% (era 30%) — a reprodução assexuada foi ajustada proporcionalmente (limiar 100%, custo 70%) para preservar sua posição como via mais difícil que a sexuada. Efeito esperado: criaturas precisam efetivamente aprender a buscar comida antes de conseguir se reproduzir, criando pressão evolutiva real contra ficar parado ou andar sem rumo.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | Nova constante `STARTING_ENERGY = 75.0`; `__init__` usa em vez de `100.0` hardcoded |
| `backend/simulation/engine.py` | modificado | `REPRODUCTION_ENERGY_COST` 30→50, `MIN_ENERGY_TO_MATE` 50→100, `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` 70→100, `ASEXUAL_REPRODUCTION_ENERGY_COST` 50→70 |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest backend/tests/`: **85 passed**, 0 failed — nenhum arquivo de teste precisou de alteração (constantes são importadas, não hardcoded, confirmando a análise da spec)
- `npm run test` / `npm run build`: N/A — frontend não tocado
- Backend real subido via `uvicorn` (porta isolada 8095), ~8s sem traceback, encerrado ao final

## Validação funcional (motor real, sem mocks)

```
STARTING_ENERGY=75.0, MIN_ENERGY_TO_MATE=100.0, REPRODUCTION_ENERGY_COST=50.0
MIN_ENERGY_TO_REPRODUCE_ASEXUALLY=100.0, ASEXUAL_REPRODUCTION_ENERGY_COST=70.0

Criatura recem-criada: energy=75.0 (esperado 75.0)
ADULT com energy=75 tentando reproduzir assexuado: 1 criatura(s) (esperado 1, sem filho)
ADULT com energy=100 tentando reproduzir assexuado: 2 criatura(s) (esperado 2)
```

Confirmado: uma criatura recém-nascida (75% de energia) **não consegue** se reproduzir, mesmo estando `ADULT` e com `action_mate=True` — precisa efetivamente ganhar energia (comer) até chegar a 100% primeiro.

## Como validar

1. `cd backend && venv\Scripts\python.exe -m pytest tests/test_reproduction.py tests/test_asexual_reproduction.py -v` — confirma que a reprodução (sexuada e assexuada) segue funcionando, agora sob as novas exigências.
2. Via `manager.py` → Start Tudo → observar por alguns minutos: criaturas não devem mais se aglomerar acasalando logo ao nascer — a população deve crescer mais devagar, só depois de criaturas conseguirem comer o suficiente.
