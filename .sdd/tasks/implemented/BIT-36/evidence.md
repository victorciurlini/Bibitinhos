# Evidência — BIT-36: Camadas Ocultas

**Data de conclusão:** 2026-08-27

## Demanda atendida

Adicionadas 2 camadas ocultas (`num_hidden = 2`) à rede NEAT, permitindo que a rede evolua representações internas mais complexas. A topologia Gen-0 passou de 64 conexões diretas (16→4) para 104 conexões (16×6 input→{output,hidden} + 2×4 hidden→output).

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/neat_config.ini` | modificado | `num_hidden = 0` → `2`; comentário da topologia atualizado |
| `backend/simulation/rtneat_wrapper.py` | modificado | `create_zero_genome`: zera pesos hidden→output em Gen-0 para evitar cancelamento do bias seedado |
| `backend/tests/test_rtneat_wrapper.py` | modificado | `test_create_zero_genome_is_fully_connected`: conexões 64→104, nodes 4→6 |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest tests/`: 246 passed, 0 failed

## Como validar

1. `python -c "from simulation.rtneat_wrapper import create_zero_genome, load_neat_config; c = load_neat_config(); g = create_zero_genome(1,c); print(len(g.connections), len(g.nodes))"` → `104 6`
2. `python -m pytest tests/test_rtneat_wrapper.py -v` → 7 passed
