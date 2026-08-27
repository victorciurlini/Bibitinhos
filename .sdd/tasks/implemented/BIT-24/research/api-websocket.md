# Research — BIT-22 / api-websocket

## Arquivos relevantes

- `backend/main.py` (77 linhas — lido integralmente)

## Conteúdo relevante para a demanda

- WebSocket **unidirecional hoje**: `websocket_endpoint` faz `await websocket.receive_text()`
  em loop e **descarta** o que recebe (comentário: "o client não precisará enviar muito").
  Toda a fundação de comandos cliente→servidor precisa nascer aqui.
- Broadcast: `ConnectionManager.broadcast(dict)` serializa com `json.dumps` e envia para
  todas as conexões; mensagem única `{"type": "state_update", ...engine.get_state()}` a 30 FPS.
- `engine` é singleton de módulo (`engine = SimulationEngine()`), acessível do endpoint.
- Sem rotas REST relevantes além do healthcheck `GET /`.

## O que precisa ser feito

Protocolo de comandos (JSON por cima do WebSocket existente — sem nova rota):

```jsonc
// cliente → servidor
{"action": "set_time_control", "paused": true, "speed": 2.0}
{"action": "drag", "phase": "start", "creature_id": 42}
{"action": "drag", "phase": "move",  "creature_id": 42, "x": 812.5, "y": 440.0}  // coords de MUNDO
{"action": "drag", "phase": "end",   "creature_id": 42}
```

- Parse com `json.loads` + dispatch por `action`; mensagem malformada/ação desconhecida é
  **ignorada silenciosamente com log** (`print`/logger), nunca derruba a conexão.
- Nenhuma resposta direta por comando: o efeito aparece no próximo `state_update`
  (que passa a ecoar `paused`/`speed`); protocolo permanece retrocompatível
  (cliente antigo que não envia nada continua funcionando).
- Validação no servidor (não confiar no cliente): speed ∈ {0.5, 1.0, 2.0, 4.0},
  coords clampadas ao mundo pelo engine, `creature_id` inexistente → no-op.

## Perguntas em aberto

- Nenhuma. (Decidido: sem framework de RPC, sem ack por mensagem — o state a 30 FPS é o ack.)
