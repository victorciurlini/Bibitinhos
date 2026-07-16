# Regras da Simulação

> Documento vivo — os valores abaixo refletem o código em 2026-07-15 (pós BIT-20, com o
> trabalho do BIT-21 já presente na working tree). **O código é a fonte da verdade**:
> as constantes citam o arquivo onde vivem; em caso de divergência, vale o `.py`.

## 1. Mundo físico (`physics.py`)

- Caixa **2000×2000**, sem gravidade.
- `space.damping = 0.35` — arrasto de água (BIT-17): sem propulsão, o corpo retém só
  35% da velocidade por segundo. Velocidade terminal medida a full thrust: ~46.8 px/s.
- Paredes com `elasticity = 1.0` (quicam).

## 2. Criatura (`creature.py`)

Corpo: `pymunk.Circle` de raio 10, massa 1.0. Atributos "de DNA" ainda mockados:
`speed = 50`, `size = 10`, `max_energy = 100`, `diet = 'herbivore'`.
Energia inicial: **75** (`STARTING_ENERGY` — a cria precisa comer antes de poder se
reproduzir, já que os limiares de reprodução ficam acima disso... ver §6).

### 2.1 Ciclo de vida (por idade, em segundos simulados)

| Fase | Idade | Metabolismo (energia/s) | Notas |
|---|---|---|---|
| EGG | 0–2 | 0.0 | Inerte: cérebro não é aplicado, isento de custo de motor e ociosidade |
| JUVENILE | 2–10 | 0.3 | Move e sente, não reproduz |
| ADULT | 10–30 | 0.8 | Única fase que reproduz; visão passa a detectar outras criaturas |
| ELDER | 30+ | 2.0 | Degradação acelerada; morre por inanição (não há teto de idade) |

Morte: `energy <= 0`. O corpo é removido do espaço físico no mesmo frame.

### 2.2 Locomoção (BIT-07)

- **Só para frente**: `forward_thrust = max(0, Motor_Forward)` vira impulso no eixo
  local X. Não existe ré.
- **Torque**: `Motor_Torque × 20` (volante de arcade).
- **Grip lateral** (`LATERAL_GRIP_RATE = 20/s`): amortece a componente lateral da
  velocidade — a criatura não derrapa de lado por inércia, mas colisões ainda a empurram.
  ⚠️ Não reduzir abaixo de ~11.1: quebra `test_locomotion.py`.

### 2.3 Economia de energia (BIT-20 — a regra mais importante do jogo)

O modelo antigo cobrava 5.0/s para andar e 0.5/s para girar parado — a seleção natural
otimizava (corretamente!) para a paralisia. O BIT-20 inverteu o gradiente: **girar parado
é hoje a pior estratégia possível**.

```
movement_factor = min(1, |velocidade real| / 35)          # MOVEMENT_REFERENCE_SPEED
idle_cost   = 1.2 × (1 − movement_factor)                  # IDLE_PENALTY_RATE
motor_cost  = 0.6 × thrust                                 # MOTOR_FORWARD_COST
            + 1.0 × |torque| × (1 − movement_factor)       # SPIN_COST (grátis em movimento)
energia    −= dt × (motor_cost + idle_cost + metabolismo)
```

Pontos de design que os testes protegem (`test_exploration_pressure.py`):

- A multa usa a **velocidade real do corpo**, não o output do motor — empurrar a parede
  paga o imposto cheio (imburlável). Medida *antes* do impulso do frame, de propósito.
- Curvar **em movimento é grátis** (a criatura precisa virar para perseguir comida).
- EGG é isento de motor e ociosidade.
- `IDLE_PENALTY_RATE` foi calibrado de 2.0 → **1.2** ao vivo: a 2.0 a população colapsava
  (13 extinções/5min); a 1.2 o ecossistema se sustenta e parado-girando segue perdendo.

## 3. Visão (`sensors.py` — BIT-01, 13, 14, 21)

- Raio **80px**, cone **frontal de 120°** dividido em **9 setores** (setor 4 = eixo
  "para frente"; nada atrás ou fora do cone ativa setor algum).
- Implementação: `space.bb_query()` + `arctan2` (NumPy); paredes são ignoradas
  (não têm `collision_type`).
- Cada setor carrega **sinal com semântica** (BIT-13):
  - **Comida** → valor **positivo**, magnitude = fome (`1 − energia/max`). Quanto mais
    faminta, mais "gritante" a comida.
  - **Outra criatura** → só percebida se a observadora for ADULT; magnitude = fração de
    energia da observadora. Sinal **negativo** (repulsivo) por padrão, mas **positivo**
    (atrativo) se a observadora está *pronta para acasalar* (BIT-21: ADULT com
    energia ≥ 65% e sem cooldown) — o mesmo circuito de food-taxis passa a puxá-la
    para parceiros.
  - Comida tem precedência sobre criatura no mesmo setor.

## 4. Cérebro (contrato de I/O — `rtneat_wrapper.py`, docstring canônica)

Rede feedforward NEAT, avaliada a 10 FPS; saídas cacheadas e reaplicadas a cada frame.

**16 inputs**: `vision[0..8]`, `Energy_Level` (0–1), `Age_Degradation` (idade/60, cap 1),
`Hormonal_Level` (placeholder 0.0), `Biological_Clock` (placeholder 0.0),
`Load_Sensor` (placeholder — `is_holding` nunca muda), `Kinetic_Feedback` linear e
angular (velocidades normalizadas, clamp ±1).

