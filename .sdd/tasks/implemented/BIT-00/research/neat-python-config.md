# Pesquisa: formato de config e API do neat-python 0.92

> Todos os achados abaixo foram extraídos LENDO O CÓDIGO-FONTE instalado no venv
> (`neat_python-0.92.dist-info` confirma a versão 0.92) e VALIDADOS empiricamente
> executando `venv/Scripts/python.exe` com um arquivo de config real (parseou e ativou a rede sem erro).

## Arquivos relevantes

- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\config.py` — classe `Config`, seção `[NEAT]`
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\genome.py` — `DefaultGenome` e `DefaultGenomeConfig` (seção `[DefaultGenome]`)
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\genes.py` — `DefaultNodeGene`, `DefaultConnectionGene` (definem quais atributos exigem params na config)
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\attributes.py` — `FloatAttribute`, `BoolAttribute`, `StringAttribute` (definem os sufixos de parâmetros: `_init_mean`, `_mutate_rate`, etc.)
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\species.py` — `DefaultSpeciesSet` (seção `[DefaultSpeciesSet]`)
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\stagnation.py` — `DefaultStagnation` (seção `[DefaultStagnation]`)
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\reproduction.py` — `DefaultReproduction` (seção `[DefaultReproduction]`)
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\nn\feed_forward.py` — `FeedForwardNetwork.create` / `.activate`
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\activations.py` — funções de ativação registradas
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\aggregations.py` — funções de agregação registradas
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\venv\Lib\site-packages\neat\__init__.py` — exports de topo (`neat.Config`, `neat.DefaultGenome`, ...)
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\simulation\rtneat_wrapper.py` — wrapper existente do projeto (já usa `configure_new`, `configure_crossover`, `mutate`)

## Conteúdo relevante para a demanda

### 1. `Config` (config.py) — assinatura e seção [NEAT]

Assinatura (linha 140):
```python
Config(genome_type, reproduction_type, species_set_type, stagnation_type, filename)
```
Ordem dos 4 tipos: **genome, reproduction, species_set, stagnation**. Uso típico:
```python
neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
            neat.DefaultSpeciesSet, neat.DefaultStagnation, filename)
```
Todos exportados em `neat/__init__.py` (`neat.Config`, `neat.DefaultGenome`, etc.).

Seção `[NEAT]` **obrigatória** (linhas 163-164 lançam RuntimeError se ausente). Parâmetros (linhas 134-138):

| Parâmetro | Tipo | Default | Obrigatório? |
|---|---|---|---|
| `pop_size` | int | — | SIM |
| `fitness_criterion` | str | — | SIM |
| `fitness_threshold` | float | — | SIM |
| `reset_on_extinction` | bool | — | SIM |
| `no_fitness_termination` | bool | `False` | NÃO (tem default) |

- **`no_fitness_termination` EXISTE na 0.92** (linha 138) — com default `False`, então pode ser omitido.
- Os 4 primeiros NÃO têm default → precisam estar no arquivo, senão `configparser` lança erro.
- Parsing de `[NEAT]` é estrito: qualquer chave desconhecida na seção → `UnknownConfigItemError` (linhas 180-185).
- bool aceita `True`/`False` via `getboolean` (aceita também true/false/1/0/yes/no/on/off).

### 2. `DefaultGenomeConfig` (genome.py) — seção [DefaultGenome]

Parâmetros diretos (linhas 31-43):

| Parâmetro | Tipo | Default | Obrigatório? |
|---|---|---|---|
| `num_inputs` | int | — | SIM |
| `num_outputs` | int | — | SIM |
| `num_hidden` | int | — | SIM |
| `feed_forward` | bool | — | SIM |
| `compatibility_disjoint_coefficient` | float | — | SIM |
| `compatibility_weight_coefficient` | float | — | SIM |
| `conn_add_prob` | float | — | SIM |
| `conn_delete_prob` | float | — | SIM |
| `node_add_prob` | float | — | SIM |
| `node_delete_prob` | float | — | SIM |
| `single_structural_mutation` | bool | `'false'` | NÃO |
| `structural_mutation_surer` | str | `'default'` | NÃO |
| `initial_connection` | str | `'unconnected'` | NÃO |

