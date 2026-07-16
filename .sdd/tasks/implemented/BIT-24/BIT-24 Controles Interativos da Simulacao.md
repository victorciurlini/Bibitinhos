# Spec — BIT-24: Controles Interativos da Simulação (tempo, inspeção e arrasto)

> **Renumerada de BIT-22 → BIT-24:** o número 22 foi ocupado pela task "Reprodução Sexuada
> Emergente" já mergeada em `develop`. Esta é a fundação de comandos cliente→servidor de que o
> BIT-23 (parâmetros editáveis) depende.

**Linear:** N/A
**Risco:** medium
**Camada(s):** Múltiplas — Backend (Simulação) + API/WebSocket + Frontend

---

## Demanda

O developer precisa controlar e observar a simulação em vez de só assistir: **pausar/acelerar
o tempo** (0.5x–4x), **clicar num bibite** para ver seus status ao vivo (energia, idade, fase,
visão, saídas do cérebro) e **arrastar um bibite** para outro ponto do mapa. Hoje nada disso
existe: o WebSocket é unidirecional (o servidor descarta o que o cliente envia), o loop roda a
velocidade fixa e as criaturas nem sequer têm `id` no payload.

## Abordagem técnica

Criar a **fundação de comandos cliente→servidor** por cima do WebSocket existente (mensagens
JSON com campo `action`, despachadas em `main.py` — sem rota nova, retrocompatível) e três
recursos sobre ela: controle de tempo por **substeps de `dt` fixo** (nunca aumentar o `dt` —
estabilidade do Pymunk e economia de energia dependem dele), **inspeção 100% client-side**
(hit-test local usando `x, y, radius` que o cliente já recebe a 30 FPS; o backend só passa a
serializar `id` + campos de estado que já existem na `Creature`) e **arrasto por teleporte
re-fixado** (posição da criatura segurada é re-aplicada a cada frame de física; validado ao
vivo em pymunk 7.2.0). BIT-23 (parâmetros editáveis) depende do dispatch criado aqui.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | `self.id = genome.key`; `to_dict()` ganha id + campos de inspeção |
| `backend/simulation/engine.py` | modificar | Estado de tempo (`paused`/`speed`), métodos de drag, re-pin no `step()`, `get_state()` |
| `backend/main.py` | modificar | Loop com acumulador de velocidade; dispatch de comandos no `websocket_endpoint` |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | Mouse (clique/drag), transform invertida, highlight de seleção, composição dos overlays |
| `frontend/src/components/InspectorPanel.jsx` | criar | Painel overlay com status ao vivo do bibite selecionado |
| `frontend/src/components/TimeControls.jsx` | criar | Overlay ⏸/▶ + velocidades 0.5x/1x/2x/4x |
| `backend/tests/test_interactive_controls.py` | criar | Testes de tempo, drag e serialização |
| `docs/arquitetura.md` | modificar | Contrato WebSocket: comandos cliente→servidor + campos novos do state |

## Passos de implementação

> Passos 1–4 (backend) são sequenciais entre si apenas onde indicado; 5–8 (frontend) dependem
> de 1–4 prontos. Passo 9 valida.

### 1. `creature.py` — identidade e campos de inspeção

No `__init__`, **após** a criação do genoma (`self.genome = ...`):

```python
self.id = self.genome.key  # unico e monotonico via engine.next_genome_id()
```

`to_dict()` passa a incluir (mantendo todos os campos atuais):

```python
"id": self.id,
"age": self.age,
"max_energy": self.max_energy,
"reproduction_cooldown": self.reproduction_cooldown,
"motor_forward": self.motor_forward,
"motor_torque": self.motor_torque,
"action_mate": self.action_mate,
"action_grab_drop": self.action_grab_drop,
```

### 2. `engine.py` — controle de tempo

Constante de módulo + atributos no `__init__` + método:

```python
ALLOWED_SPEEDS = (0.5, 1.0, 2.0, 4.0)
```

```python
# no __init__:
self.paused = False
self.speed = 1.0
```

```python
def set_time_control(self, paused=None, speed=None):
    """Ajusta pausa/velocidade. Valores invalidos de speed sao ignorados (no-op)."""
    if paused is not None:
        self.paused = bool(paused)
    if speed is not None and float(speed) in ALLOWED_SPEEDS:
        self.speed = float(speed)
```

