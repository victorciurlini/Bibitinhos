# Research — BIT-21: Ímpeto de busca de comida e acasalamento (camada Simulação)

## Arquivos relevantes

- `backend/simulation/rtneat_wrapper.py` — `create_zero_genome()` (semente da Gen-0), contrato de I/O da rede
- `backend/simulation/sensors.py` — `compute_vision()` (visão em 9 setores com sinal), constantes de visão
- `backend/simulation/creature.py` — `Creature.think()` (roda a rede, cacheia atuadores), `update()` (aplica torque/thrust), atributo `reproduction_cooldown`
- `backend/simulation/engine.py` — handlers de colisão criatura×criatura (reprodução sexuada) e laço de reprodução assexuada; constantes de reprodução
- `backend/simulation/neat_config.ini` — topologia `full_direct`, 16 inputs / 4 outputs
- `backend/tests/test_sensors.py` — testes de `compute_vision` (um deles muda de comportamento)
- `.sdd/tasks/implemented/BIT-20/` — task anterior (mesmo sintoma, atacado pelo lado da economia de energia)

## Contexto do BIT-20 (task imediatamente anterior)

O BIT-20 inverteu a economia de energia (ficar parado girando virou a PIOR estratégia) e semeou o
bias de `Motor_Forward` para 100% da Gen-0 nascer capaz de ANDAR. A evidência do BIT-20 mediu que o
comportamento reclamado caiu de 66% para 20% das amostras. **Mas deixou dois furos explícitos**, que
são exatamente a demanda desta task:

1. A semente faz a criatura ANDAR, mas não faz ela VIRAR em direção à comida. O cérebro é uma rede
   feedforward de pesos congelados no nascimento (NEAT não aprende dentro de uma vida — só evolui
   entre gerações via reprodução).
2. A reprodução sexuada continua em ~0 — a evidência do BIT-20 diagnosticou "bloqueada por
   probabilidade de encontro + simultaneidade", não por energia.

## Diagnóstico da raiz (validado empiricamente neste ambiente)

### Busca de comida
Com `initial_connection = full_direct` e `weight_init_mean=0.0, stdev=1.0`, cada setor visual tem uma
conexão direta para `Motor_Torque` (output node 1) com peso aleatório N(0,1). Metade dos genomas vira
para o lado ERRADO da comida. Medido (200 genomas, comida a +40° do eixo frontal):

- **Baseline (pesos aleatórios): 47,5%** viram em direção à comida — puro acaso. **Esta é a raiz.**
- Semeando os 9 pesos `visão[i] → Motor_Torque` para `GAIN*(i-4)`:
  - gain=0.5 → 83% | **gain=1.0 → 97%** | gain=2.0 → 100%

Como a evolução mal acontece (reprodução ≈ 0), a seleção nunca corrige o viés → o usuário vê para
sempre criaturas ignorando comida. A semente resolve "desde o início" sem depender da evolução.

### Convenções físicas confirmadas ao vivo (Pymunk + geometria dos setores)
- Torque **positivo → rotação anti-horária (CCW)**, `body.angle` aumenta.
- "Frente" = eixo local +x = direção de `body.angle` (`apply_impulse_at_local_point((thrust,0))`).
- Objeto em `relative_angle > 0` cai em **setor index > 4** e exige **torque positivo** para virar em
  direção a ele. Logo: torque_em_direção_ao_objeto ∝ `(i - 4)`. Setor central (4) → torque 0
  (segue reto; a semente de `Motor_Forward` do BIT-20 cuida do avanço).

### Estrutura do genoma confirmada ao vivo
- `genome.nodes.keys()` de output = `[0, 1, 2, 3]` → `Motor_Forward`=0, `Motor_Torque`=1,
  `Action_Grab_Drop`=2, `Action_Mate`=3.
- `full_direct` gera **64 conexões**; `genome.connections[(-(i+1), 1)]` existe para os 9 setores
  visuais (`i=0..8`, node de input `-(i+1)`) → `Motor_Torque`. Pode-se setar `.weight` diretamente.
- Semear é feito em `create_zero_genome()` (Gen-0 e respawns do Éden). **Filhos (crossover/clone)
  NÃO passam por lá** — herdam e mutam. É um SEED, não hardcode (mesmo padrão do BIT-20).

### Acasalamento
Bloqueio triplo numa colisão: ambos ADULT + ambos `action_mate=True` no MESMO frame + ambos
`energy ≥ MIN_ENERGY_TO_MATE (85)` + cooldown 0. Com cérebro aleatório, `action_mate` (`outputs[3]>0`)
é ~coin-flip e só muda a cada brain tick (10 Hz) → dois adultos que se cruzam raramente disparam mate
juntos. Medido: com bias 0.0 em `Action_Mate`, só **56%** dos adultos saciados querem acasalar.
Semeando o bias de `Action_Mate`:
- bias=1.5 → 93% | bias=2.0 → 99% | bias=3.0 → 100%. Faixa `U(1.5, 2.5)` dá ~93–99%.

**Conflito de sinal (decidido com o developer):** a visão codifica comida como sinal + e outra
criatura como − (design do BIT-13, para o cérebro distinguir comer de acasalar). Numa rede linear, a
mesma semente de direção que atrai para comida (+) REPELE criaturas (−). Pior: um adulto saciado tem
`mate_drive = energy_fraction` alto → repulsão forte → foge de parceiros.

Medido (dois adultos saciados em rota de colisão frontal, 40 trials, 10 s):
- com repulsão: 13/40 colisões | com neutralização: 16/40. **A repulsão é em grande parte inócua**
  porque em rota frontal o parceiro fica no setor central (i≈4 → torque ≈ 0). A neutralização ajuda
  modestamente e, ao converter repulsão em atração leve, favorece a aglomeração em oásis.

**Decisão do developer:** "Semente de ímpeto + neutralizar repulsão" — semear bias + em `Action_Mate`
e neutralizar a repulsão entre parceiros. A neutralização escolhida: em `compute_vision`, quando o
OBSERVADOR é um adulto pronto para acasalar (ADULT + `energy_fraction ≥ 0.85` + cooldown 0), outras
criaturas viram sinal POSITIVO (atrativo). Isso reaproveita a mesma semente de food-taxis para puxar
adultos prontos na direção de parceiros. Não muda o SHAPE do contrato de I/O (segue 16 in / 4 out);
muda apenas o VALOR de um canal, condicionalmente. O resultado no CONTATO (comer vs. acasalar) é
resolvido pelo tipo de colisão no engine, não pelo canal de visão — então "borrar" o sinal para um
adulto pronto é inócuo.

## O que precisa ser feito

1. `rtneat_wrapper.py` / `create_zero_genome()`: semear (a) os 9 pesos `visão→Motor_Torque` para
   `STEER_GAIN*(i-4)` (food-taxis) e (b) o bias de `Action_Mate` (node 3) em `U(1.5, 2.5)`.
2. `sensors.py` / `compute_vision()`: neutralizar a repulsão — adulto pronto percebe criaturas como
   sinal positivo. Nova constante `MATE_ATTRACTION_ENERGY_FRACTION = 0.85`.
3. Testes: novo `test_food_and_mate_seeking.py`; atualizar `test_sensors.py`
   (`test_creature_directly_ahead_within_fov_activates_center_cone` muda de sinal para adulto pronto).

## Perguntas em aberto
- Nenhuma bloqueante. `STEER_GAIN=1.0` e faixa de `Action_Mate` já validados; se a validação funcional
  headless mostrar sub/super-esterço, ajustar `STEER_GAIN` (escada 0.5 → 1.0 → 1.5) sem mudar estrutura.
