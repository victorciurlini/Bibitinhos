# Research: Backend de Simulação — pontos de integração para config NEAT

## Arquivos relevantes
- `backend/simulation/rtneat_wrapper.py` — wrapper existente (funções puras, exigem `config` como parâmetro)
- `backend/simulation/creature.py` — Creature (Pymunk Body, LifeStage enum; SEM cérebro hoje)
- `backend/simulation/engine.py` — SimulationEngine.step(dt) (sem reprodução, sem consumo de comida)
- `backend/main.py` — loop asyncio 30 FPS, instancia Creatures no startup
- `backend/requirements.txt` — `neat-python==0.92` já instalado no venv

## Conteúdo relevante para a demanda

### rtneat_wrapper.py (estado atual — 27 linhas)
```python
import neat

def create_zero_genome(genome_id, config):
    genome = config.genome_type(genome_id)
    genome.configure_new(config.genome_config)
    return genome

def organic_crossover(genome1, genome2, genome_id, config):
    child = config.genome_type(genome_id)
    child.configure_crossover(genome1, genome2, config.genome_config)
    return child

def mutate_genome(genome, config):
    genome.mutate(config.genome_config)
    return genome
```
**Gap:** todas as funções recebem `config`, mas NÃO existe função que crie/carregue esse config, nem arquivo de config no repositório. `docs/task.md` marca "[x] Implementar método de carregamento da configuração (usando o config-feedforward do neat-python)" mas isso nunca foi implementado.

### Interface planejada do cérebro (README.md §6.1)
Inputs (16):
| # | Sensor | Faixa |
|---|--------|-------|
| 0–8 | Visual_Sectors[0..8] (9 cones binários; Gen 0 só 3 ativos, resto recebe -1.0) | -1.0 / 0.0 / 1.0 |
| 9 | Energy_Level | 0.0–1.0 |
| 10 | Age_Degradation | 0.0–1.0 |
| 11 | Hormonal_Level (só ADULT) | 0.0–1.0 |
| 12 | Biological_Clock (senoidal) | -1.0–1.0 |
| 13 | Load_Sensor (0.0 vazio / 0.5 comida / 1.0 ovo) | 0.0–1.0 |
| 14–15 | Kinetic_Feedback (aceleração 2D do corpo físico) | contínuo |

Outputs (4): Motor_Forward (contínuo ±), Motor_Torque (contínuo ±), Action_Grab_Drop (binário), Action_Mate (binário).

Gen 0 deve nascer "minimamente conectada" (README: "Conexão direta Input → Output"; plan: "inputs mapeados para 0 e visão restrita").

### Testes existentes
- `backend/` tem pytest no requirements; não há diretório de testes do backend ainda (verificado: só `frontend/src/tests/App.test.jsx`).

## O que precisa ser feito
1. Criar arquivo de config NEAT versionado no repo (ex.: `backend/simulation/neat_config.ini`) com num_inputs=16, num_outputs=4, feed_forward=True.
2. Adicionar ao wrapper uma função `load_config()` com cache (config é imutável e caro de parsear; carregar uma vez por processo).
3. Criar testes (`backend/tests/test_rtneat_wrapper.py`) cobrindo: load, create_zero_genome, organic_crossover, mutate_genome e criação/ativação de FeedForwardNetwork com 16 inputs → 4 outputs.

## Perguntas em aberto
- Parâmetros exatos exigidos pela 0.92 no arquivo de config (delegado ao research neat-python-config.md).
- Valor de `initial_connection` correto na 0.92 para conexão direta input→output.
- `pop_size`/`fitness_threshold` são obrigatórios na seção [NEAT] mesmo sem usar o loop de Population? (rtNEAT não usa Population, mas o parser pode exigir.)
