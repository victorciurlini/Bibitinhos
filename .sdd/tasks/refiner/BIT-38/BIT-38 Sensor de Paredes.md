# Spec — BIT-38: Sensor de Proximidade de Paredes

**Linear:** N/A
**Risco:** high
**Camada(s):** Backend (Simulação)

---

## Demanda

Adicionar 4 novos sensores de proximidade de paredes ao cérebro NEAT, ampliando o contrato de I/O de 16 para 20 inputs. Os 4 novos sensores medem distância normalizada [0,1] da criatura às paredes Norte, Sul, Oeste e Leste, permitindo que a rede neural evolua comportamentos de navegação reactivos (evitar colisões, patrulhar bordas, etc.). Valor 0 = perto da parede, valor 1 = longe/no limite oposto.

---

## Abordagem técnica

### Fórmula de cálculo

Os sensores são calculados cada vez que `creature.think()` monta o array de inputs para a rede neural:

```python
# Acesso aos parâmetros globais
cx, cy = creature.body.position.x, creature.body.position.y
width = engine.width   # ex: 1920
height = engine.height # ex: 1080

# Cálculo dos 4 sensores de parede (normalizados [0, 1], clampados para segurança)
wall_north = min(1.0, max(0.0, cy / height))              # distância à parede norte (y=0)
wall_south = min(1.0, max(0.0, (height - cy) / height))   # distância à parede sul (y=height)
wall_west = min(1.0, max(0.0, cx / width))                # distância à parede oeste (x=0)
wall_east = min(1.0, max(0.0, (width - cx) / width))      # distância à parede leste (x=width)
```

Interpretação:
- **Wall_N**: 0 se criatura está em y≈0 (norte/topo), 1 se está em y≈height (sul/fundo)
- **Wall_S**: 0 se criatura está em y≈height (sul), 1 se está em y≈0 (norte)
- **Wall_W**: 0 se criatura está em x≈0 (oeste/esquerda), 1 se está em x≈width (leste/direita)
- **Wall_E**: 0 se criatura está em x≈width (leste), 1 se está em x≈0 (oeste)

### Localização no array de inputs

Os 4 novos inputs ocupam os índices 16, 17, 18, 19 (sequência imediata após os 16 existentes):

```
Índices 0-8:   Visual_Sector_0 a Visual_Sector_8 (9 cones visuais)
Índices 9-15:  Energy_Level, Age_Degradation, Hormonal_Level, Biological_Clock, 
               Load_Sensor, Kinetic_Linear, Kinetic_Angular (7 inputs)
Índices 16-19: Wall_North, Wall_South, Wall_West, Wall_East (4 NOVOS inputs)
```

### Mudanças no contrato de I/O do NEAT

1. **num_inputs**: 16 → 20 em `neat_config.ini`
2. **INPUT_LABELS**: adicionar 4 strings em `rtneat_wrapper.py`
3. **Documentação/contrato**: atualizar comentários em `neat_config.ini` e docstring de `rtneat_wrapper.py`
4. **Topologia Gen-0**: 20 inputs → 6 nodos (4 outputs + 2 hidden) = 20×6 + 2×4 = 128 conexões (antes: 104)
5. **Reset do Hall of Fame**: in-memory (no restart do backend o HoF é zerado automaticamente)

---

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/simulation/neat_config.ini` | modificar | Mudar num_inputs de 16 para 20; atualizar contrato de I/O no comentário de cabeçalho |
| `backend/simulation/rtneat_wrapper.py` | modificar | Adicionar 4 labels a INPUT_LABELS; atualizar docstring do módulo |
| `backend/simulation/creature.py` | modificar | Estender array de inputs no método `think()` com os 4 valores de parede |
| `backend/tests/test_rtneat_wrapper.py` | modificar | Atualizar testes: num_inputs→20, input_keys→range(20), topologia Gen-0→128 conexões |

---

## Passos de implementação

### Passo 1 — Atualizar `neat_config.ini`

Alterar a linha 27 e expandir o contrato de I/O no cabeçalho:

```ini
# Antes:
#--- Config NEAT para Bibitinhos: 16 inputs, 4 outputs, feedforward, Geracao 0 conectada ---
# Contrato de I/O (ver docstring de rtneat_wrapper.py):
#   inputs 0-8   = 9 cones visuais (Visual_Sectors)
#   input 9      = Energy_Level
#   input 10     = Age_Degradation
#   input 11     = Hormonal_Level
#   input 12     = Biological_Clock
#   input 13     = Load_Sensor
#   inputs 14-15 = Kinetic_Feedback (2 canais)
#   output 0     = Motor_Forward
#   output 1     = Motor_Torque
#   output 2     = Action_Grab_Drop
#   output 3     = Action_Mate

