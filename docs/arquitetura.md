# Arquitetura

> Documento vivo — descreve o sistema **como ele é hoje**, não a visão de produto.
> Última revisão: 2026-07-15 (pós BIT-20, com BIT-21 em implementação).

## Visão geral

```
┌──────────────────────────── backend (porta 8001) ────────────────────────────┐
│  main.py                                                                     │
│  ├─ FastAPI + CORS                                                           │
│  ├─ ConnectionManager (lista de WebSockets, broadcast JSON)                  │
│  └─ simulation_loop (asyncio, 30 FPS):                                       │
│        engine.step(1/30) → engine.get_state() → broadcast                    │
│                                                                              │
│  simulation/engine.py — SimulationEngine                                     │
│  ├─ PhysicsEngine (pymunk.Space 2000×2000, damping 0.35, paredes elásticas)  │
│  ├─ collision handlers: criatura×comida (comer), criatura×criatura (mate)    │
│  ├─ brain tick acumulado (10 FPS): compute_vision() + creature.think()       │
│  ├─ ciclo dos oásis (spawn/TTL) + spawn de comida + apodrecimento (TTL)      │
│  ├─ reprodução assexuada (varredura por frame, via de emergência)            │
│  └─ Jardim do Éden (failsafe anti-extinção)                                  │
└───────────────────────────────────────────────────────────────────────────────┘
                       │ WebSocket ws://localhost:8001/ws (30 FPS)
                       ▼
┌──────────────────────────── frontend (porta 5173) ───────────────────────────┐
│  React + Vite — SimulationCanvas.jsx                                          │
│  ├─ guarda o último state em ref; desenha via requestAnimationFrame           │
│  ├─ escala o mundo 2000×2000 para o canvas (letterbox centralizado)           │
│  └─ camadas: fundo aquático → oásis (fade por TTL) → cones de visão →         │
│     sprites tintados (bibity/egg/food) com rotação                            │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Os três ritmos

| Loop | Frequência | Onde | O que faz |
|---|---|---|---|
| Física + broadcast | 30 FPS | `main.py::simulation_loop` | `space.step()`, regras ecológicas, envia o state JSON |
| Brain tick | 10 FPS | `engine.step()` (acumulador) | `compute_vision()` + `net.activate()`; as 4 saídas ficam **cacheadas** e são reaplicadas a cada frame de física |
| Render | vsync do browser | `SimulationCanvas.jsx` | desenha o último state recebido (desacoplado do WebSocket) |

Decisões consolidadas (ver `docs/historico.md` e specs em `.sdd/tasks/implemented/`):

- **CPU-only.** GPU para NEAT foi analisada e rejeitada: topologias heterogêneas e
  esparsas não batcham; o custo de PCIe supera o ganho. Se houver gargalo, o caminho é
  Numba/NumPy vetorizado.
- **Sem multiprocessing.** Um único loop `asyncio` dá conta da população atual.
- **rtNEAT "orgânico".** `neat.Population.run()` (evolução geracional em lote) não é
  usado; genomas nascem, mutam e cruzam por eventos da simulação (colisões).

## Módulos do backend

| Módulo | Responsabilidade |
|---|---|
| `physics.py` | `create_space()`: espaço sem gravidade, `damping = 0.35` (arrasto de água, BIT-17), 4 paredes `Segment` com `elasticity = 1.0`. Categorias de colisão: `CREATURE=1`, `FOOD=2`, `WALL=4`. |
| `engine.py` | Orquestração e regras ecológicas. Constantes de reprodução vivem aqui. Handlers de colisão registrados no `__init__` via `space.on_collision`. |
| `creature.py` | Corpo (círculo r=10, massa 1.0), ciclo de vida por idade, economia de energia (BIT-20), atuadores (impulso frontal + torque + grip lateral), cor/escala visual (BIT-10/15). |
| `sensors.py` | `compute_vision()`: `bb_query` no raio de 80px + `arctan2`, 9 setores num cone frontal de 120°. Sinal com semântica (comida positiva, criatura negativa/positiva — ver `docs/simulacao.md`). |
| `rtneat_wrapper.py` | Config NEAT cacheada, `create_zero_genome()` (com seeds da Gen 0), `organic_crossover()`, `clone_genome()`, `mutate_genome()`. A docstring do módulo é a **fonte canônica do contrato de I/O** (16 in / 4 out). |
| `food.py` | Corpo **dinâmico** com 1% da massa da criatura (BIT-08: ação-reação real, comida é empurrável), TTL de 30s (apodrece, BIT-18). |
| `oasis.py` | `Oasis` é uma zona lógica (sem corpo Pymunk) que delimita onde comida pode nascer. Constantes do Jardim do Éden também vivem aqui. |
| `runner.py` | Modo headless (BIT-28): `populate()` (bootstrap da Gen 0, também usado pelo `startup_event`) e `HeadlessRunner` (loop síncrono em velocidade máxima com snapshots de `compute_metrics()`). Entry point: `backend/cli.py` (argparse; `--ticks/--creatures/--snapshot-interval/--seed/--output`) — ver `docs/desenvolvimento.md`. |

## Contrato WebSocket

Mensagem única, `type: "state_update"`, emitida a 30 FPS:

### Servidor → cliente (`state_update`, 30 FPS)

```jsonc
{
  "type": "state_update",
  "paused": false,           // BIT-24: eco do controle de tempo
  "speed": 1.0,              // BIT-24: ∈ {0.5, 1.0, 2.0, 4.0}
  "time": 123.4,             // segundos simulados
  "generation": 1,
  "width": 2000, "height": 2000,
  "vision_radius": 80.0,
  "vision_fov_degrees": 120.0,
  "creatures": [{
    "id": 42,                 // BIT-24: == genome.key, único e monotônico
    "x": 0.0, "y": 0.0,
    "rotation": 1.57,         // radianos
    "radius": 10.0,           // já multiplicado pela escala visual (idade/energia)
    "color": "#22c55e",       // gradiente de ciclo de vida (azul→verde→cinza→preto)
    "energy": 75.0,
    "max_energy": 100.0,      // BIT-24: para a barra de energia do inspetor
    "age": 12.3,              // BIT-24: idade em segundos simulados
    "diet": "herbivore",
    "life_stage": "ADULT",    // EGG | JUVENILE | ADULT | ELDER
    "reproduction_cooldown": 0.0,  // BIT-24
    "vision": [0.0, ...],     // 9 floats em [-1, 1]
    "motor_forward": 0.0,     // BIT-24: saída do cérebro (bipolar)
    "motor_torque": 0.0,      // BIT-24: saída do cérebro (bipolar)
    "action_mate": false,     // BIT-24: saída do cérebro (bool)
    "action_grab_drop": false // BIT-24: saída do cérebro (bool)
  }],
  "foods":  [{ "x": 0, "y": 0, "energy_value": 40.0, "radius": 5.0, "color": "#ffff00" }],
  "oases":  [{ "x": 0, "y": 0, "radius": 150.0, "ttl": 20.0, "ttl_fraction": 0.8 }],
  "metrics": {                 // BIT-26: agregados populacionais correntes (campo aditivo)
    "time": 123.4,             // == time_elapsed no momento do snapshot
    "population": 14,
    "stage_counts": { "EGG": 2, "JUVENILE": 3, "ADULT": 8, "ELDER": 1 },
    "avg_energy": 61.2,
    "avg_age": 40.7,
    "births_total": 12,        // acumulado desde o boot (só reprodução; respawn do Éden não conta)
    "deaths_total": 8,         // acumulado desde o boot
    "food_count": 87,
    "oases_count": 3
  }
}
```

### REST: `GET /metrics/history` (BIT-26)

Histórico das métricas populacionais, amostrado pelo engine a cada 1 s **simulado**
(`METRICS_SAMPLE_INTERVAL`) num `deque` com cap de 600 amostras (`METRICS_HISTORY_MAX`,
~10 min). Resposta: `{"history": [<amostras no mesmo formato do campo "metrics">]}` em
ordem cronológica. Usado só para **bootstrap** do painel de métricas do HUD (a série
sobrevive a reloads/reconexões do frontend); o broadcast de 30 FPS carrega apenas os
agregados correntes — a série temporal nunca infla o `state_update`.

### Cliente → servidor (BIT-24, texto JSON no `/ws` existente)

Fundação de comandos por mensagem JSON com campo `action`, despachada em `main.py`
(sem rota nova, **retrocompatível**: um cliente antigo que nada envia continua funcionando).
Mensagem malformada ou ação desconhecida é ignorada — nunca derruba a conexão; campos são
validados/coeridos no servidor (não se confia no cliente).

```jsonc
{"action": "set_time_control", "paused": true}          // campos opcionais e independentes
{"action": "set_time_control", "speed": 2.0}            // speed ∈ {0.5, 1.0, 2.0, 4.0}; inválido = no-op
{"action": "drag", "phase": "start", "creature_id": 42}
{"action": "drag", "phase": "move",  "creature_id": 42, "x": 812.5, "y": 440.0}  // coords de MUNDO
{"action": "drag", "phase": "end",   "creature_id": 42}
{"action": "inspect_creature", "creature_id": 42}       // BIT-27: pede o genoma (resposta unicast)
```

- **Controle de tempo** (`set_time_control`): pausa/velocidade por **substeps de `dt` fixo**
  (1/30) no `simulation_loop` — nunca aumentando o `dt` (estabilidade do Pymunk e a economia de
  energia dependem dele). Pausado, nenhum step roda mas o broadcast continua. A UI reflete o
  estado ecoado (`paused`/`speed`), nunca assume que o comando foi aplicado.
- **Arrasto** (`drag`): teleporte re-fixado. A posição da criatura segurada é re-aplicada a
  cada frame de física (imediatamente antes de `physics.step`), vencendo o motor. Funciona com a
  simulação pausada. A criatura arrastada continua pagando metabolismo/ociosidade e sujeita a
  colisões (comer/acasalar no caminho) — emergente, não é bug. Se ela morre durante o drag, é
  solta no `step()` seguinte; a desconexão do cliente também solta (`end_drag`).
- **Inspeção de genoma** (`inspect_creature`, BIT-27): o cliente pede o genoma **uma vez por
  seleção** (o genoma é imutável durante a vida da criatura) e o servidor responde em
  **unicast** — só ao socket que pediu, nunca no broadcast (o `state_update` fica intocado).

### Servidor → cliente (`creature_inspection`, unicast, BIT-27)

Resposta à ação `inspect_creature`. Serialização em `rtneat_wrapper.genome_to_dict()` (dono do
contrato NEAT): os nodes de **input** não existem em `genome.nodes` no NEAT 0.92 — vêm de
`config.genome_config.input_keys` (-1..-16), com labels do contrato (`INPUT_LABELS`/`OUTPUT_LABELS`).

```jsonc
{
  "type": "creature_inspection",
  "creature_id": 42,
  "genome": {                    // null se a criatura não existe mais
    "key": 42,
    "nodes": {
      "-1": { "key": -1, "type": "input",  "label": "Visual_Sector_0" },
      "0":  { "key": 0,  "type": "output", "label": "Motor_Forward", "bias": 0.49, "activation": "tanh" },
      "137":{ "key": 137,"type": "hidden", "bias": 0.0, "activation": "tanh" }  // hidden não tem label
    },
    "connections": [
      { "from": -1, "to": 0, "weight": 0.5, "enabled": true }
    ]
  }
}
```

No frontend, o grafo é renderizado em SVG puro por `NeuralNetworkViewer.jsx` (3 colunas fixas:
inputs → hidden → outputs), dentro da seção colapsável "Rede neural" do `InspectorPanel`.

## Frontend

`SimulationCanvas.jsx` é o único componente relevante:

- **Viewport**: `scale = min(canvas.w/2000, canvas.h/2000)`, com offset para centralizar.
- **Sprites**: `public/sprites/{bibity,egg,food}.png`; criaturas são tintadas com a cor
  do ciclo de vida via canvas offscreen (`source-atop`, alpha 0.55) e rotacionadas pelo
  ângulo do corpo. Fallback para círculos + linha de direção se o sprite não carregou.
- **Cones de visão** (BIT-12/14): os 9 setores do FOV de 120° são desenhados atrás do
  sprite, usando `vision_radius`/`vision_fov_degrees` vindos do state (mesma geometria
  de `sensors.py`).
- **Oásis** (BIT-18): gradiente radial verde cuja opacidade decai com `ttl_fraction`
  (fade-out natural antes de expirar).
- **Ambiente aquático** (BIT-17): fundo em gradiente vertical azul.

## Limitações conhecidas / dívidas

- `Hormonal_Level` (input 11) e `Biological_Clock` (input 12) são placeholders fixos
  em `0.0` — os sistemas não existem.
- `Action_Grab_Drop` (output 2) é lido do cérebro, mas não há mecânica de grab/carry
  nem `Weld Joint`; `Load_Sensor` (input 13) depende de `is_holding`, que nunca muda.
- Colisor da criatura é **círculo**, não cápsula (simplificação da visão original).
- Não há Docker nem CI (modo headless existe desde o BIT-28; painéis de métricas
  populacionais desde o BIT-26; inspetor de rede neural desde o BIT-27).
- `generation` no state é fixo em 1 (não há contagem real de gerações — evolução é
  contínua, não geracional).
