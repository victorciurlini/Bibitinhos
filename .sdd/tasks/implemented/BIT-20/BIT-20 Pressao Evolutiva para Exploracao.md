# Spec — BIT-20: Pressão Evolutiva para Exploração

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação)

---

## Demanda

O comportamento dominante entre as criaturas que mais sobrevivem é **ficar parado girando no lugar** —
e, mesmo assim, conseguir procriar. O developer quer que os bibites sejam **incentivados a todo momento
a explorar o mapa** atrás de comida e de parceiros, **punidos por ficarem parados** e **recompensados por
comer e reproduzir**, com esse comportamento garantido **desde o início** da simulação.

## Abordagem técnica

O problema **não está no cérebro NEAT — está no balanceamento energético**. Hoje andar custa `5.0`
energia/s e girar no lugar custa `0.5`/s (mais o metabolismo de `0.8`/s): andar em linha reta é **4.5x
mais caro** que girar. A seleção natural está funcionando perfeitamente e otimizando para a paralisia,
porque é isso que o ambiente recompensa. Quem anda morre em 20s; quem gira vive 77s.

A correção tem quatro frentes, todas em `backend/simulation/`:

1. **Inverter o gradiente de energia** — barateia a propulsão, e cria um *imposto de ociosidade* pago
   proporcionalmente a quão parada a criatura está, medido pela **velocidade real do corpo Pymunk**
   (não pelo output do motor — o que torna a multa imburlável: empurrar contra a parede paga cheio).
   Girar parado passa a ser a **pior** estratégia possível (26s de vida contra 78s explorando).
2. **Seed genético na Gen 0** — hoje **48% das criaturas nascem fisicamente incapazes de andar**
   (`bias_init_mean=0.0` + `forward_thrust = max(0.0, motor_forward)` ⇒ bias negativo = thrust zero
   permanente). Enviesar o bias do node `Motor_Forward` garante o comportamento "desde o início".
3. **Destravar a reprodução sexuada** — `MIN_ENERGY_TO_MATE = 100.0` (posto pelo BIT-16) é *exatamente*
   o teto de `max_energy`, o que exige duas criaturas com energia perfeitamente cheia colidindo no mesmo
   frame. A via assexuada, com o mesmo limiar, exige só **uma** — logo é estruturalmente mais fácil.
   **É essa assimetria que faz o bibite parado clonar em vez de acasalar.**
4. **Parar de subsidiar quem está parado** — o Jardim do Éden hoje spawna um oásis *em cima da posição*
   de cada sobrevivente; passa a nascer a uma distância que **obriga a locomoção** até a comida.

Dependência: nenhuma task pendente. Corrige um efeito colateral do **BIT-16** (já mergeado), que atacou
este mesmo sintoma pelo lado errado (encareceu a reprodução sem tocar no custo de locomoção).

**Fora de escopo:** criar um sistema explícito de "decidir entre comer ou acasalar". O contrato de visão
do BIT-13 já entrega isso ao cérebro (sinal positivo = comida, magnitude = fome; negativo = criatura
ADULT, magnitude = energia; mais `Energy_Level` no input 9). A rede **já tem todos os sensores** para
essa decisão — faltava o incentivo, não a informação. Hardcodar a decisão mataria a emergência.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | Nova economia de energia: custo de motor barato + imposto de ociosidade por velocidade real |
| `backend/simulation/rtneat_wrapper.py` | modificar | Seed do bias de `Motor_Forward` em `create_zero_genome()` |
| `backend/simulation/engine.py` | modificar | `MIN_ENERGY_TO_MATE` 100→85; assexuada encarecida; Éden nasce longe do sobrevivente |
| `backend/simulation/food.py` | modificar | `energy_value` 20.0 → 25.0 |
| `backend/simulation/oasis.py` | modificar | Constantes de distância do oásis do Éden |
| `backend/tests/test_exploration_pressure.py` | criar | Testes da nova economia + seed genético |

## Passos de implementação

> Passos 1-2 são o núcleo (independentes entre si). Passos 3-5 são ajustes de balanceamento que
> dependem conceitualmente do passo 1, mas podem ser editados em paralelo. Passo 6 valida tudo.