- **`single_structural_mutation` EXISTE na 0.92** (linha 41, default `'false'`). É usado em `mutate()` (linha 270) e em `check_structural_mutation_surer()` (linha 126).

Além desses, `DefaultGenomeConfig` agrega dinamicamente (linhas 46-49) os parâmetros vindos das classes de gene (`node_gene_type.get_config_params()` + `connection_gene_type.get_config_params()`). Ou seja, os atributos de `DefaultNodeGene` e `DefaultConnectionGene` geram parâmetros OBRIGATÓRIOS na seção `[DefaultGenome]`.

`DefaultNodeGene._gene_attributes` (genes.py 80-83):
- `FloatAttribute('bias')`, `FloatAttribute('response')`, `StringAttribute('activation', options='sigmoid')`, `StringAttribute('aggregation', options='sum')`

`DefaultConnectionGene._gene_attributes` (genes.py 105-106):
- `FloatAttribute('weight')`, `BoolAttribute('enabled')`

Cada `FloatAttribute('X')` gera (attributes.py 32-39; os que têm default `None` são OBRIGATÓRIOS):

| Sufixo | Tipo | Default | Obrigatório? |
|---|---|---|---|
| `X_init_mean` | float | None | SIM |
| `X_init_stdev` | float | None | SIM |
| `X_init_type` | str | `'gaussian'` | NÃO |
| `X_replace_rate` | float | None | SIM |
| `X_mutate_rate` | float | None | SIM |
| `X_mutate_power` | float | None | SIM |
| `X_max_value` | float | None | SIM |
| `X_min_value` | float | None | SIM |

Cada `StringAttribute('X')` gera (attributes.py 134-136):

| Sufixo | Tipo | Default | Obrigatório? |
|---|---|---|---|
| `X_default` | str | `'random'` | NÃO |
| `X_options` | list | None | SIM |
| `X_mutate_rate` | float | None | SIM |

> Nota: `options` é definido no código do gene (`options='sigmoid'` / `options='sum'`), mas como `ConfigParameter` com default `None` ainda é gerado, o parâmetro `activation_options` / `aggregation_options` é OBRIGATÓRIO no arquivo mesmo assim (a interpretação usa o valor do arquivo). Confirmado empiricamente: omitir `aggregation_options` causa erro.

Cada `BoolAttribute('X')` gera (attributes.py 88-91):

| Sufixo | Tipo | Default | Obrigatório? |
|---|---|---|---|
| `X_default` | str | None | SIM |
| `X_mutate_rate` | float | None | SIM |
| `X_rate_to_true_add` | float | `0.0` | NÃO |
| `X_rate_to_false_add` | float | `0.0` | NÃO |

Logo, os parâmetros de gene OBRIGATÓRIOS na seção `[DefaultGenome]`:
- **bias**: `bias_init_mean`, `bias_init_stdev`, `bias_replace_rate`, `bias_mutate_rate`, `bias_mutate_power`, `bias_max_value`, `bias_min_value`
- **response**: `response_init_mean`, `response_init_stdev`, `response_replace_rate`, `response_mutate_rate`, `response_mutate_power`, `response_max_value`, `response_min_value`
- **weight**: `weight_init_mean`, `weight_init_stdev`, `weight_replace_rate`, `weight_mutate_rate`, `weight_mutate_power`, `weight_max_value`, `weight_min_value`
- **activation**: `activation_options`, `activation_mutate_rate` (+ `activation_default` recomendado)
- **aggregation**: `aggregation_options`, `aggregation_mutate_rate` (+ `aggregation_default` recomendado)
- **enabled**: `enabled_default`, `enabled_mutate_rate`

### initial_connection — valores válidos na 0.92