`get_state()` ganha, no topo do dict: `"paused": self.paused, "speed": self.speed`.

### 3. `engine.py` — arrasto (depende do passo 1 pelo `id`)

Atributos no `__init__`: `self._held_creature = None` e `self._drag_target = None`.

```python
def get_creature_by_id(self, creature_id):
    for c in self.creatures:
        if c.id == creature_id:
            return c
    return None

def start_drag(self, creature_id):
    creature = self.get_creature_by_id(creature_id)
    if creature is None or not creature.is_alive:
        return False
    self._held_creature = creature
    self._drag_target = (creature.body.position.x, creature.body.position.y)
    return True

def drag_to(self, x, y):
    """Move a criatura segurada. Aplica imediatamente (funciona tambem com a simulacao
    pausada, ja que o broadcast continua) e guarda o alvo para o re-pin de cada step."""
    if self._held_creature is None:
        return
    tx = max(0.0, min(float(self.width), float(x)))
    ty = max(0.0, min(float(self.height), float(y)))
    self._drag_target = (tx, ty)
    self._held_creature.body.position = self._drag_target
    self._held_creature.body.velocity = (0, 0)

def end_drag(self):
    self._held_creature = None
    self._drag_target = None
```

Em `step()`, **imediatamente antes** de `self.physics.step(dt)`: re-fixar a segurada (senão o
motor dela continuaria aplicando impulsos e ela escaparia da mão), soltando se ela morreu:

```python
        if self._held_creature is not None:
            if not self._held_creature.is_alive:
                self.end_drag()
            else:
                self._held_creature.body.position = self._drag_target
                self._held_creature.body.velocity = (0, 0)
```

**Decisões de design (não alterar):** a criatura arrastada continua pagando metabolismo e
imposto de ociosidade (velocidade ~0) e continua sujeita a colisões (comer/acasalar no caminho)
— comportamento emergente aceito, não é bug a "corrigir".

### 4. `main.py` — loop com velocidade + dispatch de comandos

`simulation_loop` substitui o `engine.step(1/30.0)` fixo por acumulador de substeps com
**`dt` fixo de 1/30** (0.5x = um step a cada duas iterações; 2x/4x = 2/4 substeps por
iteração). Pausado: nenhum step, **broadcast continua** (o cliente precisa do eco de
`paused`/`speed` e do estado corrente para drag/inspeção):

```python
async def simulation_loop():
    speed_accumulator = 0.0
    while True:
        try:
            if not engine.paused:
                speed_accumulator += engine.speed
                while speed_accumulator >= 1.0:
                    engine.step(1 / 30.0)
                    speed_accumulator -= 1.0
            state = engine.get_state()
            state["type"] = "state_update"
            await manager.broadcast(state)
        except Exception:
            import traceback
            traceback.print_exc()
        await asyncio.sleep(1 / 30.0)
```

`websocket_endpoint` deixa de descartar mensagens: parse JSON + dispatch. Mensagem malformada
ou ação desconhecida é ignorada (nunca derruba a conexão); campos são validados/coeridos —
não confiar no cliente:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            action = msg.get("action")
            if action == "set_time_control":
                engine.set_time_control(paused=msg.get("paused"), speed=msg.get("speed"))
            elif action == "drag":
                phase = msg.get("phase")
                if phase == "start":
                    engine.start_drag(msg.get("creature_id"))
                elif phase == "move":
                    try:
                        engine.drag_to(float(msg.get("x")), float(msg.get("y")))
                    except (TypeError, ValueError):
                        pass
                elif phase == "end":
                    engine.end_drag()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        engine.end_drag()  # cliente caiu no meio de um drag: solta a criatura
