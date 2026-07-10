# Spec — Config NEAT (16 inputs / 4 outputs) e loader no rtneat_wrapper

**Linear:** N/A — decisão do usuário: fluxo apenas com docs locais em `.sdd/`, sem card
**Risco:** low
**Camada(s):** Backend (simulação/IA)

---

## Demanda
Criar o arquivo de configuração do neat-python 0.92 que define a interface neural dos Bibitinhos (16 inputs sensoriais, 4 outputs motores, feedforward, Geração 0 com conexões diretas input→output) e a função de carregamento dessa config no `rtneat_wrapper.py` — o pré-requisito para conectar cérebros às criaturas (passos 2 e 3 do roadmap). O `docs/task.md` marcava isso como feito, mas nem o arquivo nem o loader existem no código.

**Escopo OUT:** conectar o cérebro à `Creature` (sensores/visão = passo 2; atuadores = passo 3), reprodução por colisão, oásis.

## Abordagem técnica
Versionar um `neat_config.ini` já validado empiricamente contra a 0.92 instalada no venv (formato derivado do código-fonte da lib — a 0.92 não empacota exemplos e difere das versões atuais). Adicionar `load_neat_config()` com cache de módulo ao wrapper existente, e endurecer `organic_crossover` contra o `assert` de fitness da 0.92 (rtNEAT não usa fitness; a 0.92 exige fitness numérico nos pais para crossover). Testes pytest provam o contrato completo: parse → genoma Gen 0 → rede → crossover → mutação.

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/simulation/neat_config.ini` | criar | Config NEAT 0.92: 16 in / 4 out, `feed_forward=True`, `initial_connection=full_direct`, `num_hidden=0` |
| `backend/simulation/rtneat_wrapper.py` | modificar | Adicionar `DEFAULT_CONFIG_PATH`, `load_neat_config()` (com cache) e default de fitness em `organic_crossover` |
| `backend/tests/test_rtneat_wrapper.py` | criar | Testes pytest do contrato completo |

## Passos de implementação

1. **Criar `backend/simulation/neat_config.ini`** com o conteúdo exato validado em `research/neat-python-config.md` (seção "Exemplo de config mínimo válido"). Pontos inegociáveis do formato 0.92:
   - As 4 seções `[DefaultGenome]`, `[DefaultSpeciesSet]`, `[DefaultStagnation]`, `[DefaultReproduction]` DEVEM existir (senão `NoSectionError`), além de `[NEAT]`.
   - `[NEAT]`: `pop_size`, `fitness_criterion`, `fitness_threshold`, `reset_on_extinction` são obrigatórios (sem default). Nota: `pop_size`/stagnation/elitism são exigidos pelo parser mas irrelevantes para o rtNEAT orgânico (não usamos `Population.run()`); documentar isso em comentário no .ini.
   - `[DefaultGenome]`: TODOS os parâmetros de atributo de gene são obrigatórios — 7 params para cada um de `bias`/`response`/`weight`, mais `activation_options`/`activation_mutate_rate`, `aggregation_options`/`aggregation_mutate_rate`, `enabled_default`/`enabled_mutate_rate`. Listas separadas por ESPAÇO (não vírgula).
   - `num_inputs=16`, `num_outputs=4`, `num_hidden=0`, `feed_forward=True`, `initial_connection=full_direct`, `activation_default=tanh` (outputs contínuos ±1 para motor).
2. **Modificar `backend/simulation/rtneat_wrapper.py`**:
   - `DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "neat_config.ini")` (path relativo ao módulo, não ao CWD — o uvicorn roda com CWD em `backend/`).
   - `load_neat_config(config_path=None)`: retorna `neat.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation, path)` — ordem dos 4 tipos é essa, posicional. Cachear por path em dict de módulo (config é imutável; parse é caro para ser refeito por criatura).
   - Em `organic_crossover`: antes do `configure_crossover`, se `genome1.fitness`/`genome2.fitness` for `None`, atribuir `0.0` (a 0.92 tem `assert` de fitness numérico; no rtNEAT a dominância parental virá de energia/idade no passo de reprodução, fora deste escopo).
   - Documentar no docstring do módulo o contrato de I/O: inputs índice 0–8 = cones visuais, 9 = energia, 10 = idade, 11 = hormonal, 12 = relógio biológico, 13 = carga, 14–15 = feedback cinético (2 canais); outputs 0 = motor_forward, 1 = motor_torque, 2 = action_grab_drop, 3 = action_mate. (`activate(inputs)` mapeia `inputs[i]` → node key `-(i+1)`; manter contrato estável.)
3. **Criar `backend/tests/test_rtneat_wrapper.py`** cobrindo:
   - `load_neat_config()` parseia sem erro; `genome_config.num_inputs == 16`, `num_outputs == 4`; `input_keys == [-1..-16]`, `output_keys == [0,1,2,3]`.
   - `create_zero_genome(1, config)` → genoma com 64 conexões (full_direct) e 4 nodes.
   - `neat.nn.FeedForwardNetwork.create(genome, config)` + `net.activate([0.0]*16)` → lista de 4 floats.
   - `net.activate` com tamanho errado de input → `RuntimeError` (guarda de contrato).
   - `organic_crossover(g1, g2, 3, config)` com pais de `fitness=None` → produz filho sem AssertionError.
   - `mutate_genome(child, config)` roda sem erro.
   - Cache: duas chamadas de `load_neat_config()` retornam o mesmo objeto.
4. **Rodar os testes** com o venv do projeto: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_rtneat_wrapper.py -v` (a partir da raiz; ajustar `sys.path`/`conftest.py` para `backend/` ser importável se necessário).