`allowed_connectivity` (genome.py 20-22):
```
['unconnected', 'fs_neat_nohidden', 'fs_neat', 'fs_neat_hidden',
 'full_nodirect', 'full', 'full_direct',
 'partial_nodirect', 'partial', 'partial_direct']
```
Comportamento (configure_new, linhas 190-232):
- `unconnected` → nenhuma conexão inicial (Geração 0 sem conexões).
- `fs_neat` / `fs_neat_nohidden` → 1 input aleatório conectado a todos os outputs.
- `fs_neat_hidden` → 1 input aleatório a todos hidden+output.
- `full` / `full_nodirect` / `full_direct` → totalmente conectado. **`full_direct` conecta cada input a cada output diretamente** (é o que queremos para Geração 0 minimamente conectada com input→output direto; com `num_hidden = 0`, `full`, `full_direct` e `full_nodirect` são equivalentes e produzem 16x4 = 64 conexões diretas).
- `partial`/`partial_nodirect`/`partial_direct` → recebem probabilidade: sintaxe **`initial_connection = partial_direct 0.5`** (o parser em linhas 64-67 faz `self.initial_connection.split()`, pega a fração e valida 0<=frac<=1). Ou seja, a probabilidade vai NA MESMA LINHA separada por espaço.

**Para "Geração 0 minimamente conectada (input→output direto)"**: usar `initial_connection = full_direct` com `num_hidden = 0`. Validado: produz 64 conexões `(-16..-1, 0..3)`.

### 3. Seções das outras 3 classes

`[DefaultSpeciesSet]` (species.py 62-63):

| Parâmetro | Tipo | Default | Obrigatório? |
|---|---|---|---|
| `compatibility_threshold` | float | — | SIM |

`[DefaultStagnation]` (stagnation.py 14-17) — todos com default (nenhum estritamente obrigatório, mas recomendável declarar):

| Parâmetro | Tipo | Default |
|---|---|---|
| `species_fitness_func` | str | `'mean'` |
| `max_stagnation` | int | `15` |
| `species_elitism` | int | `0` |

`[DefaultReproduction]` (reproduction.py 29-31) — todos com default:

| Parâmetro | Tipo | Default |
|---|---|---|
| `elitism` | int | `0` |
| `survival_threshold` | float | `0.2` |
| `min_species_size` | int | `2` |

> IMPORTANTE: mesmo que Stagnation/Reproduction tenham defaults, as 4 seções `[DefaultGenome]`, `[DefaultSpeciesSet]`, `[DefaultStagnation]`, `[DefaultReproduction]` DEVEM EXISTIR no arquivo. `Config.__init__` chama `parameters.items(<nome_da_classe>)` (linhas 188-198) para cada tipo; se a seção não existir, `configparser` lança `NoSectionError`. Cada seção também rejeita chaves desconhecidas (via `DefaultClassConfig`, config.py 118-123).

### 4. Rede feedforward (nn/feed_forward.py)

- Criar: `net = neat.nn.FeedForwardNetwork.create(genome, config)` — recebe o **genome** e o **Config completo** (não o genome_config; internamente acessa `config.genome_config`, linha 35).
- Ativar: `outputs = net.activate(inputs)` — `inputs` é lista/sequência de tamanho `num_inputs` (16). **Retorna uma LISTA** com `num_outputs` (4) floats, na ordem dos `output_keys` `[0, 1, 2, 3]` (linha 26). Lança RuntimeError se o número de inputs não bate (linha 13-14).

### 5. configure_new / configure_crossover (genome.py)

- `genome.configure_new(config)` — recebe **`genome_config`** (o objeto `DefaultGenomeConfig`, i.e. `config.genome_config`), linha 175.
- `genome.configure_crossover(genome1, genome2, config)` — **na 0.92 RECEBE config** (o `genome_config`), linha 234. Assinatura: `configure_crossover(self, genome1, genome2, config)`. Exige que ambos os pais tenham `fitness` numérico (assert linhas 236-237).

O wrapper existente do projeto (`backend/simulation/rtneat_wrapper.py`) já chama corretamente:
```python
genome.configure_new(config.genome_config)
child.configure_crossover(genome1, genome2, config.genome_config)
genome.mutate(config.genome_config)
```

### 6. mutate / single_structural_mutation