```

> Concorrência: `simulation_loop` e o endpoint rodam no mesmo event loop asyncio — mutação de
> flags/atributos do engine entre `await`s é segura, sem lock.

### 5. `SimulationCanvas.jsx` — fundação de interação

- Novos refs: `wsRef` (socket, para `sendCommand`), `viewTransformRef`
  (`{scale, offsetX, offsetY}` — **atualizado dentro do renderLoop** a cada frame, já que é lá
  que a transform é calculada), `selectedIdRef`, `dragRef` (`null` ou
  `{creatureId, startX, startY, moved}`).
- Helper `sendCommand(obj)`: `wsRef.current?.readyState === WebSocket.OPEN &&
  wsRef.current.send(JSON.stringify(obj))`.
- Helper `toWorld(e)`: usa `canvas.getBoundingClientRect()` + `viewTransformRef`:
  `worldX = (e.clientX - rect.left - offsetX) / scale` (idem Y).
- Helper `hitTest(worldX, worldY)`: varre `latestWorldState.current.creatures`, retorna a
  criatura de menor distância com `dist <= radius + 6` (slop em unidades de mundo), ou `null`.

### 6. Clique → seleção + highlight + `InspectorPanel.jsx`

- `mousedown`: guarda candidato (`dragRef = {creatureId: hit?.id, startX, startY, moved: false}`).
- `mouseup` com deslocamento de tela `< 5px`: é **clique** — `selectedIdRef.current =
  hit ? hit.id : null` (clicar no vazio deseleciona).
- No renderLoop, após desenhar as criaturas: se `selectedIdRef.current` existe no state,
  desenhar um anel branco (`ctx.arc`, raio `radius + 6`, `lineWidth 2/scale`); se o id sumiu
  do state (morreu), limpar `selectedIdRef`.
- **`InspectorPanel.jsx`** (novo): recebe via props um objeto `creature` (ou `null` → não
  renderiza). Overlay `position: absolute; top: 10px; right: 10px` no mesmo estilo do badge de
  status existente. Conteúdo: `#id`, fase + idade (s), barra de energia
  (`energy`/`max_energy`, cor da criatura), dieta, cooldown de reprodução, os **9 setores de
  visão** como barrinhas verticais (verde para sinal > 0, vermelho para < 0, altura ∝ |valor|)
  e as saídas do cérebro: barras bipolares para `motor_forward`/`motor_torque` e badges
  ligado/desligado para `action_mate`/`action_grab_drop`.
- **Atualização sem re-render a 30 FPS** (padrão do arquivo: state fica em ref): um
  `setInterval` de **150 ms** copia a criatura selecionada de `latestWorldState.current` para
  um `useState` (`inspectedCreature`), que alimenta o painel. Limpar o interval no cleanup do
  `useEffect`.

### 7. Arrasto (depende do passo 5)

- No `mousemove` com `dragRef` ativo: se deslocamento de tela ≥ 5px e `creatureId != null` e
  ainda não iniciou, enviar `{"action":"drag","phase":"start","creature_id":id}` e marcar
  `moved: true`; a partir daí, a cada evento, `{"action":"drag","phase":"move","creature_id":id,
  "x":worldX,"y":worldY}` (a própria taxa do `mousemove` é adequada; sem throttle extra).
- `mouseup`/`mouseleave` com drag iniciado: `{"action":"drag","phase":"end","creature_id":id}`
  e `dragRef = null`.
- Cursor: `grabbing` durante o drag (via style no canvas); demais estados podem ficar em
  `default` (hover-cursor `grab` é opcional, não é critério de aceite).

### 8. `TimeControls.jsx` (novo)

Overlay `position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%)`. Botões:
`⏸/▶` (toggle de `paused`) e `0.5x | 1x | 2x | 4x`. Cada clique envia
`{"action":"set_time_control","paused":...}` ou `{..., "speed": v}`. O botão ativo é destacado
com base em `paused`/`speed` **ecoados no state** (mesmo mecanismo de interval de 150 ms do
passo 6 — expor `paused`/`speed` num `useState` junto) — a UI nunca assume que o comando foi
aplicado; ela reflete o servidor.

`SimulationCanvas.jsx` compõe: `<InspectorPanel creature={inspectedCreature} />` e
`<TimeControls paused={...} speed={...} onCommand={sendCommand} />` dentro do `<div>` raiz.

### 9. `backend/tests/test_interactive_controls.py` (novo)

Importar constantes, nunca hardcodar (padrão do projeto). Cobrir no mínimo:

1. `set_time_control(paused=True)` seta a flag; `speed=2.0` seta; `speed=3.0` (inválida) é
   ignorada mantendo a anterior; `ALLOWED_SPEEDS == (0.5, 1.0, 2.0, 4.0)`.
2. `get_state()` contém `paused` e `speed`.
3. `to_dict()` contém `id` (== `genome.key`) e os campos novos do passo 1.
4. `start_drag` com id válido retorna `True`; com id inexistente retorna `False`; com criatura
   morta retorna `False`.
