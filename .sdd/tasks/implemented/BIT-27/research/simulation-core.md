# Research — simulation-core (BIT-27: Inspetor de rede neural)

> Relatório do sub-agente Explore sobre `backend/simulation/` para a demanda do inspetor de rede neural.

## Arquivos relevantes
- `backend/simulation/rtneat_wrapper.py` (linhas 1-148)
- `backend/simulation/creature.py` (linhas 153-180, 245-264)
- `backend/simulation/neat_config.ini` (16 inputs, 4 outputs, topologia)
- `backend/tests/test_rtneat_wrapper.py` (linhas 1-63)
- `frontend/src/components/InspectorPanel.jsx` (linhas 1-145)

## Conteúdo relevante

**Estrutura de dados NEAT:**
```python
# Em creature.py:154-157
self.config = load_neat_config()  # neat.Config (neat-python 0.92)
self.genome = genome or create_zero_genome(engine.next_genome_id(), self.config)  # DefaultGenome
self.id = self.genome.key  # inteiro único
self.net = neat.nn.FeedForwardNetwork.create(self.genome, self.config)  # rede compilada
```

**Atributos do `genome` (neat-python `DefaultGenome`):**
- `genome.key`: inteiro identificador único
- `genome.connections`: dict `{(in_node_key, out_node_key): ConnectionGene, ...}` — ConnectionGene tem `weight` (float), `enabled` (bool)
- `genome.nodes`: dict `{node_key: NodeGene, ...}` — NodeGene tem `activation` (string), `bias` (float), `response` (float)
- `genome.fitness`: float ou None (não usado em rtNEAT orgânico)

**Contrato de I/O da rede (16 inputs → 4 outputs)** (rtneat_wrapper.py:10-27 e neat_config.ini):
```
Inputs (índices 0-15 mapeiam para node keys -(i+1)):
  0-8:   Visual_Sectors (9 cones, setor 4 = frontal, [-1,1])
  9:     Energy_Level (0-1)
  10:    Age_Degradation (0-1)
  11:    Hormonal_Level (0-1, não implementado — sempre 0.0)
  12:    Biological_Clock (-1 a 1, não implementado — sempre 0.0)
  13:    Load_Sensor (0/1, grab/drop)
  14-15: Kinetic_Feedback (velocidade linear/angular)

Outputs (node keys 0-3):
  0: Motor_Forward ([-1,1], tanh)
  1: Motor_Torque ([-1,1], tanh)
  2: Action_Grab_Drop (binário via threshold > 0)
  3: Action_Mate (binário via threshold > 0)
```

**Topologia Gen 0 (neat_config.ini:25-32):**
```ini
num_inputs = 16
num_outputs = 4
num_hidden = 0
initial_connection = full_direct  # 16×4 = 64 conexões diretas input→output
feed_forward = True
```

**Método `think()` que executa a rede (creature.py:165-180):** monta os 16 inputs e chama `self.net.activate(inputs)` → 4 floats.

**Inspeção hoje (BIT-24, InspectorPanel.jsx):**
- Mostra dados básicos de `creature.to_dict()`: vision (9 barras), motor_forward/motor_torque (barras bipolares), action_mate/action_grab_drop (badges), idade, energia, cooldown
- **Não expõe**: topologia da rede, pesos de conexão, ativações de nós intermediários, genoma

**Serialização do genoma para JSON** (esboço validável):
```python
def genome_to_dict(genome):
    return {
        "key": genome.key,
        "fitness": genome.fitness,
        "nodes": {
            str(node_key): {
                "key": node_key,
                "bias": node.bias,
                "response": node.response,
                "activation": node.activation,
                "aggregation": node.aggregation,
            }
            for node_key, node in genome.nodes.items()
        },
        "connections": {
            f"{in_key}->{out_key}": {
                "in": in_key,
                "out": out_key,
                "weight": conn.weight,
                "enabled": conn.enabled,
            }
            for (in_key, out_key), conn in genome.connections.items()
        },
    }
```
Nota: `genome.nodes` contém apenas nós de saída e ocultos; os nós de input (keys negativas) existem só nas conexões e na config — o serializador precisa derivá-los de `config.genome_config.input_keys`.

**Ativações intermediárias:** `neat.nn.FeedForwardNetwork` não expõe ativações de nós por padrão. Alternativas: wrapper que faz cache de entradas/saídas por nó, ou implementação customizada com hook de ativações.

## O que precisa ser feito
1. Serializador `genome_to_dict(genome)` (topologia + pesos, JSON-safe), incluindo nós de input derivados da config
2. Expor a inspeção do genoma da criatura (método em `Creature` ou função utilitária)
3. Novo endpoint/mensagem para o frontend obter o genoma da criatura selecionada
4. Frontend: visualização de grafo da rede no InspectorPanel (nós como círculos, conexões como linhas; cor por sinal do peso, espessura por |peso|)
5. (Opcional) captura de ativações de nós durante `think()` — exige wrapper de rede

## Perguntas em aberto
1. Capturar ativações intermediárias ou só topologia estática + pesos?
2. Visualização estática ou dinâmica (atualizada a cada think)?
3. Histórico de mudanças do genoma ao longo do tempo? (exigiria persistência)
