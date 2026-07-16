# Research — simulation-core (BIT-20)

Investigação feita diretamente pelo refiner (codegraph + validação ao vivo contra Pymunk/neat-python
no venv do projeto). Nenhum sub-agente: a demanda toca apenas `backend/simulation/`, e todos os
arquivos relevantes foram lidos e as suposições físicas foram medidas empiricamente, não assumidas.

## Arquivos relevantes

- `backend/simulation/creature.py` — custo de motor, metabolismo, `update()`, `think()`, `STARTING_ENERGY`
- `backend/simulation/engine.py` — reprodução sexuada (collision handler) e assexuada (laço em `step()`), Jardim do Éden
- `backend/simulation/physics.py` — `space.damping = 0.35` (arrasto de água, BIT-17)
- `backend/simulation/food.py` — `energy_value=20.0`
- `backend/simulation/oasis.py` — spawn de comida, constantes do Éden
- `backend/simulation/rtneat_wrapper.py` — `create_zero_genome()`, contrato de I/O da rede
- `backend/simulation/neat_config.ini` — `bias_init_mean=0.0`, `bias_init_stdev=1.0`

## Diagnóstico: por que o bibite fica parado girando (e mesmo assim procria)

### Causa raiz #1 — o gradiente de energia recompensa a paralisia

Em `creature.py:177`:

```python
motor_cost = forward_thrust * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05
```

Com `speed=50` e `size=10`, isso dá **5.0 energia/s** para andar a full thrust contra apenas
**0.5 energia/s** para girar a full torque. Somado ao metabolismo (ADULT = 0.8/s):

| Comportamento | Custo | Sobrevive (de 100 de energia) |
|---|---|---|
| Parado imóvel | 0.80/s | **125s** |
| Parado girando | 1.30/s | **77s** |
| Explorando (thrust 0.8) | 4.95/s | **20s** |
| Full + curvando | 6.30/s | **16s** |

Andar em linha reta é **4.5x mais caro** que girar no lugar. A seleção natural está funcionando
corretamente — o ambiente é que premia a paralisia. Quem anda morre em 20s, quem gira vive 77s.
Não é um defeito do cérebro NEAT; é o balanceamento energético.

### Causa raiz #2 — 48% da Geração 0 nasce fisicamente incapaz de andar

`neat_config.ini` usa `bias_init_mean = 0.0`, `bias_init_stdev = 1.0`. O output 0 (`Motor_Forward`)
passa por `tanh`, e `creature.py:173` faz `forward_thrust = max(0.0, self.motor_forward)` —
não há propulsão para trás. Logo, todo genoma com bias negativo no node 0 tem thrust
permanentemente zero.

Medido ao vivo (400 genomas Gen 0, sensores zerados): **193/400 = 48% têm `Motor_Forward <= 0`**.
Quase metade da população inicial nunca se move, por construção.

### Causa raiz #3 — a reprodução assexuada é estruturalmente MAIS FÁCIL que a sexuada

BIT-16 subiu `MIN_ENERGY_TO_MATE` para `100.0`, que é **exatamente o valor de `max_energy`**.
Consequência não intencional:

- **Sexuada**: exige DUAS criaturas com energia *perfeitamente cheia* (100.0/100.0) colidindo
  no mesmo frame, ambas com `action_mate`. Como a energia sangra a cada frame, ela só toca 100.0
  no instante exato em que uma comida é consumida estando >= 80. A janela é quase nula, e exigir
  que duas criaturas estejam nessa janela simultaneamente torna o acasalamento praticamente impossível.
- **Assexuada**: mesmo limiar (100.0), mas exige apenas UMA criatura.

Com limiares iguais, a via solo tem probabilidade ordens de magnitude maior. **É por isso que o
developer observa clonagem em vez de acasalamento** — e é a resposta ao "por algum motivo que ele
não deveria ser capaz, de procriar": ele *pode*, via `clone_genome` (BIT-09).

### Causa raiz #4 — o Jardim do Éden subsidia diretamente quem está parado

`engine.py:207-214`: quando a população cai abaixo de 10, cria um `Oasis` de raio 200 e
`food_cap=20` **exatamente na posição de cada sobrevivente**. Ou seja: chove comida de graça em
cima dos parados. Loop auto-sustentável: fica parado → população cai → Éden dispara → comida grátis
→ energia sobe a 100 → clona → repete.

### Nota: BIT-16 já tentou resolver isto e falhou

