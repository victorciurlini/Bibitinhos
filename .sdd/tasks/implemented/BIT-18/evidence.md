# Evidência — BIT-18: Renovação de Comida e Visualização dos Oásis

**Data de conclusão:** 2026-07-14

## Demanda atendida

Corrigidos os dois bugs que impediam a renovação de comida (comida sem TTL saturava o cap global e nunca liberava espaço) e o descontrole do Jardim do Éden (sem teto, chegava a empilhar 13 oásis simultâneos). Comida agora apodrece em 30s liberando vaga no cap; um teto duro de 10 oásis passa a valer inclusive para o Éden; e os oásis agora têm representação visual no canvas (mancha radial verde translúcida que esmaece conforme o TTL cai).

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/food.py` | modificado | `FOOD_TTL = 30.0`; `self.ttl = FOOD_TTL` no `__init__` |
| `backend/simulation/oasis.py` | modificado | `MAX_TOTAL_OASES = 10`; `self.ttl_initial`; `to_dict()` ganha `ttl_fraction` |
| `backend/simulation/engine.py` | modificado | bloco de expiração de comida em `step()`; loop do Éden respeita `MAX_TOTAL_OASES` |
| `frontend/src/components/SimulationCanvas.jsx` | modificado | novo bloco `data.oases.forEach` (gradiente radial), desenhado entre o fundo (BIT-17) e as criaturas |
| `backend/tests/test_oasis.py` | modificado | 4 testes novos (expiração de comida, renovação pós-saturação, teto do Éden, `ttl_fraction`) + 1 teste existente atualizado para o novo formato de `to_dict()` |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest backend/tests/`: **89 passed**, 0 failed (rodado 2x — implementador e revisor independente)
- `npm run build`: OK, sem erros
- Revisão independente (sub-agente): **APROVADO COM RESSALVAS** — ver `review-report.md`

## Validação funcional (diagnóstico headless, seed 42, 10 criaturas, 180s, dt=1/30 — mesmo cenário do bug original)

| t | foods | oases | comidas criadas (acum.) |
|---|---|---|---|
| 15s | 22 | 3 | 22 |
| 30s | 50 | 10 | 52 |
| 105s | 48 | 4 | 173 |
| 180s | 50 | 9 | 288 |

Antes da correção (research/simulation-core.md): apenas **56** comidas criadas em 180s e picos de **13 oásis simultâneos**. Depois: **288** comidas criadas (renovação contínua e sustentada) e `len(engine.oases)` nunca ultrapassou 10 em nenhum dos 5400 steps — confirmado tanto por mim quanto pelo revisor independente, de forma isolada.

## Ressalva não-bloqueante (backlog)

`Oasis(x, y, ttl=0.0).to_dict()` lança `ZeroDivisionError` (`ttl_initial == 0`). Não é alcançável hoje pelo código de produção (spawn natural sorteia `[15,40]`, Éden usa constante `30.0`), mas é uma fragilidade latente sem guard — vale um follow-up de baixo risco.

## Como validar

1. `cd backend && venv\Scripts\python.exe -m pytest tests/ -v` — 89 testes verdes.
2. Via `manager.py` → Start Tudo → abrir frontend: observar manchas verdes translúcidas (oásis) que aparecem, esmaecem gradualmente e somem; comida deve continuar nascendo dentro delas ao longo de vários minutos, sem estagnar após ~30s como antes.
