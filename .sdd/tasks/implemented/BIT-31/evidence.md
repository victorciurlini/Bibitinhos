# Evidência — BIT-31: Hall of Fame contra Reset Evolutivo

**Data de conclusão:** 2026-08-27

## Demanda atendida

Introduzido Hall of Fame no engine: ao morrer, cada criatura é avaliada por `score = age + W·children_count` e, se elegível, tem o genoma clonado e preservado em lista ordenada com cap de 12. Na extinção total, a re-semeadura clona+muta genomas do hall (preservando a geração da linhagem), com fallback para genoma zero se o hall ainda estiver vazio.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/engine.py` | modificado | Import `load_neat_config`; constantes `HALL_OF_FAME_SIZE`/`HALL_OF_FAME_CHILDREN_WEIGHT`; `self.hall_of_fame = []` no `__init__`; métodos `_record_in_hall_of_fame` e `_spawn_from_hall_of_fame`; chamada ao registro no laço de morte; re-semeadura de extinção via hall |
| `backend/tests/test_hall_of_fame.py` | criado | 12 testes cobrindo inserção/ordenação/cap do hall, deepcopy, extinção com hall populado (geração preservada), extinção com hall vazio (fallback), e integração via `step()` |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest tests/`: **212 passed**, 8 warnings (DeprecationWarning do neat-python e pydantic, pré-existentes)
- `npm run test` / `npm run build`: N/A (frontend não tocado)

## Como validar

1. `manager.py` → Start Tudo → aguardar a primeira extinção (população zerar)
2. Após a extinção, verificar no frontend que `max_generation` nas métricas **não reseta para 0** — as novas criaturas nascem com a geração dos melhores genomas do hall
3. Verificar no `backend.log` que não há tracebacks durante a re-semeadura
