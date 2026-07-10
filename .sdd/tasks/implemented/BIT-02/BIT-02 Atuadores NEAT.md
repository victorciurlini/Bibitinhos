# Spec — BIT-02: Atuadores NEAT (conectar FeedForwardNetwork aos motores)

**Linear:** N/A (ver memória `bibitinhos-workflow-sem-linear`)
**Risco:** medium
**Camada(s):** Backend (Simulação)

---

## Demanda

Substituir a locomoção hardcoded da `Creature` (impulso fixo para frente) pela saída real de uma rede `neat.nn.FeedForwardNetwork`, construída a partir do genoma da criatura (via `rtneat_wrapper.load_neat_config()`/`create_zero_genome()`, já existentes desde BIT-00). A rede roda no brain tick de 10 FPS (mesmo acumulador introduzido em BIT-01), lendo os 9 cones de visão + 7 sensores adicionais, e produz 4 saídas: `Motor_Forward`, `Motor_Torque`, `Action_Grab_Drop`, `Action_Mate`. As duas primeiras passam a mover fisicamente a criatura (impulso/torque no `pymunk.Body`, reaplicados a cada frame de física de 30 FPS); as duas últimas são apenas armazenadas como flags cacheadas — seus efeitos de jogo (segurar objeto, acasalar) **não fazem parte desta task**.

## Abordagem técnica

Cada `Creature` ganha `self.genome`/`self.net` (criados no `__init__`, com genoma zero por padrão ou um genoma injetado via parâmetro — abrindo caminho para reprodução futura). Um novo método `Creature.think(engine)` monta o vetor de 16 inputs e chama `net.activate()`, guardando os 4 outputs em atributos cacheados. `think()` é chamado a 10 FPS, dentro do mesmo bloco de acumulador de tempo que BIT-01 introduziu em `SimulationEngine.step()` (logo após `compute_vision`). `Creature.update()` (30 FPS) passa a aplicar os outputs cacheados em vez do impulso fixo anterior.

**Depende de BIT-01** (usa `creature.vision`, calculado lá) e **deve ser implementada depois do merge da BIT-01** para evitar conflito de edição simultânea em `creature.py`/`engine.py` (mesmo diretório de trabalho, branches diferentes).

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | `__init__` ganha `genome=None`; cria `self.config`/`self.genome`/`self.net`; novos atributos `self.motor_forward/torque`, `self.action_grab_drop/mate`, `self.is_holding`; novo método `think(engine)`; `update()` reescrito para usar os outputs cacheados |
| `backend/simulation/engine.py` | modificar | `__init__`: `self._next_genome_id = 0`; novo método `next_genome_id()`; bloco do brain tick (de BIT-01) ganha chamada a `creature.think(self)` logo após `compute_vision` |
| `backend/tests/test_creature_think.py` | criar | Testes de `Creature.think()`/`update()`: rede roda sem erro com 16 inputs, outputs no range esperado, energia é descontada proporcional à magnitude do motor |

## Passos de implementação

> Passo 1 é independente; passos 2-3 dependem do 1; passo 4 depende de 1-3.

1. **`creature.py` — inicialização do cérebro**, no `__init__`, após os atributos de "DNA":
   ```python
   from simulation.rtneat_wrapper import load_neat_config, create_zero_genome
   import neat

   AGE_DEGRADATION_SCALE = 60.0
   MOTOR_TORQUE_SCALE = 20.0
   KINETIC_LINEAR_NORM = 200.0
   KINETIC_ANGULAR_NORM = 10.0

   # dentro de __init__(self, engine, x=None, y=None, genome=None):
   self.config = load_neat_config()
   self.genome = genome if genome is not None else create_zero_genome(engine.next_genome_id(), self.config)
   self.net = neat.nn.FeedForwardNetwork.create(self.genome, self.config)

   self.motor_forward = 0.0
   self.motor_torque = 0.0
   self.action_grab_drop = False
   self.action_mate = False
   self.is_holding = False  # placeholder p/ Load_Sensor; mecanica de grab fora de escopo
   ```
   Validado ao vivo neste ambiente (pymunk 7.2.0 / neat-python 0.92): `create_zero_genome` + `FeedForwardNetwork.create` + `net.activate([0.0]*16)` retornam 4 floats sem erro.

2. **`engine.py` — genome id + hook do brain tick**:
   ```python
   # __init__:
   self._next_genome_id = 0

   def next_genome_id(self):
       self._next_genome_id += 1
       return self._next_genome_id
   ```
   No bloco já existente (de BIT-01) dentro de `step(dt)`:
   ```python
   self._brain_accumulator += dt
   if self._brain_accumulator >= BRAIN_TICK_INTERVAL:
       self._brain_accumulator -= BRAIN_TICK_INTERVAL
       for creature in self.creatures:
           if creature.is_alive:
               creature.vision = compute_vision(creature, self)
               creature.think(self)   # <-- linha nova
   ```

