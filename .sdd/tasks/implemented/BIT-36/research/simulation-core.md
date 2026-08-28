# Research — BIT-36: Camadas Ocultas na Rede Neural

## Arquivos examinados

- `backend/simulation/neat_config.ini`
- `backend/simulation/rtneat_wrapper.py`
- `backend/tests/test_rtneat_wrapper.py`

---

## Estado atual da config (`neat_config.ini`)

```ini
num_hidden          = 0
initial_connection  = full_direct
```

Com esses valores, `configure_new()` gera:
- **4 nós** (0..3 = outputs; inputs são implícitos no neat-python 0.92, chaves -1..-16)
- **64 conexões** (16 inputs × 4 outputs, todas diretas — medido)

---

## Comportamento do neat-python 0.92 com `num_hidden=2`

### `full_direct` + `num_hidden=2` (snippet executado)

```
nodes: [0, 1, 2, 3, 4, 5]
connections count: 104
```

Breakdown:
- 16 inputs × 6 destinos (4 outputs + 2 hidden) = **96 conexões** input→{output,hidden}
- 2 hidden × 4 outputs = **8 conexões** hidden→output
- Total: **104 conexões**

O `full_direct` com hidden presente cria conexões input→output E input→hidden E hidden→output. Os nós hidden recebem conexões de todos os inputs e projetam para todos os outputs. **Não há conexão hidden→hidden na Gen-0** (isso só apareceria por mutação `node_add_prob`).

### `full_nodirect` + `num_hidden=2` (controle)

```
connections count: 40
```

- 16 × 2 = 32 conexões input→hidden
- 2 × 4 = 8 conexões hidden→output
- Sem conexões input→output diretas

### Decisão: `full_direct` é o correto para BIT-36

O `full_direct` preserva as 64 conexões diretas input→output da Gen-0 (importante para os seeds de locomoção e food-taxis do BIT-20/21 continuarem funcionando imediatamente) e adiciona os caminhos mediados pelos nós ocultos. A evolução pode potencializar os hidden nodes quando eles trouxerem vantagem.

---

## Ativação da rede com `num_hidden=2`, `full_direct`

```python
net.activate([0.0] * 16)  # outputs count: 4  — contrato I/O preservado
```

A API `net.activate()` continua recebendo 16 inputs e retornando 4 outputs. Nenhum arquivo que usa `net.activate()` precisa ser alterado.

---

## `genome_to_dict()` — serialização de nós hidden

```python
hidden_nodes = [{'key': 4, 'type': 'hidden', 'bias': ..., 'activation': 'tanh'}, ...]
```

A função já serializa nós ocultos corretamente porque itera `genome.nodes.items()` e classifica por `key in gc.output_keys` (outputs) ou não (hidden). **Nenhuma alteração necessária em `rtneat_wrapper.py`.**

---

## Seeds BIT-20/BIT-21 — impacto

`create_zero_genome()` aplica seeds checando chaves específicas de nós:
- `MOTOR_FORWARD_NODE_KEY = 0` — nó output, sempre presente → sem impacto
- `ACTION_MATE_NODE_KEY = 3` — nó output, sempre presente → sem impacto
- food-taxis: conexões `(-(i+1), MOTOR_TORQUE_NODE_KEY=1)` — ainda existem em `full_direct` → sem impacto

Os seeds continuam funcionando. Os novos nós ocultos (chaves 4 e 5) nascem com bias N(0,1) e pesos N(0,1) — comportamento padrão do neat-python.

---

## Testes que quebram com a mudança

### `test_create_zero_genome_is_fully_connected`

```python
assert len(genome.connections) == 64   # falha → novo valor: 104
assert len(genome.nodes) == 4          # falha → novo valor: 6
```

Ambas as asserções verificam contagens absolutas hardcoded. **Precisam ser atualizadas.**

### Demais testes

- `test_load_neat_config_parses_topology` — verifica apenas num_inputs/num_outputs/input_keys/output_keys → não quebra
- `test_network_activates_with_16_inputs_returns_4_outputs` — verifica len(outputs)==4 → não quebra
- `test_network_activate_wrong_input_size_raises` — não depende de topologia → não quebra
- `test_organic_crossover_with_no_fitness_does_not_raise` — não depende de topologia → não quebra
- `test_mutate_genome_runs_without_error` — não depende de topologia → não quebra

---

## Resumo das decisões tomadas

| Decisão | Valor |
|---|---|
| `num_hidden` | 2 |
| `initial_connection` | `full_direct` (inalterado) |
| Conexões na Gen-0 | 104 (era 64) |
| Nós na Gen-0 | 6 (era 4, +2 hidden com chaves 4 e 5) |
| Alterações em `rtneat_wrapper.py` | Nenhuma |
| Alterações em `sensors.py` / `creature.py` | Nenhuma |
| Testes a atualizar | `test_create_zero_genome_is_fully_connected` (2 asserções) |