num_inputs              = 16

# Depois:
#--- Config NEAT para Bibitinhos: 20 inputs, 4 outputs, feedforward, Geracao 0 conectada ---
# Contrato de I/O (ver docstring de rtneat_wrapper.py):
#   inputs 0-8   = 9 cones visuais (Visual_Sectors)
#   input 9      = Energy_Level
#   input 10     = Age_Degradation
#   input 11     = Hormonal_Level
#   input 12     = Biological_Clock
#   input 13     = Load_Sensor
#   inputs 14-15 = Kinetic_Feedback (2 canais: linear, angular)
#   inputs 16-19 = Wall_Proximity (4 canais: Norte, Sul, Oeste, Leste) — BIT-38
#   output 0     = Motor_Forward
#   output 1     = Motor_Torque
#   output 2     = Action_Grab_Drop
#   output 3     = Action_Mate

num_inputs              = 20
```

### Passo 2 — Atualizar `backend/simulation/rtneat_wrapper.py`

Expandir `INPUT_LABELS` com 4 novos labels:

```python
# Antes (linha 77-82):
INPUT_LABELS = [
    "Visual_Sector_0", "Visual_Sector_1", "Visual_Sector_2", "Visual_Sector_3",
    "Visual_Sector_4", "Visual_Sector_5", "Visual_Sector_6", "Visual_Sector_7",
    "Visual_Sector_8", "Energy_Level", "Age_Degradation", "Hormonal_Level",
    "Biological_Clock", "Load_Sensor", "Kinetic_Linear", "Kinetic_Angular",
]

# Depois:
INPUT_LABELS = [
    "Visual_Sector_0", "Visual_Sector_1", "Visual_Sector_2", "Visual_Sector_3",
    "Visual_Sector_4", "Visual_Sector_5", "Visual_Sector_6", "Visual_Sector_7",
    "Visual_Sector_8", "Energy_Level", "Age_Degradation", "Hormonal_Level",
    "Biological_Clock", "Load_Sensor", "Kinetic_Linear", "Kinetic_Angular",
    "Wall_North", "Wall_South", "Wall_West", "Wall_East",  # BIT-38
]
```

Se houver uma docstring de módulo descrevendo os inputs, adicionar um parágrafo sobre os 4 novos sensores de parede (BIT-38).

### Passo 3 — Atualizar `backend/simulation/creature.py`, método `think()`

Expandir o array de inputs com os 4 sensores de parede (linhas 164-179):

```python
# Antes:
def think(self, engine):
    """Roda a rede neural a 10 FPS (brain tick) e cacheia as 4 saidas de atuadores."""
    inputs = list(self.vision) + [
        min(self.energy / self.max_energy, 1.0),                                    # Energy_Level
        min(self.age / AGE_DEGRADATION_SCALE, 1.0),                                  # Age_Degradation
        0.0,                                                                         # Hormonal_Level (sistema nao existe ainda)
        0.0,                                                                         # Biological_Clock (sistema nao existe ainda)
        1.0 if self.is_holding else 0.0,                                             # Load_Sensor
        max(-1.0, min(1.0, self.body.velocity.length / KINETIC_LINEAR_NORM)),        # Kinetic_Feedback linear
        max(-1.0, min(1.0, self.body.angular_velocity / KINETIC_ANGULAR_NORM)),      # Kinetic_Feedback angular
    ]
    outputs = self.net.activate(inputs)
    self.motor_forward = outputs[0]
    self.motor_torque = outputs[1]
    self.action_grab_drop = outputs[2] > 0.0
    self.action_mate = outputs[3] > 0.0

# Depois:
def think(self, engine):
    """Roda a rede neural a 10 FPS (brain tick) e cacheia as 4 saidas de atuadores."""
    # BIT-38: Sensores de proximidade de parede (normalizados [0,1], 0=perto, 1=longe/limite)
    cx, cy = self.body.position.x, self.body.position.y
    wall_north = min(1.0, max(0.0, cy / engine.height))
    wall_south = min(1.0, max(0.0, (engine.height - cy) / engine.height))
    wall_west = min(1.0, max(0.0, cx / engine.width))
    wall_east = min(1.0, max(0.0, (engine.width - cx) / engine.width))
    
    inputs = list(self.vision) + [
        min(self.energy / self.max_energy, 1.0),                                    # Energy_Level
        min(self.age / AGE_DEGRADATION_SCALE, 1.0),                                  # Age_Degradation
        0.0,                                                                         # Hormonal_Level (sistema nao existe ainda)
        0.0,                                                                         # Biological_Clock (sistema nao existe ainda)
        1.0 if self.is_holding else 0.0,                                             # Load_Sensor
        max(-1.0, min(1.0, self.body.velocity.length / KINETIC_LINEAR_NORM)),        # Kinetic_Feedback linear
        max(-1.0, min(1.0, self.body.angular_velocity / KINETIC_ANGULAR_NORM)),      # Kinetic_Feedback angular
        wall_north,  # Índice 16: Wall_North
        wall_south,  # Índice 17: Wall_South
        wall_west,   # Índice 18: Wall_West
        wall_east,   # Índice 19: Wall_East
    ]
    outputs = self.net.activate(inputs)
    self.motor_forward = outputs[0]
    self.motor_torque = outputs[1]
    self.action_grab_drop = outputs[2] > 0.0
    self.action_mate = outputs[3] > 0.0
