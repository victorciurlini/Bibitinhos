## Arquivos relevantes

- `backend/simulation/creature.py` — classe `Creature`, sem `self.genome`/`self.net` hoje; `update()` aplica impulso fixo (`self.speed`) independente de qualquer cérebro
- `backend/simulation/engine.py` — `SimulationEngine.step()`; desde BIT-01 (em implementação em paralelo, branch `BIT-01`) ganha um acumulador de tempo que dispara `compute_vision()` a 10 FPS
- `backend/simulation/rtneat_wrapper.py` — `load_neat_config()`, `create_zero_genome(genome_id, config)`, `organic_crossover()`, `mutate_genome()`; docstring é o contrato de I/O oficial (16 inputs / 4 outputs)
- `backend/simulation/neat_config.ini` — `num_inputs=16`, `num_outputs=4`, `activation_default=tanh`, `initial_connection=full_direct`, `num_hidden=0`
- `backend/main.py` — cria as 10 criaturas iniciais via `Creature(engine)` (sem genome); `engine.step(1/30.0)` a 30 FPS

## Conteúdo relevante para a demanda

### Contrato de I/O já fixado (rtneat_wrapper.py, criado em BIT-00)
```
Inputs:  0-8 Visual_Sectors | 9 Energy_Level | 10 Age_Degradation | 11 Hormonal_Level
         12 Biological_Clock | 13 Load_Sensor | 14-15 Kinetic_Feedback (linear/angular)
Outputs: 0 Motor_Forward (tanh) | 1 Motor_Torque (tanh) | 2 Action_Grab_Drop (threshold) | 3 Action_Mate (threshold)
```
`activation_default = tanh` no `.ini` já garante que as saídas da rede ficam no range aproximado de `[-1, 1]` — não é preciso reescalar manualmente no código.

### Validação ao vivo da API (pymunk 7.2.0 / neat-python 0.92, ambiente do projeto)
```python
import neat
from simulation.rtneat_wrapper import load_neat_config, create_zero_genome
config = load_neat_config()
g = create_zero_genome(1, config)
net = neat.nn.FeedForwardNetwork.create(g, config)
out = net.activate([0.0] * 16)
# -> [-0.9499, -0.9243, 0.9781, 0.3388]  (4 floats, range tanh)
```
Confirmado: `neat.nn.FeedForwardNetwork.create(genome, config)` funciona direto com o genome/config já existentes desde BIT-00. Nenhum gap de API a resolver.

### `Creature.update(dt, engine)` atual (a ser substituído)
```python
if self.life_stage != LifeStage.EGG:
    forward_impulse = (self.speed * dt, 0)
    self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
self.energy -= dt * (self.speed * 0.1 + self.size * 0.05)
```
Movimento é sempre "acelerar reto para frente" na intensidade fixa de `self.speed` — nenhuma leitura de rede.

### Ponto de integração com BIT-01 (mesmo bloco, mesmo acumulador)
BIT-01 introduz em `engine.step()`:
```python
self._brain_accumulator += dt
if self._brain_accumulator >= BRAIN_TICK_INTERVAL:
    self._brain_accumulator -= BRAIN_TICK_INTERVAL
    for creature in self.creatures:
        if creature.is_alive:
            creature.vision = compute_vision(creature, self)
```
BIT-02 deve **estender esse mesmo bloco** (não criar um segundo acumulador/loop) para também rodar a rede logo após calcular a visão.

## O que precisa ser feito

1. `Creature.__init__` ganha parâmetro opcional `genome=None`: se `None`, cria genoma zero via `create_zero_genome(engine.next_genome_id(), config)` (Geração 0 / spawn aleatório); se fornecido, usa diretamente (abre o caminho para BIT-04 passar um genoma de crossover). `self.net = neat.nn.FeedForwardNetwork.create(self.genome, config)` construído uma vez na criação (reconstruir a cada tick seria caro e desnecessário — a topologia só muda em novo genoma/nova criatura).
2. `SimulationEngine` ganha um contador monotônico `self._next_genome_id` e método `next_genome_id()` — necessário para IDs únicos de genoma ao longo da simulação (spawn inicial + Jardim do Éden + futura reprodução).
3. Novo método `Creature.think(engine)`: monta o vetor de 16 inputs (9 de `self.vision` + 7 descritos abaixo), chama `self.net.activate(inputs)`, guarda os 4 outputs em atributos cacheados (`self.motor_forward`, `self.motor_torque`, `self.action_grab_drop`, `self.action_mate`). Chamado a 10 FPS, no mesmo bloco do brain tick de BIT-01, logo após `compute_vision`.
4. `Creature.update(dt, engine)` para de aplicar impulso fixo; passa a aplicar `self.motor_forward`/`self.motor_torque` (cacheados, reaplicados todo frame de física a 30 FPS até a próxima atualização do cérebro).
5. Custo de energia passa a ser proporcional à magnitude do output do motor (`abs(motor_forward)`, `abs(motor_torque)`) em vez de assumir "sempre acelerando no máximo" — barato de implementar, reaproveita os coeficientes (`speed*0.1`, `size*0.05`) já existentes.
6. Os 7 inputs não-visuais (índices 9-15) precisam de algum valor numérico para a rede rodar (o config exige exatamente 16 inputs). Nem todos têm um sistema real por trás ainda — ver decisões abaixo.

## Perguntas em aberto

- `Hormonal_Level` e `Biological_Clock` não têm nenhum sistema modelado na simulação hoje (não existe conceito de hormônio nem relógio biológico em `Creature`). Placeholder `0.0` é a única opção sem inventar um sistema novo fora de escopo — documentar explicitamente como "reservado para tarefa futura".
- `Load_Sensor` depende de "estar segurando algo", e o mecanismo de "grab" (`Action_Grab_Drop`) não existe fisicamente (não há lógica de pegar/soltar objetos no Pymunk hoje). Proponho armazenar apenas a saída do output (`self.action_grab_drop` como bool) sem implementar o efeito físico de fato — e o input `Load_Sensor` fica `0.0` fixo (nada para segurar ainda).
- `Age_Degradation`: não há um "MAX_AGE" definido no projeto (não existe morte por idade, só por energia). Precisa de uma constante nova e arbitrária para normalizar — proponho `AGE_DEGRADATION_SCALE = 60.0` (o dobro do threshold ELDER atual de 30s), documentada como tunável, sem introduzir morte por idade (fora de escopo).