- `genome.mutate(config)` — recebe `genome_config`, linha 267.
- `single_structural_mutation` EXISTE (usado na linha 270). Se `True`, aplica no máximo UMA mutação estrutural por chamada (escolhida proporcionalmente entre add/delete node/conn). Se `False` (default), avalia cada mutação independentemente.
- Também existe `structural_mutation_surer` / `check_structural_mutation_surer()` (linhas 120-130).

### 7. Node keys — convenção

Confirmado no código (genome.py 56-58) e empiricamente:
```python
self.input_keys  = [-i - 1 for i in range(self.num_inputs)]   # -1, -2, ..., -num_inputs
self.output_keys = [i for i in range(self.num_outputs)]        # 0, 1, ..., num_outputs-1
```
- Inputs: `-1 .. -16` (input 0 = key -1, input 16 = key -16).
- Outputs: `0 .. 3`.
- Hidden nodes recebem keys crescentes a partir de `max(node keys)+1` (get_new_node_key, linhas 110-118).
- Na ativação, `net.activate(inputs)` mapeia `inputs[i]` → `input_keys[i]`, então `inputs[0]` corresponde à key `-1`.

Validado empiricamente:
```
input_keys:  [-1, -2, ..., -16]
output_keys: [0, 1, 2, 3]
nodes:       [0, 1, 2, 3]  (só os 4 outputs, num_hidden=0)
conexões:    64  (full_direct: cada input -> cada output)
outputs:     lista de 4 floats
```

### 8. Exemplos de config no pacote instalado

**NÃO há** arquivo de config de exemplo dentro do `site-packages/neat` (não há `.cfg`, `.ini`, tests ou docs empacotados). Foi necessário derivar o formato lendo o código-fonte (feito acima) e validar rodando.

### Funções de ativação/agregação disponíveis (para `*_options`)

Ativações registradas (activations.py 105-119):
`sigmoid, tanh, sin, gauss, relu, softplus, identity, clamped, inv, log, exp, abs, hat, square, cube`

Agregações registradas (aggregations.py 58-64):
`product, sum, max, min, maxabs, median, mean`

## Exemplo de config mínimo válido para 0.92 (16 inputs / 4 outputs)

Este arquivo foi **executado no venv e parseou + ativou a rede sem erro**:

```ini
#--- Config NEAT para Bibitinhos: 16 inputs, 4 outputs, feedforward, Geração 0 conectada ---

[NEAT]
fitness_criterion     = max
fitness_threshold     = 1000.0
pop_size              = 50
reset_on_extinction   = True
# no_fitness_termination tem default False; omitido de propósito

[DefaultGenome]
# --- topologia ---
num_inputs              = 16
num_outputs             = 4
num_hidden              = 0
feed_forward            = True
# full_direct + num_hidden=0 => Geração 0 com conexões diretas input->output (16x4=64)
initial_connection      = full_direct

# --- compatibilidade / especiação ---
compatibility_disjoint_coefficient = 1.0
compatibility_weight_coefficient   = 0.5

# --- probabilidades de mutação estrutural ---
conn_add_prob           = 0.5
conn_delete_prob        = 0.2
node_add_prob           = 0.2
node_delete_prob        = 0.1
single_structural_mutation = False
structural_mutation_surer  = default

# --- node: bias ---
bias_init_mean          = 0.0
bias_init_stdev         = 1.0
bias_max_value          = 30.0
bias_min_value          = -30.0
bias_mutate_power       = 0.5
bias_mutate_rate        = 0.7
bias_replace_rate       = 0.1

# --- node: response ---
response_init_mean      = 1.0
response_init_stdev     = 0.0
response_max_value      = 30.0
response_min_value      = -30.0
response_mutate_power   = 0.0
response_mutate_rate    = 0.0
response_replace_rate   = 0.0

# --- node: activation ---
activation_default      = tanh
activation_mutate_rate  = 0.05
activation_options      = tanh sigmoid relu

# --- node: aggregation ---
aggregation_default     = sum
aggregation_mutate_rate = 0.0
aggregation_options     = sum

# --- connection: weight ---
weight_init_mean        = 0.0
weight_init_stdev       = 1.0
weight_max_value        = 30.0
weight_min_value        = -30.0
weight_mutate_power     = 0.5
weight_mutate_rate      = 0.8
weight_replace_rate     = 0.1

# --- connection: enabled ---
enabled_default         = True
enabled_mutate_rate     = 0.01

[DefaultSpeciesSet]
compatibility_threshold = 3.0

[DefaultStagnation]
species_fitness_func = max
max_stagnation       = 20
species_elitism      = 2

[DefaultReproduction]
elitism            = 2
survival_threshold = 0.2
min_species_size   = 2
```