```

### Passo 4 — Atualizar testes em `backend/tests/test_rtneat_wrapper.py`

Atualizar 3 testes:

**Teste 1: `test_load_neat_config_parses_topology`**
```python
# Antes:
def test_load_neat_config_parses_topology():
    config = load_neat_config()
    assert config.genome_config.num_inputs == 16
    assert config.genome_config.num_outputs == 4
    assert config.genome_config.input_keys == [-(i + 1) for i in range(16)]
    assert config.genome_config.output_keys == [0, 1, 2, 3]

# Depois:
def test_load_neat_config_parses_topology():
    config = load_neat_config()
    assert config.genome_config.num_inputs == 20
    assert config.genome_config.num_outputs == 4
    assert config.genome_config.input_keys == [-(i + 1) for i in range(20)]
    assert config.genome_config.output_keys == [0, 1, 2, 3]
```

**Teste 2: `test_create_zero_genome_is_fully_connected`**
```python
# Antes:
def test_create_zero_genome_is_fully_connected():
    config = load_neat_config()
    genome = create_zero_genome(1, config)
    # BIT-36: num_hidden=2, full_direct → 16×6 input→{output,hidden} + 2×4 hidden→output = 104
    assert len(genome.connections) == 104
    # 4 outputs + 2 hidden = 6 (inputs são implícitos no neat-python 0.92)
    assert len(genome.nodes) == 6

# Depois:
def test_create_zero_genome_is_fully_connected():
    config = load_neat_config()
    genome = create_zero_genome(1, config)
    # BIT-38: num_hidden=2, full_direct → 20×6 input→{output,hidden} + 2×4 hidden→output = 128
    assert len(genome.connections) == 128
    # 4 outputs + 2 hidden = 6 (inputs são implícitos no neat-python 0.92)
    assert len(genome.nodes) == 6
```

**Teste 3: `test_network_activates_with_16_inputs_returns_4_outputs`** (mudar nome e argumentos)
```python
# Antes:
def test_network_activates_with_16_inputs_returns_4_outputs():
    config = load_neat_config()
    genome = create_zero_genome(1, config)
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    outputs = net.activate([0.0] * 16)
    assert len(outputs) == 4

# Depois:
def test_network_activates_with_20_inputs_returns_4_outputs():
    config = load_neat_config()
    genome = create_zero_genome(1, config)
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    outputs = net.activate([0.0] * 20)
    assert len(outputs) == 4
```

**Teste 4: `test_network_activate_wrong_input_size_raises` — sem mudança**
```python
def test_network_activate_wrong_input_size_raises():
    config = load_neat_config()
    genome = create_zero_genome(1, config)
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    with pytest.raises(RuntimeError):
        net.activate([0.0] * 5)  # Continua testando erro com número errado
```

**Teste 5: `test_exploration_pressure.py::test_gen0_genomes_are_all_seeded_to_move_forward` — atualizar linha 205**

Arquivo: `backend/tests/test_exploration_pressure.py`

```python
# Antes (linha 205):
outputs = net.activate([0.0] * 16)  # sem nada no cone de visao, sensores zerados