5. `drag_to` clampa a alvo fora do mundo (ex.: `(-50, 3000)` → `(0, 2000)`).
6. Criatura segurada permanece no `_drag_target` após `engine.step(1/30)` mesmo com
   `motor_forward = 1.0` (o re-pin vence o motor).
7. Criatura que morre durante o drag é solta automaticamente no `step()` seguinte
   (`_held_creature is None`).
8. `end_drag()` solta; após soltar, `step()` não re-fixa mais a posição.

## Contratos técnicos

### Backend (Simulação)

- `Creature.id: int` (== `genome.key`), atribuído no `__init__`.
- `SimulationEngine`: atributos `paused: bool`, `speed: float`, `_held_creature`,
  `_drag_target`; métodos `set_time_control(paused=None, speed=None)`,
  `get_creature_by_id(creature_id) -> Creature|None`, `start_drag(creature_id) -> bool`,
  `drag_to(x, y) -> None`, `end_drag() -> None`.
- Constante nova: `ALLOWED_SPEEDS = (0.5, 1.0, 2.0, 4.0)` em `engine.py`.
- Contrato de I/O do NEAT: **inalterado**.

### API/WebSocket

Cliente → servidor (novas; texto JSON no `/ws` existente):

```jsonc
{"action": "set_time_control", "paused": true}          // campos opcionais e independentes
{"action": "set_time_control", "speed": 2.0}            // speed ∈ {0.5, 1.0, 2.0, 4.0}
{"action": "drag", "phase": "start", "creature_id": 42}
{"action": "drag", "phase": "move",  "creature_id": 42, "x": 812.5, "y": 440.0}  // coords de MUNDO
{"action": "drag", "phase": "end",   "creature_id": 42}
```

Servidor → cliente (`state_update`, aditivo e retrocompatível): topo ganha
`"paused": bool, "speed": float`; cada criatura ganha `id, age, max_energy,
reproduction_cooldown, motor_forward, motor_torque, action_mate, action_grab_drop`.

### Frontend

- `SimulationCanvas.jsx`: refs `wsRef/viewTransformRef/selectedIdRef/dragRef`; helpers
  `sendCommand/toWorld/hitTest`; interval de 150 ms alimentando `inspectedCreature` +
  `paused/speed` em `useState`.
- `InspectorPanel.jsx`: props `{ creature }` — objeto do state ou `null`.
- `TimeControls.jsx`: props `{ paused, speed, onCommand }`.

## Critérios de aceite

- [ ] Clicar em ⏸ congela todas as criaturas (broadcast segue vivo; badge/painéis atualizam);
      ▶ retoma exatamente de onde parou.
- [ ] A 2x/4x a simulação avança visivelmente mais rápido **sem** mudança de comportamento
      físico (mesmo `dt` por step — sem tunneling, sem custos de energia distorcidos);
      a 0.5x, mais devagar.
- [ ] Velocidade fora de `ALLOWED_SPEEDS` enviada por um cliente malicioso é ignorada.
- [ ] Clicar num bibite abre o painel com id, fase, idade, barra de energia, cooldown, visão
      (9 setores com sinal) e saídas do cérebro, atualizando ao vivo (~150 ms); clicar no vazio
      fecha; se o bibite morre, painel fecha e o anel some sozinho.
- [ ] O bibite selecionado tem anel de destaque no canvas.
- [ ] Arrastar um bibite move-o em tempo real sob o cursor (inclusive com a simulação pausada)
      e, ao soltar, ele continua vivendo normalmente do novo ponto; arrastar não é disparado
      por cliques (threshold de 5px).
- [ ] Desconexão do cliente no meio de um drag solta a criatura no servidor.
- [ ] Cliente antigo (que não envia comandos) continua funcionando — protocolo aditivo.
- [ ] `pytest backend/tests/` 100% verde, incluindo os 8 cenários do passo 9.
- [ ] `docs/arquitetura.md` atualizado com o contrato novo.

## Rollback

Reverter `backend/simulation/creature.py`, `backend/simulation/engine.py`, `backend/main.py`,
`frontend/src/components/SimulationCanvas.jsx` e `docs/arquitetura.md`; deletar
`InspectorPanel.jsx`, `TimeControls.jsx` e `backend/tests/test_interactive_controls.py`.
Nenhuma migração de dados; protocolo é aditivo, então rollback não quebra clientes.
