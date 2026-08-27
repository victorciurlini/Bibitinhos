# Evidência — BIT-35: Robustez Evolutiva

**Data de conclusão:** 2026-08-27

## Demanda atendida

Rebalanceo de ecossistema (comida, metabolismo, reprodução), fortalecimento da rede de
segurança (Eden, Hall of Fame) e novo mecanismo de pressão adaptativa de população que
multiplica o spawn de comida pela densidade atual de criaturas.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | STARTING_ENERGY 75→85, IDLE_PENALTY_RATE 1.2→0.8, FERTILITY_ENERGY_THRESHOLD 60→50, METABOLISM_RATE_BY_STAGE[ADULT] 0.8→0.5 |
| `backend/simulation/oasis.py` | modificado | OASIS_TTL_MIN 15→25, OASIS_TTL_MAX 40→60, OASIS_FOOD_SPAWN_CHANCE 0.18→0.22, MAX_TOTAL_FOOD 110→150, EDEN_POPULATION_THRESHOLD 10→15 |
| `backend/simulation/engine.py` | modificado | MATING_RADIUS 150→200, REPRODUCTION_ENERGY_COST 30→20, REPRODUCTION_COOLDOWN 10→6, HALL_OF_FAME_SIZE 12→20; novas constantes HALL_OF_FAME_FOOD_WEIGHT/LOW\|HIGH_POP_FOOD_THRESHOLD/FOOD_MULTIPLIER_*; novo método _compute_food_multiplier(); HoF score inclui food_eaten; Eden respawn 10→15 criaturas |
| `backend/simulation/params.py` | modificado | 10 defaults atualizados para refletir novos valores |
| `backend/tests/test_ecosystem_balance.py` | criado | 22 novos testes: constantes, multiplicador adaptativo, HoF, Eden |
| `backend/tests/test_hall_of_fame.py` | modificado | 2 asserts `== 10` → `== 15` (respawn do Eden) |
| `backend/tests/test_oasis.py` | modificado | 1 assert `== 10` → `== 15`; nome do teste atualizado |
| `backend/tests/test_lineage.py` | modificado | 1 assert `== 10` → `== 15` |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest tests/`: **246 passed**, 8 warnings

## Como validar

1. Iniciar serviços (`manager.bat` ou `python manager.py`)
2. Aguardar ~2 min de simulação
3. Observar no frontend:
   - Mais comida visível no mapa (cap 150 vs 110 anterior)
   - Extinções menos frequentes (Eden ativa com 14 criaturas)
   - Geração média subindo mais rápido (reprodução mais barata: 20 E vs 30)
   - Com pop < 15: ondas de comida mais densas (multiplicador ×1.5)
   - Com pop > 50: comida mais escassa (multiplicador ×0.75)
4. Verificar no Painel de Métricas: `extinctions_total` crescendo mais lentamente
