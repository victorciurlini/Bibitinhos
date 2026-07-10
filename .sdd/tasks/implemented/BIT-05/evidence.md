# Evidência — BIT-05: Metabolismo e Longevidade

**Data de conclusão:** 2026-07-10

## Demanda atendida

Introduzido metabolismo passivo por `LifeStage`: toda criatura viva (fora do estágio `EGG`) gasta energia por segundo só por estar viva, com taxa crescente (`JUVENILE=0.3 < ADULT=0.8 < ELDER=2.0`, `EGG=0.0`). Isso torna comer uma necessidade real — antes, uma criatura com motor parado nunca perdia energia — e cria longevidade como métrica emergente: comer estende mensuravelmente quanto tempo uma criatura sobrevive.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | `METABOLISM_RATE_BY_STAGE` (dict); `update()` soma `metabolism_cost` ao `motor_cost` existente |
| `backend/tests/test_creature_think.py` | modificado | `test_update_energy_cost_proportional_to_motor_magnitude`: `quiet_cost` agora espera o custo de metabolismo do ADULT em vez de `0.0` |
| `backend/tests/test_reproduction.py` | modificado | 4 asserções de energia exata (`test_adult_pair_with_action_mate_reproduces_on_collision`, `test_action_mate_false_prevents_reproduction`, `test_juvenile_prevents_reproduction`, `test_low_energy_prevents_reproduction`) passam a usar `pytest.approx` incorporando o metabolismo de 1 step |
| `backend/tests/test_metabolism.py` | criado | 7 testes: custo por estágio (parametrizado), EGG sem custo, taxas estritamente crescentes, morte por inanição só de metabolismo, comer estende sobrevivência |

`backend/tests/test_feeding.py` não precisou de alteração — confirmado (criaturas desses testes ficam em `EGG`, que mantém custo zero).

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest backend/tests/` → **48/48 passed** (41 pré-existentes + 7 novos), sem regressão
- Smoke test de 1200 steps (40s simulados a 30 FPS, 10 criaturas): sem exceção; energia média final ~36.6/100 (dreno real e mensurável pelo metabolismo, antes seria ~100 para criaturas paradas)
- Servidor real (`uvicorn main:app`) subiu e rodou 6s sem traceback no log

## Como validar

```powershell
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Manualmente: `manager.py` → Start Tudo → abrir frontend, deixar rodar alguns minutos — criaturas paradas ou com pouco movimento devem perder energia visivelmente ao longo do tempo (antes, uma criatura parada nunca perdia energia); criaturas `ELDER` devem morrer mais rápido se não comerem, criando turnover populacional.