### 1. `creature.py` — inverter o gradiente de energia

Substituir as constantes de custo e o cálculo em `update()`.

Junto das constantes de módulo existentes (perto de `MOTOR_TORQUE_SCALE`), **adicionar**:

```python
# --- Economia de energia (BIT-20): explorar tem que ser mais barato que ficar parado ---
# O modelo antigo (thrust*speed*0.1 + |torque|*size*0.05) cobrava 5.0/s para andar e 0.5/s
# para girar no lugar, o que fazia da paralisia a estrategia otima. Aqui o sinal se inverte.
MOVEMENT_REFERENCE_SPEED = 35.0  # px/s: velocidade real a partir da qual a criatura conta como
                                 # "explorando de verdade" (75% da terminal de 46.8 px/s medida sob
                                 # damping=0.35 do BIT-17; folgada o bastante para nao punir os
                                 # ~2.6s de aceleracao a partir do repouso)
IDLE_PENALTY_RATE = 2.0          # energia/s de imposto de ociosidade, cheio quando parada
MOTOR_FORWARD_COST = 0.6         # energia/s a full thrust (era efetivamente 5.0/s)
SPIN_COST = 1.0                  # energia/s a full torque, mas so quando parada: curvar enquanto
                                 # se move e de graca (a criatura precisa virar p/ perseguir comida)
```

Em `update()`, **substituir** o bloco de custo. Trecho atual:

```python
            self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE
            motor_cost = forward_thrust * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05
```

Passa a ser (mantendo `self.body.torque` como está, e mantendo o grip lateral logo abaixo intocado):

```python
            self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE

            # Fator de movimento medido pela VELOCIDADE REAL do corpo, nao pelo output do motor:
            # e isso que torna a multa imburlavel (empurrar contra a parede => velocidade ~0 => paga cheio).
            movement_factor = min(1.0, self.body.velocity.length / MOVEMENT_REFERENCE_SPEED)
            idle_cost = IDLE_PENALTY_RATE * (1.0 - movement_factor)
            motor_cost = (
                MOTOR_FORWARD_COST * forward_thrust
                + SPIN_COST * abs(self.motor_torque) * (1.0 - movement_factor)
            )
```

E o débito final passa a incluir `idle_cost`:

```python
        metabolism_cost = METABOLISM_RATE_BY_STAGE[self.life_stage]
        self.energy -= dt * (motor_cost + idle_cost + metabolism_cost)
```

**Atenção — `EGG` é isento.** `idle_cost` e `motor_cost` são inicializados a `0.0` *fora* do
`if self.life_stage != LifeStage.EGG:` e só recebem valor dentro dele — exatamente como `motor_cost`
já funciona hoje. Um EGG não pode se mover; multá-lo por ociosidade seria puni-lo por existir.
Declarar no topo do bloco:

```python
        motor_cost = 0.0
        idle_cost = 0.0
        if self.life_stage != LifeStage.EGG:
            ...
```

### 2. `rtneat_wrapper.py` — seed genético do `Motor_Forward` (garante o comportamento "desde o início")

Confirmado ao vivo: os node keys de output do `DefaultGenome` são `[0, 1, 2, 3]`, então
**`Motor_Forward` é o node key `0`**.

Adicionar no topo do módulo:

```python
import random

# Seed de locomocao (BIT-20): com bias_init_mean=0.0 no neat_config.ini, 48% dos genomas Gen 0
# nascem com Motor_Forward <= 0 — e como forward_thrust = max(0.0, motor_forward), essas criaturas
# sao fisicamente incapazes de andar, para sempre. Enviesar o bias do node de output 0 faz 100% da
# Gen 0 nascer se movendo, preservando variedade (thrust resultante ~0.64 a ~0.99, medido).
# Isso e um SEED, nao um hardcode: a mutacao pode levar o bias para onde a evolucao quiser, e
# filhos (crossover/clone) nao passam por aqui.
MOTOR_FORWARD_NODE_KEY = 0
MOTOR_FORWARD_SEED_BIAS_MIN = 0.3
MOTOR_FORWARD_SEED_BIAS_MAX = 1.0
```

Em `create_zero_genome()`, após `genome.configure_new(...)`:

