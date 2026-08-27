# Research — BIT-22 / simulation-core

> Investigação direta pelo orquestrador (arquivos lidos integralmente nesta sessão) +
> validações ao vivo no venv (`pymunk 7.2.0`).

## Arquivos relevantes

- `backend/simulation/engine.py` — `SimulationEngine.step(dt)`, `get_state()`, handlers de colisão
- `backend/simulation/creature.py` — `Creature.__init__/think/update/to_dict`, `LifeStage`
- `backend/simulation/physics.py` — `PhysicsEngine`, espaço 2000×2000, damping 0.35
- `backend/main.py` — `simulation_loop()` (30 FPS fixo), `websocket_endpoint`

## Conteúdo relevante para a demanda

### Loop de tempo
- `main.py::simulation_loop` chama `engine.step(1/30.0)` + `broadcast` + `asyncio.sleep(1/30)`.
  O `dt` é **fixo** — não há mecanismo de pausa nem velocidade.
- O brain tick já é desacoplado dentro de `step()` via acumulador (`BRAIN_TICK_INTERVAL = 0.1s`),
  então acelerar a simulação repetindo `step(1/30)` N vezes mantém a proporção física/cérebro
  automaticamente. **Não** aumentar o `dt` por passo: `dt` grande degrada estabilidade do Pymunk
  (tunneling) e mudaria o comportamento da economia de energia (custos são `× dt`).

### Identidade da criatura
- `Creature.to_dict()` **não expõe id**. O cliente não tem como referenciar uma criatura.
- `self.genome.key` é único e monotônico (vem de `engine.next_genome_id()` tanto para Gen 0
  quanto para filhos sexuados/clones) — serve como id estável da criatura.

### Estado interno disponível para inspeção (já existe, só não é serializado)
- `energy`, `max_energy`, `age`, `life_stage`, `reproduction_cooldown`, `vision` (9 floats),
  `motor_forward`, `motor_torque`, `action_mate`, `action_grab_drop`, `is_alive`.
- `to_dict()` hoje só manda `x, y, rotation, radius, color, energy, diet, life_stage, vision`.

### Arrastar (validações ao vivo, pymunk 7.2.0)
- Teleporte de corpo dinâmico é suportado e estável: `body.position = (x, y)` +
  `body.velocity = (0, 0)`; `space.step()` seguinte respeita a nova posição.
- `space.point_query_nearest((x, y), max_distance, ShapeFilter())` funciona
  (retorna `PointQueryInfo` com `.shape`, `None` se nada no raio) — **mas não é necessário**:
  o cliente já recebe `x, y, radius` de cada criatura a 30 FPS e pode fazer hit-test local,
  enviando o `creature_id` escolhido. Evita round-trip e ambiguidade.
- Enquanto "segurada", a criatura precisa ter a posição re-fixada a cada `step()` (a física
  seguiria aplicando impulsos do motor dela); guardar alvo de drag no engine e re-aplicar.
- Efeitos colaterais aceitos: criatura arrastada continua pagando metabolismo/ociosidade
  (velocidade ~0) e pode colidir/comer/acasalar no caminho — comportamento emergente, não bug.
  Colisões dela durante o drag são inofensivas (handlers já validam energia/fase/cooldown).

### Concorrência
- `simulation_loop` (task asyncio) e `websocket_endpoint` (coroutine por conexão) rodam no
  **mesmo event loop** — comandos que só mutam flags/atributos do engine não precisam de lock.

## O que precisa ser feito

1. `engine.py`:
   - Atributos novos: `paused: bool = False`, `speed: float = 1.0`,
     `_held_creature: Creature|None = None`, `_drag_target: (float, float)|None`.
   - Métodos novos: `set_time_control(paused, speed)` (validar speed ∈ {0.5, 1.0, 2.0, 4.0}),
     `start_drag(creature_id) -> bool`, `drag_to(x, y)` (clamp ao mundo), `end_drag()`.
   - Em `step()`: se há criatura segurada e viva, re-fixar `body.position = _drag_target`
     e zerar `velocity` **antes** de `physics.step()`; se ela morreu/foi removida, soltar.
   - `get_state()`: adicionar `paused`, `speed` no topo.
2. `creature.py`:
   - `self.id = self.genome.key` no `__init__` (após criar o genoma).
   - `to_dict()` ganha: `id`, `age`, `max_energy`, `reproduction_cooldown`,
     `motor_forward`, `motor_torque`, `action_mate` (bool), `action_grab_drop` (bool).
3. `main.py`:
   - `simulation_loop` com acumulador de velocidade: `acc += engine.speed; while acc >= 1:
     engine.step(1/30); acc -= 1` (0.5x = passo frame sim frame não; 2x/4x = substeps com
     dt fixo). Pausado: não dá step, mas **continua broadcast** (o cliente precisa do estado
     e do eco de `paused`).
   - `websocket_endpoint`: parsear JSON recebido e despachar comandos (ver api-websocket.md).

## Perguntas em aberto

- Nenhuma bloqueante. (Decidido: velocidades discretas {0.5, 1, 2, 4}; hit-test no cliente;
  drag não isenta custos de energia.)