Notas de formato:
- Listas (`*_options`) são separadas por **espaço** (config.py 38-39 faz `v.split(" ")`), nunca por vírgula.
- `partial_*` levaria a fração na mesma linha: `initial_connection = partial_direct 0.5`.
- Comentários com `#` são aceitos pelo `configparser`.

## O que precisa ser feito

1. **Criar o arquivo de config** (ex.: `backend/simulation/neat_config.ini` ou dentro de `backend/config/`) com o conteúdo do exemplo acima (16 inputs / 4 outputs / `full_direct` / `feed_forward=True`). Os 16 inputs mapeiam para os sensores descritos (9 cones + energia + idade + hormonal + relógio biológico + sensor de carga + feedback cinético 2D → confirmar se "feedback cinético 2D" é 1 ou 2 canais; ver Perguntas em aberto) e os 4 outputs para `motor_forward, motor_torque, action_grab_drop, action_mate`.

2. **Adicionar uma função de carregamento** ao projeto (natural em `backend/simulation/rtneat_wrapper.py`, que já é o módulo NEAT do projeto):
```python
import os
import neat

def load_neat_config(config_path):
    """Carrega a Config do NEAT 0.92 a partir de um arquivo .ini."""
    return neat.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_path,
    )
```
As funções `create_zero_genome`, `organic_crossover`, `mutate_genome` já existentes no wrapper estão corretas para a 0.92 (usam `configure_new`, `configure_crossover(g1,g2,genome_config)`, `mutate(genome_config)`).

3. **Para instanciar redes** durante a simulação, usar:
```python
net = neat.nn.FeedForwardNetwork.create(genome, config)   # config = objeto Config completo
outputs = net.activate(vetor_de_16_floats)                # retorna lista de 4 floats
```

4. **Ordem dos inputs**: definir e documentar o mapeamento sensor→índice (0..15), pois `activate(inputs)` associa `inputs[i]` à key `-(i+1)`. Manter esse contrato estável.

## Perguntas em aberto

1. **"feedback cinético 2D" = quantos canais?** O enunciado lista 9 cones + energia + idade + hormonal + relógio biológico + sensor de carga = 14, e "feedback cinético 2D" precisa ser 2 canais (vx, vy ou linear+angular) para fechar em **16 inputs**. Assumi 2 canais no exemplo (num_inputs=16). Confirmar com o design da simulação.
2. **Valores de hiperparâmetros** (mutate rates, threshold de compatibilidade, pop_size, fitness_threshold, elitismo) no exemplo são placeholders razoáveis; precisam ser calibrados para a dinâmica de vida artificial em tempo real (rtNEAT) do Bibitinhos.
3. **rtNEAT vs NEAT geracional**: o módulo chama-se `rtneat_wrapper` (real-time NEAT). O neat-python 0.92 é geracional (classe `Population`). Se a simulação usa substituição contínua de indivíduos, o projeto provavelmente NÃO usa `Population.run()` e sim orquestra `configure_new`/`configure_crossover`/`mutate` manualmente (como o wrapper já sugere). A config aqui serve para ambos, mas os parâmetros geracionais (`pop_size`, `max_stagnation`, `elitism`, `survival_threshold`) podem ser irrelevantes se a evolução for gerida fora do `Population`. Confirmar a estratégia evolutiva pretendida.
4. **Localização/nome do arquivo de config** no projeto ainda a definir (sugerido `backend/simulation/neat_config.ini`).
