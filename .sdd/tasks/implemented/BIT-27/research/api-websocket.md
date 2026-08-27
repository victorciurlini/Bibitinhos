# Research — api-websocket (BIT-27: Inspetor de rede neural)

> Relatório do sub-agente Explore sobre `backend/main.py` e protocolo WebSocket para a demanda do inspetor.

## Arquivos relevantes
- `backend/main.py:49–79` — `websocket_endpoint()`: dispatch das ações do cliente (`set_time_control`, `drag`, `set_param`, `reset_params`). **Não há ação de inspeção hoje** — a seleção é 100% client-side (o frontend filtra `creatures[]` pelo id selecionado)
- `backend/simulation/creature.py:154–157` — `self.genome` (neat.DefaultGenome), `self.net` (FeedForwardNetwork), `self.id = genome.key`
- `backend/simulation/creature.py:165–180` — `think()`: 16 inputs → `net.activate()` → 4 outputs cacheados
- `backend/simulation/rtneat_wrapper.py:10–27` — contrato canônico de I/O (16 in / 4 out, labels)
- `backend/tests/test_interactive_controls.py:75–82` — testes dos campos de inspeção atuais

## Conteúdo relevante

**Estrutura do genoma (neat-python 0.92, `DefaultGenome`):**
- `genome.key` — int único
- `genome.connections` — dict `{(in_key, out_key): ConnectionGene}` com `.weight`, `.enabled`
- `genome.nodes` — dict `{node_key: NodeGene}` com `.bias`, `.response`, `.activation`, `.aggregation` — **apenas nós de saída e ocultos**; inputs (keys -1..-16) existem só nas conexões/config
- `genome.fitness` — float/None (não usado no rtNEAT orgânico)

**O que o `state_update` já envia da criatura:** apenas saídas cacheadas (`motor_forward`, `motor_torque`, `action_mate`, `action_grab_drop`) e `vision[9]`. Nenhuma topologia/pesos.

**O genoma é imutável durante a vida da criatura** → basta enviar uma vez por seleção, não a cada frame.

## Proposta de protocolo (aditivo, retrocompatível)

Cliente → Servidor:
```json
{"action": "inspect_creature", "creature_id": 42}
```

Servidor → Cliente (**unicast**, via `websocket.send_json`, não broadcast):
```json
{
  "type": "creature_inspection",
  "creature_id": 42,
  "genome": {
    "nodes": {
      "-1": {"key": -1, "type": "input",  "label": "Visual_Sector_0"},
      "0":  {"key": 0,  "type": "output", "label": "Motor_Forward", "bias": 0.8, "activation": "tanh"},
      "20": {"key": 20, "type": "hidden", "bias": -0.3, "activation": "tanh"}
    },
    "connections": [
      {"from": -1, "to": 0, "weight": 0.5, "enabled": true}
    ]
  }
}
```
Se `creature_id` não existe (morreu), responder `{"type":"creature_inspection","creature_id":42,"genome":null}`.

## O que precisa ser feito
1. `genome_to_dict(genome, config)` no backend (incluindo nós de input derivados de `config.genome_config.input_keys`, com labels do contrato do rtneat_wrapper)
2. Nova ação `inspect_creature` no dispatch do `websocket_endpoint` com resposta unicast
3. Testes: serialização (Gen 0 = 20 nós, 64 conexões) e round-trip da mensagem

## Perguntas em aberto
1. Enviar `inputs`/`outputs` correntes junto? (já chegam via `state_update` — desnecessário)
2. Ativações de nós ocultos em tempo real? (FeedForwardNetwork não expõe; exigiria wrapper — candidato a ficar fora de escopo)