```python
def create_zero_genome(genome_id, config):
    """
    Creates a new empty genome with basic structure based on the provided configuration.
    This acts as a pure function abstraction.
    """
    genome = config.genome_type(genome_id)
    genome.configure_new(config.genome_config)
    # Vies inicial positivo em Motor_Forward: a Gen 0 (e os respawns do Eden) ja nasce andando.
    if MOTOR_FORWARD_NODE_KEY in genome.nodes:
        genome.nodes[MOTOR_FORWARD_NODE_KEY].bias = random.uniform(
            MOTOR_FORWARD_SEED_BIAS_MIN, MOTOR_FORWARD_SEED_BIAS_MAX
        )
    return genome
```

Atualizar a docstring do módulo mencionando o seed junto do contrato de I/O.

### 3. `engine.py` — destravar a via sexuada e encarecer a assexuada

```python
REPRODUCTION_ENERGY_COST = 40.0   # era 50.0 — recompensa reproduzir: pos-parto sobra 45, sobrevivivel
REPRODUCTION_COOLDOWN = 10.0      # inalterado
MIN_ENERGY_TO_MATE = 85.0         # era 100.0 (== max_energy, ou seja: exigia energia PERFEITAMENTE
                                  # cheia nas DUAS criaturas no mesmo frame — janela quase nula, o que
                                  # empurrava toda a reproducao para a via assexuada, que exige so uma).
                                  # 85 > STARTING_ENERGY (75): a cria AINDA precisa comer antes de
                                  # acasalar, preservando a intencao do BIT-16.
MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 100.0  # inalterado (teto de max_energy)
ASEXUAL_REPRODUCTION_ENERGY_COST = 85.0    # era 70.0 — clonar vira aposta de vida ou morte (sobra 15)
ASEXUAL_REPRODUCTION_COOLDOWN = 45.0       # era 20.0 — 4.5x o cooldown sexuado
```

Efeito líquido: acasalar (limiar 85, custo 40, cooldown 10) domina folgadamente sobre clonar
(limiar 100, custo 85, cooldown 45). A clonagem permanece como via de emergência contra extinção
— conforme decidido pelo developer, **não** foi desativada, apenas encarecida.

### 4. `engine.py` — Jardim do Éden para de subsidiar quem está parado

Hoje o oásis do Éden nasce **na posição exata** do sobrevivente, fazendo chover comida sobre quem está
parado. Passa a nascer a uma distância que obriga a locomoção. Substituir o bloco `elif`:

```python
        elif len(self.creatures) < EDEN_POPULATION_THRESHOLD:
            if not self._eden_active:
                self._eden_active = True
                for creature in self.creatures:
                    # O oasis nasce LONGE do sobrevivente (BIT-20): o Eden continua sendo o seguro
                    # contra extincao, mas a comida tem que ser conquistada andando, nao chover em
                    # cima de quem ficou parado.
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(EDEN_OASIS_MIN_DISTANCE, EDEN_OASIS_MAX_DISTANCE)
                    ox = max(0.0, min(float(self.width), creature.body.position.x + dist * math.cos(angle)))
                    oy = max(0.0, min(float(self.height), creature.body.position.y + dist * math.sin(angle)))
                    self.oases.append(Oasis(
                        ox, oy,
                        radius=EDEN_OASIS_RADIUS, ttl=EDEN_OASIS_TTL, food_cap=EDEN_OASIS_FOOD_CAP,
                    ))
```

Requer `import math` no topo de `engine.py` (hoje só importa `random`), e adicionar
`EDEN_OASIS_MIN_DISTANCE, EDEN_OASIS_MAX_DISTANCE` ao import vindo de `simulation.oasis`.

### 5. `oasis.py` e `food.py` — constantes de apoio

Em `oasis.py`, junto das constantes do Éden:

```python
EDEN_OASIS_MIN_DISTANCE = 250.0  # o oasis do Eden nasce longe do sobrevivente: comida se conquista andando
EDEN_OASIS_MAX_DISTANCE = 400.0  # < VISION_RADIUS + margem: continua encontravel, mas exige locomocao
```

Em `food.py`, o default do construtor:

```python
class Food:
    def __init__(self, engine, x, y, energy_value=25.0):  # era 20.0 — recompensa por comer
```

### 6. `backend/tests/test_exploration_pressure.py` — novo arquivo de testes

Importar as constantes (nunca hardcodar valores — é o padrão dos testes deste projeto, e foi o que
permitiu que o BIT-16 mudasse constantes sem quebrar a suíte). Cobrir:

1. **Girar parado é mais caro que explorar** — monta duas criaturas ADULT, uma com
   `motor_forward=0.0, motor_torque=1.0` e velocidade ~0, outra com `motor_forward=0.8` e velocidade
   >= `MOVEMENT_REFERENCE_SPEED`; roda `update()` e afirma que a primeira perdeu **mais** energia.
   *Este é o teste que trava a regressão do comportamento reclamado.*
2. **Imposto de ociosidade escala com a velocidade** — criatura com `velocity.length == 0` paga
   `IDLE_PENALTY_RATE` cheio; com `velocity.length >= MOVEMENT_REFERENCE_SPEED` paga zero.
3. **EGG não paga ociosidade** — criatura com `life_stage == EGG` e velocidade 0 perde `0.0` de energia.
4. **Curvar em movimento é grátis** — criatura a `velocity >= MOVEMENT_REFERENCE_SPEED` com
   `motor_torque=1.0` paga o mesmo que com `motor_torque=0.0`.
5. **Multa imburlável** — criatura com `motor_forward=1.0` mas `velocity.length == 0` (empurrando
   contra a parede) paga o imposto de ociosidade cheio.
6. **Seed genético** — sobre N genomas de `create_zero_genome()`, 100% têm
   `nodes[0].bias >= MOTOR_FORWARD_SEED_BIAS_MIN`, e a rede ativada com 16 zeros retorna
   `outputs[0] > 0` (todas conseguem andar).
7. **Sexuada é mais acessível que a assexuada** — `MIN_ENERGY_TO_MATE < MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`
   e `REPRODUCTION_ENERGY_COST < ASEXUAL_REPRODUCTION_ENERGY_COST`.
8. **Éden nasce longe** — com população < `EDEN_POPULATION_THRESHOLD`, todo oásis criado está a pelo
   menos `EDEN_OASIS_MIN_DISTANCE` do sobrevivente (com tolerância para o clamp nas bordas do mapa).

### 7. Validação

Rodar a suíte inteira: `backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`.

**Testes existentes que provavelmente vão precisar de ajuste** (não são regressões — a economia mudou
deliberadamente): `test_metabolism.py` e `test_locomotion.py` podem assumir o custo antigo. Se um teste
afirmar o valor absoluto do custo de motor antigo, atualizá-lo para a nova fórmula. **Não** enfraquecer
os testes de `test_locomotion.py` que protegem o grip lateral (`LATERAL_GRIP_RATE`) — o comentário em
`creature.py:15-17` avisa que ele quebra abaixo de ~11.1, e este BIT não o toca.

## Contratos técnicos

### Backend (Simulação)

**`creature.py`** — constantes novas:
- `MOVEMENT_REFERENCE_SPEED: float = 35.0`
- `IDLE_PENALTY_RATE: float = 2.0`
- `MOTOR_FORWARD_COST: float = 0.6`
- `SPIN_COST: float = 1.0`

Nova fórmula de energia por segundo (aplicada em `update()`, `EGG` isento de motor/idle):

```
movement_factor = min(1.0, body.velocity.length / MOVEMENT_REFERENCE_SPEED)
idle_cost       = IDLE_PENALTY_RATE * (1 - movement_factor)
motor_cost      = MOTOR_FORWARD_COST * forward_thrust
                + SPIN_COST * |motor_torque| * (1 - movement_factor)
energia        -= dt * (motor_cost + idle_cost + METABOLISM_RATE_BY_STAGE[life_stage])
```

**`rtneat_wrapper.py`** — constantes novas: `MOTOR_FORWARD_NODE_KEY = 0`,
`MOTOR_FORWARD_SEED_BIAS_MIN = 0.3`, `MOTOR_FORWARD_SEED_BIAS_MAX = 1.0`.
`create_zero_genome(genome_id, config)` mantém a assinatura; passa a enviesar `nodes[0].bias`.

