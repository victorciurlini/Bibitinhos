# Research — api-websocket (BIT-26: Painéis de métricas populacionais)

> Relatório do sub-agente Explore sobre `backend/main.py` e protocolo WebSocket para a demanda de métricas.

## Arquivos relevantes
- `backend/main.py:81–100` — `simulation_loop()`: computa e envia state a 30 FPS
- `backend/main.py:94–96` — `state = engine.get_state(); state["type"] = "state_update"; await manager.broadcast(state)`
- `backend/simulation/engine.py:319–333` — `get_state()`
- `backend/simulation/creature.py:245–264` — `Creature.to_dict()`
- `backend/simulation/params.py:144–153` — `get_params()`
- `docs/arquitetura.md:64–101` — especificação do payload `state_update`

## Protocolo WebSocket atual

**Servidor → Cliente (broadcast 30 FPS)** — único tipo: `state_update`:
```json
{
  "type": "state_update",
  "paused": false, "speed": 1.0, "time": 123.4, "generation": 1,
  "width": 1400, "height": 1400,
  "vision_radius": 80.0, "vision_fov_degrees": 120.0,
  "creatures": [ {"id":1,"x":700,"y":700,"rotation":1.57,"radius":10,"color":"#22c55e",
    "energy":75,"max_energy":100,"age":12.3,"diet":"herbivore","life_stage":"ADULT",
    "reproduction_cooldown":0,"vision":[...9 floats...],"motor_forward":0.5,
    "motor_torque":0.2,"action_mate":false,"action_grab_drop":false} ],
  "foods": [ {"x":500,"y":600,"energy_value":32,"radius":5,"color":"#ffff00"} ],
  "oases": [ {"x":400,"y":400,"radius":150,"ttl":20,"ttl_fraction":0.667} ],
  "params": { "...22 parâmetros..." : 0 }
}
```

**Cliente → Servidor (BIT-24):** `set_time_control`, `drag` (start/move/end), `set_param`, `reset_params` — dispatch em `main.py:49–79`.

**REST:** apenas `GET /` (health check, `main.py:38–40`). **Não existe endpoint de estatísticas.**

## Observações
- Dados por criatura já permitem agregar no cliente: população, distribuição por fase, idade/energia médias, `len(foods)`, `len(oases)`
- Não há histórico entre ticks — snapshot puro
- Payload cresce ~1.5 KB por criatura; com 50+ criaturas × 30 FPS ≈ 2.25 MB/s — campo `metrics` agregado adiciona custo desprezível; série temporal completa a 30 FPS NÃO deve ir no broadcast
- Protocolo é aditivo/retrocompatível: campo novo no `state_update` não quebra cliente antigo

## O que precisa ser feito
1. Novo método no engine: `compute_population_metrics() -> dict` (ou classe `PopulationMetrics`)
2. Incluir campo `metrics` (agregados correntes) no `get_state()`/`state_update`
3. Para gráficos históricos: manter buffer no backend (amostragem ~1 s simulado) e expor bootstrap via REST (`GET /metrics/history`) — evita inflar o broadcast

## Perguntas em aberto
1. Quais métricas exatas? (população, natalidade/mortalidade, energia, fases…)
2. Agregar no servidor ou no cliente? (servidor: consistente com headless BIT-28 e reconexões)
3. Histórico: buffer em memória com que tamanho/frequência?
