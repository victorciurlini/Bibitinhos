# Evidência — BIT-30: Instrumentação de Linhagem & Hereditariedade

**Data de conclusão:** 2026-08-27

## Demanda atendida

Adicionados rastreamento de linhagem (`generation`, `food_eaten`, `children_count`) a cada `Creature`, contadores de extinção e soma de tempos de vida ao `SimulationEngine`, e os quatro agregados de linhagem (`max_generation`, `avg_generation`, `extinctions_total`, `avg_lifespan`) ao payload de métricas — todos aditivos, sem quebrar nenhum contrato existente.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | Parâmetro `generation=0` em `__init__`; atributos `generation`, `food_eaten`, `children_count`; campos em `to_dict()` |
| `backend/simulation/engine.py` | modificado | Atributos `extinctions_total` e `_lifespan_sum` em `__init__`; `food_eaten += 1` na colisão; `children_count` e `generation` calculada nas reproduções sexuada e assexuada; `_lifespan_sum += c.age` na morte; `extinctions_total += 1` na extinção; re-semeadura com `generation=0` explícito |
| `backend/simulation/metrics.py` | modificado | `compute_metrics()` ganha `max_generation`, `avg_generation`, `extinctions_total`, `avg_lifespan` |
| `backend/simulation/runner.py` | modificado | `populate()` passa `generation=0` explicitamente ao criar criaturas |
| `backend/tests/test_lineage.py` | criado | 20 testes cobrindo atributos iniciais, geração em reprodução sexuada/assexuada, `food_eaten`, `_lifespan_sum`, extinções e `compute_metrics()` |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest tests/`: **200 passed**, 8 warnings (DeprecationWarning do neat-python e pydantic, pré-existentes)
- `npm run test` / `npm run build`: N/A (frontend não tocado)

## Como validar

1. `python manager.py` → Start Tudo → aguardar alguns segundos de simulação
2. No painel de métricas (frontend), verificar que os novos campos aparecem no payload JSON do WebSocket (`max_generation`, `avg_generation`, `extinctions_total`, `avg_lifespan`)
3. Inspecionar uma criatura (GET `/inspect/{id}`) — o `to_dict()` agora inclui `generation`, `food_eaten`, `children_count`
4. Aguardar a primeira extinção e confirmar que `extinctions_total` sobe para 1 no payload de métricas