# Depois:
outputs = net.activate([0.0] * 20)  # sem nada no cone de visao, sensores zerados
```

---

## Contratos técnicos

### Backend (Simulação)

**Topologia NEAT:**
- **num_inputs**: 16 → 20
- **num_outputs**: 4 (inalterado)
- **Índices dos novos inputs**: 16, 17, 18, 19
- **Labels**: "Wall_North", "Wall_South", "Wall_West", "Wall_East"
- **Node keys (neat-python 0.92)**: input_keys = [-1, -2, ..., -20]; output_keys = [0, 1, 2, 3]

**Conexões Gen-0:**
- Antes: 16 inputs × 6 nodos (4 outputs + 2 hidden) + 2 hidden × 4 outputs = 16×6 + 2×4 = 104 conexões
- Depois: 20 inputs × 6 nodos + 2 hidden × 4 outputs = 20×6 + 2×4 = 128 conexões

**Fórmula de cálculo (precisão):**
```
wall_north = clamp(cy / height, 0.0, 1.0)
wall_south = clamp((height - cy) / height, 0.0, 1.0)
wall_west = clamp(cx / width, 0.0, 1.0)
wall_east = clamp((width - cx) / width, 0.0, 1.0)
```
Onde clamp(x, 0, 1) = max(0.0, min(1.0, x)).

**Semântica:**
- 0.0 = criatura está **na ou muito perto da parede**
- 1.0 = criatura está **na parede oposta** (máxima distância)
- Valor intermediário = proporção linear da distância

**Chamariz no engine:**
- `engine.width` e `engine.height` estão sempre disponíveis em `engine.py::SimulationEngine` (linhas 80-81)
- Chamada de `creature.think(engine)` em `engine.py::step()` (linha 341)
- O parâmetro `engine` é passado; acesso direto a dimensões é seguro

**Hall of Fame:**
- In-memory, zerado a cada restart do backend
- Não precisa de migração de dados (genomas antigos com 16 inputs não carregam no novo NEAT)

### Frontend (sem mudanças)

O painel de inspetor de rede (`CreatureDetailPanel` e `InspectorPanel`) já suporta renderização dinâmica baseada em `INPUT_LABELS`. Nenhuma alteração necessária no frontend; o inspetor exibirá automaticamente os 4 novos inputs quando o backend enviar o estado.

---

## Critérios de aceite

- [ ] `neat_config.ini` linha 27: `num_inputs = 20`
- [ ] `neat_config.ini` cabeçalho comentado: menciona 20 inputs e inputs 16-19 com Wall_*
- [ ] `rtneat_wrapper.py` INPUT_LABELS: 20 strings, incluindo "Wall_North", "Wall_South", "Wall_West", "Wall_East"
- [ ] `creature.py::think()`: calcula 4 valores de parede e os adiciona ao array de inputs antes de `net.activate()`
- [ ] `creature.py::think()`: comentário "#BIT-38" explicando a adição
- [ ] `test_rtneat_wrapper.py::test_load_neat_config_parses_topology()`: asserção num_inputs == 20, input_keys == [-(i+1) for i in range(20)]
- [ ] `test_rtneat_wrapper.py::test_create_zero_genome_is_fully_connected()`: asserção len(genome.connections) == 128
- [ ] `test_rtneat_wrapper.py::test_network_activates_with_20_inputs_returns_4_outputs()`: ativa com 20 inputs
- [ ] `pytest backend/tests/ -v`: todas as 100+ testes passam, incluindo testes existentes que activam redes (não quebra genomas Gen-1+)
- [ ] Simulação roda sem erros: backend inicia, cria Gen-0, criaturas nadam, visão/motores/ações funcionam
- [ ] Inspetor de rede no HUD: exibe os 4 novos labels (Wall_North, Wall_South, Wall_West, Wall_East) e seus valores entre [0, 1]

---

## Rollback

Se precisar reverter a mudança:

1. **neat_config.ini**: restaurar `num_inputs = 16` e comentário original do contrato
2. **rtneat_wrapper.py**: remover 4 labels "Wall_*" de INPUT_LABELS
3. **creature.py**: remover cálculo de wall_north/south/west/east e as 4 linhas no array de inputs
4. **test_rtneat_wrapper.py**: reverter as 3 asserções para num_inputs==16, input_keys==range(16), conexões==104
5. **Restart backend**: Hall of Fame é zerado automaticamente (in-memory)
6. **Testar**: `pytest backend/tests/ -v` deve passar; simulação deve rodar

---

## Notas de implementação

- **Ordem é crítica**: INPUT_LABELS[i] casa com input_keys[i] = -(i+1). Os 4 novos labels DEVEM estar nas posições 16, 17, 18, 19.
- **Clamping defensivo**: os sensores são clampados a [0, 1] para segurança, mesmo que (cx/width) já esteja em [0,1] naturalmente (proteção contra coordenadas fora-do-mundo ou divisão por zero hipotética).
- **Sem breaking changes**: criaturas Gen-0 e posteriores que nasçam APÓS a mudança usarão automaticamente 20 inputs. Genomas salvos com 16 inputs não carregam ao tentar ativar redes com 20 inputs, mas isso é comportamento correto (genomas antigos são descartados no restart).
- **Docstring de `think()`**: atualizar brevemente para mencionar que os 4 inputs de parede são adicionados (opcional, mas recomendado para manutenção).