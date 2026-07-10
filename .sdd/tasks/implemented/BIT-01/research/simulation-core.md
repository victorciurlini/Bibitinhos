## Arquivos relevantes

- `backend\simulation\creature.py` (89 linhas) — classe `Creature`, sem cérebro/sensores hoje
- `backend\simulation\engine.py` (67 linhas) — `SimulationEngine.step(dt)`, loop único de atualização
- `backend\simulation\physics.py` (41 linhas) — `PhysicsEngine`, `create_space()`, constantes de colisão
- `backend\simulation\food.py` (40 linhas) — classe `Food`, corpo estático
- `backend\main.py` (78 linhas) — loop asyncio único a 30 FPS (linhas 59-69)
- `backend\simulation\rtneat_wrapper.py` — docstring define o contrato de I/O do cérebro (16 inputs, 4 outputs), incluindo `Visual_Sectors[0..8]`
- `backend\simulation\neat_config.ini` — `num_inputs=16`, cones visuais mapeados para inputs 0-8
- `README.md` (linhas 150-255) — especificação do "Sistema Cognitivo Evolutivo" (§6) e "SensorModule" (§7.2)
- `.sdd\tasks\implemented\BIT-00\research\backend-sim.md` — pesquisa anterior (pré-BIT-00), desatualizada quanto ao loader

## Conteúdo relevante para a demanda

### `creature.py` — classe `Creature` (estado atual)
Atributos físicos:
```python
self.body = pymunk.Body(mass, moment)          # linha 19
self.body.position = (start_x, start_y)         # linha 23
self.body.angle = random.uniform(0, math.pi*2)  # linha 24
self.shape = pymunk.Circle(self.body, 10.0)     # linha 27
self.shape.filter = pymunk.ShapeFilter(categories=1)  # linha 30 (categoria=CREATURE, SEM collision_type definido)
```
Atributos "DNA" mockados: `self.speed`, `self.size`, `self.energy`, `self.max_energy`, `self.diet` (linhas 37-41). `self.life_stage` é `LifeStage` Enum (EGG/JUVENILE/ADULT/ELDER, linhas 6-10).

`update(self, dt, engine)` (linhas 47-70): incrementa idade, promove estágio de vida por idade fixa (mock), aplica impulso constante para frente (`apply_impulse_at_local_point`), consome energia proporcional a `speed`/`size`, mata a criatura se `energy <= 0`.

**Não existe** nenhum atributo de cérebro (`self.net`/`self.genome`), nenhum sensor, nenhuma chamada a `net.activate()`. O `update()` não recebe nem usa `Visual_Sectors` — o movimento é puramente determinístico (linha reta acelerando).

### `physics.py` — constantes de colisão
```python
COLLISION_CATEGORY_CREATURE = 1
COLLISION_CATEGORY_FOOD = 2
COLLISION_CATEGORY_WALL = 4
```
Essas são **categorias de filtro de colisão física** (`pymunk.ShapeFilter(categories=...)`), usadas só para decidir quem colide fisicamente com quem — **não são `collision_type`** (atributo separado do Pymunk usado para handlers de colisão / identificação em queries). Nem `creature.shape` nem `food.shape` definem `.collision_type` hoje; `food.py` linha 17 hardcoda `categories=2` sem importar a constante de `physics.py` (número mágico duplicado).

`PhysicsEngine.step(dt)` só chama `self.space.step(dt)` — nenhuma lógica de sensor, nenhum `bb_query` hoje.

### `food.py` — classe `Food`
Corpo estático (`pymunk.Body.STATIC`), raio 5.0, `energy_value=20.0` default. `consume()` remove do space e marca `is_active = False`. Nenhum vínculo com "visão" — é só um objeto físico estático.

### `engine.py` — `SimulationEngine.step(dt)`
```python
def step(self, dt):
    self.time_elapsed += dt
    self.physics.step(dt)                       # física
    if len(self.foods) < 50:
        if random.random() < 0.05:
            ... self.add_food(Food(self, x, y))  # spawn
    for creature in self.creatures:
        creature.update(dt, self)                # 1 único tick para tudo
    ... remoção de mortos/comida consumida, respawn "Jardim do Éden"
```
Existe **um único tick** (`dt` fixo) para física + atualização de criaturas — não há distinção entre "tick de física" e "tick de cérebro/sensores". `engine.creatures` e `engine.foods` são as únicas listas — é aqui que qualquer `bb_query` precisaria iterar para separar vizinhos por tipo.

### `main.py` — loop principal (linhas 59-69)
```python
async def simulation_loop():
    while True:
        try:
            engine.step(1 / 30.0)
            state = engine.get_state()
            state["type"] = "state_update"
            await manager.broadcast(state)
        except Exception as e:
            traceback.print_exc()
        await asyncio.sleep(1 / 30.0)  # 30 FPS
```
Frequência única de **30 FPS** (`dt=1/30`), usada tanto para física quanto para broadcast via WebSocket. **Não há separação de tick para o cérebro (brain tick)** — tudo roda no mesmo `asyncio.sleep`.

### Contrato já definido em `rtneat_wrapper.py` / `neat_config.ini`
- Inputs 0-8: `Visual_Sectors` — 9 cones binários de visão (Gen 0: só 3 ativos, resto = -1.0)
- Input 9: `Energy_Level`, 10: `Age_Degradation`, 11: `Hormonal_Level`, 12: `Biological_Clock`, 13: `Load_Sensor`, 14-15: `Kinetic_Feedback`
- Outputs: `Motor_Forward`, `Motor_Torque`, `Action_Grab_Drop`, `Action_Mate`

