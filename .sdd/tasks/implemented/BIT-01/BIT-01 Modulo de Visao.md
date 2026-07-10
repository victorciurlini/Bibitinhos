# Spec — BIT-01: Módulo de Visão (Sensor Tick a 10 FPS)

**Linear:** N/A (projeto Bibitinhos não usa Linear — ver memória `bibitinhos-workflow-sem-linear`)
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

Implementar o `SensorModule` de visão das criaturas: a cada 1/10s (10 FPS, dissociado do tick de física de 30 FPS), calcular quais dos 9 cones binários ao redor de cada `Creature` detectam algo (comida, outra criatura ou parede), usando `space.bb_query()` do Pymunk para achar vizinhos e `numpy.arctan2` para mapear o ângulo relativo de cada vizinho ao cone correspondente. O resultado alimenta os inputs 0-8 (`Visual_Sectors`) do contrato já documentado em `backend/simulation/rtneat_wrapper.py`.

Conectar a saída da visão a um `FeedForwardNetwork` real (rede NEAT) e trocar a locomoção por impulsos vindos do cérebro é **fora de escopo** desta task — fica para a próxima (conectar `net.activate()` aos atuadores).

## Abordagem técnica

Criar um módulo puro `backend/simulation/sensors.py` com `compute_vision(creature, engine) -> list[float]`, que consulta `engine.physics.space.bb_query()` num raio fixo ao redor da criatura, calcula o ângulo relativo de cada vizinho via `numpy.arctan2` e marca o cone correspondente como `1.0` (presença) ou deixa `0.0` (vazio) — sem diferenciar tipo de vizinho (comida/criatura/parede tratados igual, presença binária pura). `SimulationEngine.step()` ganha um acumulador de tempo que dispara essa função por criatura no máximo a cada 1/10s, dissociado do tick de física (30 FPS), guardando o resultado em `creature.vision`.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/sensors.py` | criar | `VISION_RADIUS`, `NUM_VISION_SECTORS=9`, função pura `compute_vision(creature, engine) -> list[float]` |
| `backend/simulation/creature.py` | modificar | `__init__`: adicionar `self.vision = [0.0] * 9`. `to_dict()`: incluir `"vision": self.vision` (debug/observabilidade, sem consumo no frontend ainda) |
| `backend/simulation/engine.py` | modificar | `__init__`: adicionar `self._brain_accumulator = 0.0` e `BRAIN_TICK_INTERVAL = 1/10`. `step(dt)`: acumular `dt`; quando `>= BRAIN_TICK_INTERVAL`, subtrair o intervalo e, para cada criatura viva, `creature.vision = compute_vision(creature, self)` |
| `backend/tests/test_sensors.py` | criar | Testes de `compute_vision()` cobrindo cone frontal, traseiro, lateral, vizinho fora do raio, nenhum vizinho, exclusão da própria criatura |

## Passos de implementação

> Passos 1-2 são independentes entre si; passo 3 depende do 1; passo 4 depende de 1, 2 e 3.

1. **Criar `backend/simulation/sensors.py`**:
   ```python
   import math
   import numpy as np
   import pymunk

   VISION_RADIUS = 200.0
   NUM_VISION_SECTORS = 9

   def compute_vision(creature, engine):
       vision = [0.0] * NUM_VISION_SECTORS
       space = engine.physics.space
       cx, cy = creature.body.position
       bb = pymunk.BB(cx - VISION_RADIUS, cy - VISION_RADIUS, cx + VISION_RADIUS, cy + VISION_RADIUS)
       shapes = space.bb_query(bb, pymunk.ShapeFilter())

       sector_width = 2 * np.pi / NUM_VISION_SECTORS

       for shape in shapes:
           if shape is creature.shape:
               continue
           nx, ny = shape.body.position
           dx, dy = nx - cx, ny - cy
           distance = math.hypot(dx, dy)
           if distance == 0 or distance > VISION_RADIUS:
               continue

           absolute_angle = np.arctan2(dy, dx)
           relative_angle = absolute_angle - creature.body.angle
           # normaliza para (-pi, pi]
           relative_angle = (relative_angle + np.pi) % (2 * np.pi) - np.pi
           # desloca meio setor para o cone 0 ficar centrado em "reto à frente"
           shifted = (relative_angle + sector_width / 2) % (2 * np.pi)
           index = int(shifted // sector_width) % NUM_VISION_SECTORS
           vision[index] = 1.0

       return vision
   ```
   Notas de implementação (validadas contra o ambiente real, pymunk 7.2.0):
   - `space.bb_query(bb, shape_filter)` recebe `shape_filter` obrigatório e retorna `list[Shape]`. `pymunk.ShapeFilter()` default (`categories=mask=0xFFFFFFFF`) casa com qualquer shape do space (criatura, comida, parede) sem precisar mexer em `physics.py`/`food.py`.
   - `pymunk.BB(left, bottom, right, top)` — ordem confirmada via `help(pymunk.BB)`.
   - Cone 0 cobre o intervalo `[-20°, +20°)` relativo ao `body.angle` da criatura (reto à frente); os demais cones seguem em sentido anti-horário (convenção padrão de ângulo do Pymunk/atan2).
   - Comida, outra criatura e paredes são tratados de forma idêntica (presença binária pura) — não há canal de "tipo" nos 9 cones. Isso é intencional: a spec original pede "9 cones binários", sem diferenciação de tipo.

2. **`creature.py`**: no `__init__`, logo após os atributos de "DNA" mockados, adicionar `self.vision = [0.0] * 9`. No `to_dict()`, adicionar a chave `"vision": self.vision` (lista serializável, útil para inspeção/debug futuro — não requer nenhuma mudança no frontend nesta task).

3. **`engine.py`**:
   - Import `from simulation.sensors import compute_vision` no topo.
   - `__init__`: adicionar `self._brain_accumulator = 0.0` e uma constante de módulo `BRAIN_TICK_INTERVAL = 1 / 10.0`.
   - Em `step(dt)`, após a atualização de física e **antes** do loop `for creature in self.creatures: creature.update(dt, self)` (ou depois — a ordem entre visão e movimento não importa nesta task, já que nada ainda consome `creature.vision` para mover), inserir:
     ```python
     self._brain_accumulator += dt
     if self._brain_accumulator >= BRAIN_TICK_INTERVAL:
         self._brain_accumulator -= BRAIN_TICK_INTERVAL
         for creature in self.creatures:
             if creature.is_alive:
                 creature.vision = compute_vision(creature, self)
     ```
   - Usar subtração (não reset a zero) para não acumular drift caso `dt` varie.

4. **`backend/tests/test_sensors.py`**: seguir o padrão de `backend/tests/test_rtneat_wrapper.py` (pytest simples, sem mocks pesados — instanciar `SimulationEngine` real é aceitável já que é rápido). Casos mínimos:
   - Nenhum vizinho → `compute_vision` retorna `[0.0] * 9`.
   - Uma `Food` posicionada diretamente à frente da criatura (mesmo ângulo do `body.angle`, dentro do raio) → cone 0 (índice 0) é `1.0`, demais `0.0`.
   - Uma `Creature` posicionada diretamente atrás (ângulo oposto) → cone índice 4 ou 5 (setor oposto, calcular pelo mesmo algoritmo do passo 1) é `1.0`.
   - Vizinho fora de `VISION_RADIUS` (ex. `VISION_RADIUS + 50` de distância) → nenhum cone ativado.
   - A própria criatura nunca ativa cone (garantido pela exclusão `shape is creature.shape`, mas testar explicitamente instanciando só 1 criatura sem vizinhos).

## Contratos técnicos

### Backend (Simulação)
- Função nova: `compute_vision(creature: Creature, engine: SimulationEngine) -> list[float]` em `backend/simulation/sensors.py`.
- Novo atributo: `Creature.vision: list[float]` (9 elementos, `0.0` ou `1.0`), atualizado no máximo a 10 Hz por `SimulationEngine.step()`.
- Constantes novas: `sensors.VISION_RADIUS = 200.0`, `sensors.NUM_VISION_SECTORS = 9`, `engine.BRAIN_TICK_INTERVAL = 1/10.0`.
- Sem mudança de schema WebSocket obrigatória; `to_dict()` ganha campo extra `"vision"` (retrocompatível — só adiciona chave, não quebra consumidores atuais do frontend).

## Critérios de aceite

- [ ] `compute_vision(creature, engine)` retorna sempre uma lista de exatamente 9 floats, cada um `0.0` ou `1.0`.
- [ ] Vizinho (Food ou Creature) diretamente à frente, dentro do raio, ativa o cone 0; nenhum outro cone é ativado nesse caso simples.
- [ ] Vizinho fora de `VISION_RADIUS` não ativa nenhum cone.
- [ ] Sem vizinhos, todos os 9 cones ficam `0.0`.
- [ ] A criatura nunca detecta a si mesma.
- [ ] `SimulationEngine.step()` só recalcula `creature.vision` quando o acumulador atinge `1/10s` — chamando `engine.step(1/30.0)` 3 vezes seguidas, `compute_vision` deve ter sido efetivamente aplicado no máximo 1 vez (verificável via monkeypatch/contador em teste, ou inferência indireta pelo acumulador).
- [ ] `pytest backend/tests/test_sensors.py` 100% verde.
- [ ] Nenhuma regressão: `pytest backend/tests/` continua 100% verde (inclui `test_rtneat_wrapper.py`).

## Rollback

Reverter/deletar `backend/simulation/sensors.py` e `backend/tests/test_sensors.py`; desfazer as duas pequenas alterações em `creature.py` (`self.vision` no `__init__` e chave `"vision"` no `to_dict()`) e em `engine.py` (import, acumulador, bloco do brain tick). Nenhuma migração de dados envolvida — mudança isolada, sem estado persistente.