**`engine.py`** — `MIN_ENERGY_TO_MATE` 100→85, `REPRODUCTION_ENERGY_COST` 50→40,
`ASEXUAL_REPRODUCTION_ENERGY_COST` 70→85, `ASEXUAL_REPRODUCTION_COOLDOWN` 20→45.
**`oasis.py`** — `EDEN_OASIS_MIN_DISTANCE = 250.0`, `EDEN_OASIS_MAX_DISTANCE = 400.0`.
**`food.py`** — `Food.__init__(..., energy_value=25.0)`.

### API/WebSocket
**Nenhuma mudança.** Nenhum campo novo, nenhum formato alterado.

### Frontend
**Nenhuma mudança.**

### Contrato de I/O do NEAT
**Inalterado** — continuam 16 inputs e 4 outputs, mesma ordem, mesma semântica. O seed altera apenas o
*valor inicial* de um bias, não a topologia nem o contrato. Genomas antigos permanecem compatíveis.

## Critérios de aceite

- [ ] Uma criatura ADULT parada girando (`motor_forward=0`, `motor_torque=1`, velocidade ≈ 0) perde
      energia **mais rápido** que uma explorando (`motor_forward=0.8`, velocidade ≥ 35 px/s).
      Alvos medidos: **3.80/s** contra **1.28/s**.
- [ ] Girar parado é a **pior** estratégia de sobrevivência disponível (~26s de vida contra ~78s
      explorando, partindo de 100 de energia).
- [ ] Uma criatura com `motor_forward = 1.0` mas travada contra a parede (velocidade ≈ 0) paga o
      imposto de ociosidade **cheio** (a multa não é burlável pelo output do motor).
- [ ] Curvar enquanto se move é gratuito: a `velocidade ≥ MOVEMENT_REFERENCE_SPEED`, o custo com
      `motor_torque = 1.0` é igual ao custo com `motor_torque = 0.0`.
- [ ] `EGG` continua sem pagar custo de motor **nem** de ociosidade (perde `0.0` de energia).
- [ ] **100%** dos genomas de `create_zero_genome()` produzem `outputs[0] > 0` com os 16 inputs zerados
      (hoje: 52%).
- [ ] `MIN_ENERGY_TO_MATE (85) < MIN_ENERGY_TO_REPRODUCE_ASEXUALLY (100)` e
      `REPRODUCTION_ENERGY_COST (40) < ASEXUAL_REPRODUCTION_ENERGY_COST (85)` — acasalar é
      inequivocamente mais fácil e mais barato que clonar.
- [ ] `MIN_ENERGY_TO_MATE (85) > STARTING_ENERGY (75)` — a cria ainda **precisa comer** antes de
      poder acasalar (intenção do BIT-16 preservada).
- [ ] O oásis do Jardim do Éden nasce a ≥ 250px do sobrevivente, nunca em cima dele.
- [ ] `pytest backend/tests/` 100% verde.
- [ ] **Validação funcional (a que importa):** rodar via `manager.py` por alguns minutos e observar que
      (a) as criaturas se **movem pelo mapa** desde o primeiro instante, (b) **não** existe mais o padrão
      de bibite parado girando no lugar, (c) a reprodução acontece predominantemente por **encontro entre
      duas criaturas**, não por clonagem solitária.

## Rollback

Reverter os 5 arquivos de `backend/simulation/` (`creature.py`, `rtneat_wrapper.py`, `engine.py`,
`food.py`, `oasis.py`) e deletar `backend/tests/test_exploration_pressure.py`. Nenhuma migração de
dados, nenhum contrato externo tocado — `git checkout -- backend/simulation/` basta.

**Se a população colapsar** (extinções em cadeia), a causa mais provável é o imposto de ociosidade estar
alto demais em relação à oferta de comida. Ajustar nesta ordem, sem reverter a estrutura:
1. `IDLE_PENALTY_RATE` 2.0 → 1.2
2. `Food.energy_value` 25 → 35
3. `MOVEMENT_REFERENCE_SPEED` 35 → 25 (torna mais fácil contar como "em movimento")