**4 outputs**: `Motor_Forward` (contínuo, tanh), `Motor_Torque` (contínuo),
`Action_Grab_Drop` (> 0 = ativo; ainda sem efeito físico), `Action_Mate` (> 0 = ativo).

### 4.1 Seeds da Geração 0 (só em `create_zero_genome`; filhos não passam por aqui)

Seeds enviesam valores iniciais **sem alterar topologia nem contrato** — mutação e
crossover podem levá-los para onde a evolução quiser:

| Seed | BIT | O quê | Por quê |
|---|---|---|---|
| Locomoção | 20 | bias de `Motor_Forward` ~ U(0.3, 1.0) | Com bias médio 0, 48% da Gen 0 nascia incapaz de andar (thrust clampado em 0) |
| Food-taxis | 21 | peso `visão[i]→Motor_Torque` = 1.0×(i−4) | Gen 0 vira em direção à comida que enxerga (97% medido, contra 47.5% aleatório) |
| Ímpeto reprodutivo | 21 | bias de `Action_Mate` ~ U(1.5, 2.5) | Adultos saciados nascem querendo acasalar (~93–99% medido, contra 56%) |

## 5. Evolução (rtNEAT orgânico)

Não há gerações em lote nem fitness explícito — fitness é **estar vivo e deixar
descendência**. O wrapper expõe a matemática do `neat-python` como funções puras:
`organic_crossover()` (exige fitness numérico nos pais; setamos 0.0 para satisfazer o
assert da lib), `clone_genome()` (deepcopy + novo id) e `mutate_genome()`. Todo filho
(sexuado ou clone) é mutado ao nascer.

## 6. Reprodução (`engine.py`)

### 6.1 Sexuada (via principal — colisão ADULT × ADULT)

Condições: ambos ADULT, ambos com `Action_Mate` ativo, ambos com energia ≥ **65**
(`MIN_ENERGY_TO_MATE`) e sem cooldown.

Efeito: cada pai paga **30** (`REPRODUCTION_ENERGY_COST`), cooldown de **10s**; o filho
nasce como EGG no ponto médio, com genoma = crossover + mutação.

### 6.2 Assexuada (via de emergência — BIT-09, encarecida no BIT-20)

Para um ADULT que **não colidiu com nenhuma criatura no frame**, com `Action_Mate`
ativo e energia ≥ **90** (`MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`): clona o próprio genoma
(+ mutação) pagando **85** de energia (sobra ~15 — aposta de vida ou morte) e cooldown
de **45s** (4.5× o sexuado).

O desenho garante que **acasalar domina clonar** (limiar menor, custo menor, cooldown
menor) — clonagem existe só como seguro contra extinção, nunca como estratégia dominante.

## 7. Comida (`food.py`)

- Corpo **dinâmico** com 1% da massa da criatura (BIT-08): ação-reação real — a criatura
  empurra a comida em vez de bater numa "parede".
- `energy_value = 40` por unidade (BIT-20: era 20; recompensa por comer).
- **Apodrece** em 30s (`FOOD_TTL`, BIT-18): libera vaga no cap global; sem isso, comida
  órfã de oásis expirados saturava o mapa e a renovação parava.
- Cap global: **50** comidas (`MAX_TOTAL_FOOD`).

## 8. Oásis e Jardim do Éden (`oasis.py` + `engine.py`)

Comida **só nasce dentro de oásis** — zonas lógicas (sem corpo físico) com TTL, que
forçam nomadismo.

| Parâmetro | Oásis normal | Oásis do Éden |
|---|---|---|
| Máx. simultâneos | 4 ativos (10 no total, teto duro) | conta no teto de 10 |
| Chance de spawn | 1% por frame | 1 por sobrevivente, ao cruzar o limiar |
| Raio | 150 | 200 |
| TTL | 15–40s (uniforme) | 30s |
| Cap de comida | 8 | 20 |
| Chance de comida | 8% por frame por oásis | idem |

**Jardim do Éden** (failsafe anti-extinção):

- População < **10** (`EDEN_POPULATION_THRESHOLD`): um oásis denso por sobrevivente,
  nascendo a **250–400px de distância** dele (BIT-20 — antes nascia em cima, o que
  fechava o ciclo perverso "parar → população cai → Éden → comida grátis → clonar";
  agora a comida do resgate se conquista andando). Dispara uma vez por episódio
  (flag `_eden_active`).
- População == **0**: respawn de 10 criaturas Geração 0 (fallback de extinção total).

## 9. Feedback visual (frontend — BIT-10, 12, 15, 17, 18)

- **Cor da criatura** = idade + energia: azul `#3b82f6` (0–2s) → verde `#22c55e`
  (maduro, 2–10s) → gradiente contínuo verde→cinza (10–30s) → de cinza a quase-preto
  `#111827` conforme a energia esvai (30s+). Escala visual também varia com idade/energia.
- **Cones de visão** desenhados atrás do sprite (mesma geometria do backend).
- **Oásis** visíveis como gradiente verde com fade proporcional ao TTL restante.
- **Fundo aquático** em gradiente azul (coerente com o arrasto de água).