A spec do BIT-16 cita exatamente as mesmas patologias ("ficar parado, andar em linha reta até bater
na parede") e tentou corrigi-las **encarecendo a reprodução**. Não funcionou porque não tocou no
custo de *locomoção* — o gradiente continuou premiando a paralisia, e o efeito colateral (limiar
sexual == teto de energia) piorou a situação ao empurrar a reprodução para a via assexuada.
**A alavanca correta é o custo de locomoção, não o limiar de reprodução.**

## Validação empírica (rodada no venv do projeto)

### Física — velocidade terminal sob o arrasto do BIT-17 (`damping=0.35`)

```
thrust=1.00 -> terminal = 46.80 px/s
thrust=0.80 -> terminal = 37.44 px/s
thrust=0.50 -> terminal = 23.40 px/s
thrust=0.25 -> terminal = 11.70 px/s
tempo p/ 90% da terminal (full thrust): 2.60s
```

A relação é **linear**: `v_terminal ≈ 46.8 × thrust`. Isso é crítico para calibrar o limiar de
"movimento": ele precisa ser alcançável (< 46.8) e folgado o bastante para não punir a criatura
durante os 2.6s de aceleração a partir do repouso. **`MOVEMENT_REFERENCE_SPEED = 35.0`** (75% da
terminal, atingível com thrust >= 0.75).

### NEAT — node keys e efeito do seed

```
node keys dos outputs: [0, 1, 2, 3]   -> Motor_Forward == node key 0 (confirmado)
Gen 0 incapaz de andar: 193/400 = 48%

seed U(0.3,1.0) no bias do node 0: 400/400 andam | thrust medio=0.89 min=0.64 max=0.99
seed U(0.5,1.5) no bias do node 0: 400/400 andam | thrust medio=0.97 min=0.85 max=1.00
```

`U(0.3, 1.0)` é a escolha melhor: leva 100% da Gen 0 a andar **preservando variedade genética**
(min 0.64 / max 0.99), enquanto `U(0.5,1.5)` satura o `tanh` e colapsa quase todos em thrust ~1.0.

### Economia proposta — validada por simulação

Fórmula proposta (`MOVEMENT_REFERENCE_SPEED=35, IDLE_PENALTY_RATE=2.0, MOTOR_FORWARD_COST=0.6, SPIN_COST=1.0`):

| Comportamento | Custo NOVO | Sobrevive | (era) |
|---|---|---|---|
| **Parado girando** (o exploit) | **3.80/s** | **26s** 🔻 pior | (77s) |
| Parado imóvel | 2.80/s | 36s | (125s) |
| Rastejando (0.25) | 2.28/s | 44s | (49s) |
| Meia força (0.5) | 1.76/s | 57s | (30s) |
| **Explorando (0.8)** | **1.28/s** | **78s** 🥇 melhor | (20s) |
| Full + curvando | 1.40/s | 71s | (16s) |

O gradiente inverte completamente: o exploit passa de 2ª melhor estratégia para **a pior possível**.
Há um **ótimo interno em thrust ≈ 0.8** (78s > 71s do full-throttle), o que evita a degenerescência
oposta ("acelerar cegamente até bater na parede", a outra patologia citada no BIT-16).

Curvar **enquanto se move é grátis** (`SPIN_COST` escala com `1 - movement_factor`) — essencial,
pois a criatura precisa poder virar para perseguir comida sem ser punida.

Energia ao virar ADULT (10s de idade, nascendo com 75):
- parado-girando: **44.6** · explorando: **64.8**

Ambos ficam **abaixo de 85**, então com `MIN_ENERGY_TO_MATE = 85` toda criatura ainda **precisa comer
antes de conseguir acasalar** — preserva a intenção central do BIT-16 sem manter o limiar colado no teto.

## O que precisa ser feito

1. **`creature.py`** — substituir `motor_cost` por um modelo baseado em **velocidade real medida**
   (`self.body.velocity.length`), não no output do motor. Medir a velocidade real é o que torna a
   punição imburlável: empurrar contra uma parede (velocidade ≈ 0) passa a pagar a multa cheia.
   Adicionar `idle_cost`. Isentar `EGG` (não se move nem paga motor hoje).
2. **`rtneat_wrapper.py`** — enviesar o bias do node de output 0 em `create_zero_genome()`
   (só Gen 0/Éden; filhos herdam por crossover/clone e a evolução pode mutar livremente).
3. **`engine.py`** — `MIN_ENERGY_TO_MATE` 100 → 85 (destrava a via sexuada); encarecer a assexuada
   (custo 70 → 85, cooldown 20 → 45); Éden passa a nascer *longe* do sobrevivente.
4. **`food.py`** — `energy_value` 20 → 25 (recompensa por comer).

## Perguntas em aberto (resolvidas)

- **"Avaliar se está com fome e deveria comer, ou procurar parceiro"** — *não requer mecanismo novo*.
  O contrato de visão do BIT-13 já entrega essa informação ao cérebro: sinal positivo = comida
  (magnitude = fome), negativo = outra criatura ADULT (magnitude = energia dela), mais o
  `Energy_Level` no input 9. A rede **já tem tudo** para tomar essa decisão — o que faltava era o
  incentivo, não o sensor. Criar um sistema de decisão explícito seria hardcodar comportamento que
  deve emergir. **Fora de escopo.**
- **Frontend/API** — nenhuma mudança necessária. Nenhum contrato de I/O do NEAT (16 inputs / 4 outputs),
  nenhum formato de mensagem WebSocket é alterado.