3. **`creature.py` — método `think(self, engine)`**:
   ```python
   def think(self, engine):
       inputs = list(self.vision) + [
           min(self.energy / self.max_energy, 1.0),                                    # Energy_Level
           min(self.age / AGE_DEGRADATION_SCALE, 1.0),                                  # Age_Degradation
           0.0,                                                                         # Hormonal_Level (nao implementado)
           0.0,                                                                         # Biological_Clock (nao implementado)
           1.0 if self.is_holding else 0.0,                                             # Load_Sensor
           max(-1.0, min(1.0, self.body.velocity.length / KINETIC_LINEAR_NORM)),        # Kinetic_Feedback (linear)
           max(-1.0, min(1.0, self.body.angular_velocity / KINETIC_ANGULAR_NORM)),      # Kinetic_Feedback (angular)
       ]
       outputs = self.net.activate(inputs)
       self.motor_forward = outputs[0]
       self.motor_torque = outputs[1]
       self.action_grab_drop = outputs[2] > 0.0
       self.action_mate = outputs[3] > 0.0
   ```
   `Hormonal_Level` e `Biological_Clock` ficam fixos em `0.0` — não existe sistema de hormônio/relógio biológico na simulação; documentar no código como placeholder reservado para task futura (não inventar o sistema aqui).

4. **`creature.py` — `update(self, dt, engine)` reescrito**:
   ```python
   def update(self, dt, engine):
       if not self.is_alive:
           return
       self.age += dt
       if self.age > 30:
           self.life_stage = LifeStage.ELDER
       elif self.age > 10:
           self.life_stage = LifeStage.ADULT
       elif self.age > 2:
           self.life_stage = LifeStage.JUVENILE

       if self.life_stage != LifeStage.EGG:
           forward_impulse = (self.motor_forward * self.speed * dt, 0)
           self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
           self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE

       motor_cost = abs(self.motor_forward) * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05
       self.energy -= dt * motor_cost
       if self.energy <= 0:
           self.is_alive = False
   ```
   Mantém a mesma estrutura/coeficientes de energia de antes, só troca "sempre no máximo" por "proporcional à saída real do motor".

5. **`main.py`**: nenhuma mudança necessária — `Creature(engine)` continua funcionando (genome=None cria genoma zero automaticamente).

6. **`backend/tests/test_creature_think.py`**: instanciar `SimulationEngine` real + `Creature`, chamar `creature.think(engine)` diretamente (sem depender do acumulador de tempo) e verificar:
   - Não lança exceção com uma criatura recém-criada (vision ainda `[0.0]*9`).
   - `motor_forward`/`motor_torque` ficam dentro de aproximadamente `[-1, 1]` (tanh).
   - `action_grab_drop`/`action_mate` são `bool`.
   - Chamar `creature.update(dt, engine)` após `think()` reduz `creature.energy` (comparado ao valor anterior), e a redução é proporcional a `abs(motor_forward)`/`abs(motor_torque)` (testar com um genoma cujo output é conhecido, ou apenas checar que energia nunca aumenta).

## Contratos técnicos

### Backend (Simulação)
- `Creature.__init__(self, engine, x=None, y=None, genome=None)` — novo parâmetro opcional `genome`, retrocompatível (chamadas existentes em `main.py`/`engine.py` continuam funcionando sem alteração).
- `Creature.think(engine) -> None` — efeito colateral: atualiza `self.motor_forward`, `self.motor_torque`, `self.action_grab_drop`, `self.action_mate`.
- `SimulationEngine.next_genome_id() -> int` — contador monotônico, começa em 1.
- Novos atributos públicos em `Creature`: `genome`, `net`, `config`, `motor_forward`, `motor_torque`, `action_grab_drop`, `action_mate`, `is_holding` — `action_mate` é o contrato que BIT-04 (Reprodução) vai consumir.

## Critérios de aceite

- [ ] Criaturas se movem de forma não-determinística (saída da rede, não mais impulso fixo) — visível rodando a simulação (`manager.py` → Start Tudo → abrir frontend): movimento deixa de ser "sempre reto".
- [ ] `net.activate()` roda sem exceção para todas as criaturas vivas a cada brain tick (10 FPS), incluindo Gen 0 (genoma zero).
- [ ] `motor_forward`/`motor_torque` armazenados ficam no range aproximado de `[-1, 1]` (validação indireta: config usa `activation_default=tanh`).
- [ ] Custo de energia por frame é proporcional à magnitude do motor, não mais constante fixo.
- [ ] `action_grab_drop`/`action_mate` existem como atributos booleanos em `Creature`, mesmo sem efeito de jogo ainda.
- [ ] `pytest backend/tests/test_creature_think.py` 100% verde.
- [ ] Nenhuma regressão: `pytest backend/tests/` (incluindo `test_rtneat_wrapper.py` e os testes da BIT-01) continua 100% verde.

## Rollback

Reverter `creature.py` para a versão anterior ao `__init__`/`update`/`think` desta task; remover `next_genome_id()`/`self._next_genome_id` de `engine.py` e a chamada `creature.think(self)` do bloco de brain tick; deletar `backend/tests/test_creature_think.py`. Sem estado persistente/migração envolvida.