## Contratos técnicos

### NEAT I/O (contrato estável para os passos 2 e 3)
| Índice input | Sensor | Faixa |
|---|---|---|
| 0–8 | Visual_Sectors (9 cones; Gen 0: 3 ativos, resto -1.0) | -1.0/0.0/1.0 |
| 9 | Energy_Level | 0.0–1.0 |
| 10 | Age_Degradation | 0.0–1.0 |
| 11 | Hormonal_Level | 0.0–1.0 |
| 12 | Biological_Clock | -1.0–1.0 |
| 13 | Load_Sensor | 0.0/0.5/1.0 |
| 14–15 | Kinetic_Feedback (2 canais; semântica exata — velocidade linear local × angular — fecha no passo 2) | contínuo |

| Índice output | Ação |
|---|---|
| 0 | Motor_Forward (contínuo ±, tanh) |
| 1 | Motor_Torque (contínuo ±, tanh) |
| 2 | Action_Grab_Drop (binário via threshold, no passo 3) |
| 3 | Action_Mate (binário via threshold, no passo 3) |

### API Python
```python
from simulation.rtneat_wrapper import load_neat_config, create_zero_genome, organic_crossover, mutate_genome
config = load_neat_config()                     # cacheado; aceita path opcional
genome = create_zero_genome(genome_id, config)  # Gen 0: 64 conexões diretas
net = neat.nn.FeedForwardNetwork.create(genome, config)  # Config COMPLETO, não genome_config
outputs = net.activate([...16 floats...])       # lista de 4 floats
```

## Critérios de aceite

- [ ] `backend/simulation/neat_config.ini` existe e `load_neat_config()` o parseia sem erro no venv do projeto (neat-python 0.92).
- [ ] Genoma Gen 0 nasce com 64 conexões diretas (16×4), `input_keys` -1..-16 e `output_keys` 0..3.
- [ ] Rede feedforward criada do genoma ativa com 16 inputs e retorna 4 outputs.
- [ ] `organic_crossover` funciona com pais de `fitness=None` (sem AssertionError).
- [ ] `mutate_genome` executa sem erro sobre o filho do crossover.
- [ ] Suíte `backend/tests/test_rtneat_wrapper.py` verde via pytest do venv.
- [ ] Nenhuma mudança de comportamento na simulação atual (main.py/engine.py/creature.py intocados).

## Rollback
Deletar `backend/simulation/neat_config.ini` e `backend/tests/test_rtneat_wrapper.py`; reverter `backend/simulation/rtneat_wrapper.py` via `git checkout -- backend/simulation/rtneat_wrapper.py`.