`neat_config.ini` tem `num_inputs=16`, `num_outputs=4`, `feed_forward=True`, `initial_connection=full_direct`.

### README.md §7.2 — `SensorModule` (especificação, não implementada)
```
Bibite (Extends Entity)
├─ Metabolism
├─ NeuralBrain → Feedforward rtNEAT
├─ SensorModule → Colisões Pymunk → arrays escalares
└─ ActuatorModule → apply_force()/torque
```
README Milestone 2 ("O Despertar Sensorial") pede implementar `SensorModule`, convertendo visão/colisões em arrays estruturados, com "rede neural fixa provisória" antes do rtNEAT completo (Milestone 3) — ou seja, **o escopo do módulo de visão não exige, por si só, ligar a rede NEAT real**; pode ser testado com um consumidor provisório dos 9 valores.

## O que precisa ser feito

1. **Adicionar `collision_type` real aos shapes**: hoje `creature.py` e `food.py` só usam `categories` (filtro de colisão física), não `shape.collision_type`. Para o `bb_query()` filtrar por tipo (criatura vs comida vs parede) de forma limpa, definir `shape.collision_type = COLLISION_CATEGORY_CREATURE`/`FOOD` (reaproveitando as constantes já existentes em `physics.py`) em ambas as classes, e importar essas constantes em `food.py` em vez do número mágico `2`.

2. **Criar módulo de sensores dedicado**: `backend/simulation/sensors.py` com função pura `compute_vision(creature, engine) -> list[float]` (9 floats), seguindo o padrão de funções puras já usado em `rtneat_wrapper.py` — facilita testar sem instanciar a simulação inteira.

3. **Uso do `space.bb_query()`**: `engine.physics.space.bb_query(bb, shape_filter)` retorna um **set de `Shape`** dentro do bounding box informado — não filtra por raio circular real nem por ângulo, então é preciso:
   - Construir uma `pymunk.BB` centrada na posição da criatura com um raio de visão (nova constante `VISION_RADIUS`).
   - Iterar sobre os shapes retornados, excluir o próprio `shape` da criatura, obter `shape.body.position` de cada vizinho.
   - Calcular vetor relativo `(dx, dy) = neighbor.position - creature.body.position`, ângulo absoluto `theta = np.arctan2(dy, dx)`, subtrair `creature.body.angle` para obter ângulo relativo, normalizar para `[-pi, pi]`.
   - Mapear o ângulo relativo para um dos 9 setores (cones) — **FOV exato não especificado no README** (ver perguntas em aberto).
   - Marcar o cone correspondente como binário (presença/ausência).

4. **Separar brain tick (10 FPS) do tick de física (30 FPS)**: hoje `main.py` só tem um loop a `1/30`. Abordagem recomendada (mais simples, sem duplicar loops asyncio): `SimulationEngine` mantém um acumulador de tempo interno; a cada `engine.step(dt)` chamado a 30 FPS, incrementa o acumulador, e dispara o cálculo de sensores + decisão de atuadores por criatura somente quando o acumulador ultrapassar `1/10` s, resetando-o. O resultado do cérebro (motor forward/torque) fica em cache na própria `Creature` e é reaplicado a cada tick de física até a próxima atualização do cérebro.

5. **Dependência de `Creature` ter cérebro instanciado**: para o valor de visão "servir para algo" fim-a-fim, a criatura precisa de `self.net` (via `neat.nn.FeedForwardNetwork.create(genome, config)`, usando `load_neat_config()` já existente em `rtneat_wrapper.py` desde BIT-00). **Isso pode ficar fora do escopo do BIT-01** se o objetivo for só entregar `compute_vision()` testável isoladamente — a integração com o `FeedForwardNetwork` já está planejada como próxima tarefa (BIT-02) na memória do projeto.

6. **Testes**: seguir o padrão de `backend/tests/test_rtneat_wrapper.py` — criar `backend/tests/test_sensors.py` cobrindo: nenhum vizinho (9 cones vazios), 1 comida à frente (cone frontal ativo), 1 criatura atrás (cone traseiro ativo), vizinho fora do raio de visão (não ativa cone), parede dentro do raio (decidir se conta).

## Perguntas em aberto

- **FOV exato dos 9 cones**: 360° (40° cada) ou campo de visão frontal restrito? README não especifica — precisa decisão de design (proposta: 360° por simplicidade e por não haver menção de "para trás é cego" na spec).
- **Semântica do valor binário**: README diz "resto recebe -1.0" para cones desativados em Gen 0 (fora do escopo — é sobre como o genoma inicial ignora inputs, não sobre o sensor em si). Para o sensor puro: propor `1.0` = há entidade no cone, `0.0` = cone vazio (binário estrito, sem estado "desativado" no nível do sensor).
- **Alcance de visão (`VISION_RADIUS`)**: não há constante hoje nem no README. Precisa ser definida (proposta: valor fixo simples nesta task, ex. 150px, ajustável depois por life_stage se necessário — não bloquear o BIT-01 nisso).
- **Diferenciação de tipo dentro do cone**: se comida e criatura caem no mesmo cone, o sinal binário não diferencia — aceitável para o escopo de "9 cones binários" da spec original (a diferenciação fica para outros inputs, ex. `Load_Sensor`), então não é bloqueante.
- **Paredes no `bb_query`**: as 4 paredes do mapa também têm shapes no mesmo space; decidir se contam como "obstáculo visível" nos 9 cones (proposta: sim, tratar paredes igual a qualquer objeto físico para fins de visão — evita colisão às cegas).
