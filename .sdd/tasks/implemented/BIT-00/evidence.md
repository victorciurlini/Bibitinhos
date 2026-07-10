# Evidência — Config NEAT (16 inputs / 4 outputs) e loader no rtneat_wrapper

**Data de conclusão:** 2026-07-10
**Linear:** N/A

## Demanda atendida

Criado o arquivo de configuração do neat-python 0.92 (16 inputs sensoriais / 4 outputs motores, feedforward, Geração 0 conectada via `full_direct`) e a função `load_neat_config()` com cache no `rtneat_wrapper.py`, além de endurecer `organic_crossover` contra o assert de fitness da 0.92.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/neat_config.ini` | criado | Config NEAT 0.92 completa: `[NEAT]`, `[DefaultGenome]` (16 in / 4 out, `full_direct`, `num_hidden=0`), `[DefaultSpeciesSet]`, `[DefaultStagnation]`, `[DefaultReproduction]` |
| `backend/simulation/rtneat_wrapper.py` | modificado | `DEFAULT_CONFIG_PATH`, `load_neat_config()` com cache por path; docstring de módulo documentando contrato de I/O (16 inputs / 4 outputs); `organic_crossover` agora atribui `fitness = 0.0` aos pais quando `None`, antes do `configure_crossover` |
| `backend/tests/test_rtneat_wrapper.py` | criado | 7 testes pytest cobrindo parsing da config, topologia do genoma Gen 0 (64 conexões / 4 nodes), ativação da rede (16→4), erro em input de tamanho errado, crossover sem fitness, mutação e cache de `load_neat_config()` |
| `backend/conftest.py` | criado | Adiciona `backend/` ao `sys.path` para que `simulation` seja importável pelo pytest a partir da raiz do repo |

## Resultados dos gates de qualidade

- `pytest backend/tests/test_rtneat_wrapper.py -v`: **7 passed**
- `pytest backend/tests/ -v` (suíte completa): **8 passed** (nenhuma regressão no `test_simulation.py` existente)
- `main.py`/`engine.py`/`creature.py`: intocados — nenhuma mudança de comportamento na simulação atual

## Como validar

```powershell
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos
backend\venv\Scripts\python.exe -m pytest backend/tests/test_rtneat_wrapper.py -v
```

Ou manualmente:
```python
from simulation.rtneat_wrapper import load_neat_config, create_zero_genome
import neat
config = load_neat_config()
genome = create_zero_genome(1, config)
net = neat.nn.FeedForwardNetwork.create(genome, config)
print(net.activate([0.0] * 16))  # -> lista de 4 floats
```
