# Spec — BIT-21: Ímpeto de Busca de Comida e Acasalamento

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação)

---

## Demanda

Mesmo depois do BIT-20 (que fez as criaturas se moverem em vez de girar paradas), falta o **ímpeto
direcionado**: os bibites passam perto de comida — inclusive no fim da vida, precisando de energia — e
**não mudam a trajetória para comer**; e cruzam com outro bibite pronto para procriar e **não acasalam**.
O objetivo é garantir, **desde o início** da simulação, que os bibites (a) virem em direção à comida que
enxergam e (b) efetivamente acasalem quando dois adultos prontos se encontram.

## Abordagem técnica

A raiz **não é o balanceamento de energia** (isso foi o BIT-20) — é que o cérebro NEAT é uma rede
feedforward de **pesos congelados no nascimento** e a Gen-0 nasce com pesos aleatórios: medido, só
**47,5%** das criaturas viram em direção à comida (puro acaso), e como a reprodução é ~0 a evolução
nunca corrige isso. A solução, no mesmo espírito da semente de `Motor_Forward` do BIT-20, é **semear
reflexos inatos evolutíveis na Gen-0**:

1. **Food-taxis:** semear os 9 pesos `visão[i] → Motor_Torque` para `STEER_GAIN*(i-4)`, fazendo a
   criatura virar em direção à comida fora do centro (medido: 97% da Gen-0 com `STEER_GAIN=1.0`).
2. **Ímpeto reprodutivo:** semear o bias de `Action_Mate` em `U(1.5, 2.5)`, fazendo ~93–99% dos
   adultos saciados *quererem* acasalar por padrão (era 56%).
3. **Neutralizar a repulsão entre parceiros:** a visão codifica criatura como sinal − (design do
   BIT-13), então a semente de food-taxis, sozinha, faria um adulto saciado FUGIR de parceiros. Em
   `compute_vision`, um observador **pronto para acasalar** passa a perceber outras criaturas como
   sinal **positivo** (atrativo), reaproveitando a mesma semente para puxá-lo na direção de parceiros.

São **sementes, não hardcodes**: mutação e crossover podem ajustar ou perder os reflexos (Gen-0 e
respawns do Éden passam por `create_zero_genome`; filhos não). Preserva a emergência — valor declarado
no BIT-20. **O contrato de I/O do NEAT não muda** (segue 16 inputs / 4 outputs, mesma ordem); só mudam
valores iniciais de pesos/bias e o valor condicional de um canal de visão.

Dependência: nenhuma task pendente. Constrói sobre o BIT-20 (já mergeado).

**Fora de escopo:** mudar a topologia/shape do NEAT, mecânica de grab/drop, e afrouxar a regra de
acasalamento no contato (o developer escolheu manter o cérebro no comando da decisão de acasalar).

## Arquivos a tocar

| Arquivo (path relativo à raiz) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/rtneat_wrapper.py` | modificar | Semear food-taxis (`visão→Motor_Torque`) e bias de `Action_Mate` em `create_zero_genome()` |
| `backend/simulation/sensors.py` | modificar | Neutralizar repulsão: adulto pronto percebe criaturas como sinal positivo; nova constante |
| `backend/tests/test_sensors.py` | modificar | Atualizar o teste de sinal de criatura (ready vs. not-ready); manter cobertura do caso negativo |
| `backend/tests/test_food_and_mate_seeking.py` | criar | Testes das sementes de food-taxis, `Action_Mate` e da neutralização |

## Passos de implementação

> Passos 1 e 2 são independentes entre si. Passo 3 (testes) depende de 1 e 2. Passo 4 valida tudo.

### 1. `rtneat_wrapper.py` — sementes de food-taxis e de ímpeto reprodutivo

Adicionar constantes de módulo, junto das já existentes de seed (`MOTOR_FORWARD_*`):

```python
# Seed de food-taxis (BIT-21): a Gen-0 nasce virando em direcao a comida que enxerga.
# Com weight_init_mean=0.0, os 9 pesos visao[i]->Motor_Torque nascem aleatorios N(0,1) e so 47,5%
# das criaturas viram para o lado certo da comida (medido). Semeando peso = STEER_GAIN*(i-4), o setor
# central (i=4) recebe 0 (segue reto) e as bordas recebem torque proporcional ao desvio, na direcao
# correta (torque + = CCW = setores i>4). Medido: 97% da Gen-0 vira para a comida com STEER_GAIN=1.0.
# SEED, nao hardcode: mutacao/crossover podem ajustar; filhos nao passam por aqui.
MOTOR_TORQUE_NODE_KEY = 1
FOOD_TAXIS_STEER_GAIN = 1.0

# Seed de impeto reprodutivo (BIT-21): adultos saciados nascem QUERENDO acasalar (Action_Mate=node 3).
# Com bias 0.0 so 56% dos adultos saciados disparam mate; com U(1.5,2.5) sobe para ~93-99% (medido),
# fazendo com que dois adultos prontos que se cruzam efetivamente acasalem. SEED evolutivel.
ACTION_MATE_NODE_KEY = 3
ACTION_MATE_SEED_BIAS_MIN = 1.5
ACTION_MATE_SEED_BIAS_MAX = 2.5
```

Em `create_zero_genome()`, **após** o seed de `Motor_Forward` já existente e **antes** do `return`:

```python
    # Food-taxis: vira em direcao a comida fora do centro (BIT-21).
    for i in range(9):  # 9 setores visuais; input node key = -(i+1)
        conn_key = (-(i + 1), MOTOR_TORQUE_NODE_KEY)
        if conn_key in genome.connections:
            genome.connections[conn_key].weight = FOOD_TAXIS_STEER_GAIN * (i - 4)

    # Impeto reprodutivo: adultos saciados nascem inclinados a acasalar (BIT-21).
    if ACTION_MATE_NODE_KEY in genome.nodes:
        genome.nodes[ACTION_MATE_NODE_KEY].bias = random.uniform(
            ACTION_MATE_SEED_BIAS_MIN, ACTION_MATE_SEED_BIAS_MAX
        )
    return genome
```

Atualizar a docstring do módulo mencionando as duas novas sementes junto do contrato de I/O (que
**não muda**).

### 2. `sensors.py` — neutralizar a repulsão entre parceiros

Adicionar constante de módulo (junto de `VISION_RADIUS` etc.):

```python
# BIT-21: fracao de energia a partir da qual um adulto passa a ser considerado "pronto para acasalar"
# para efeito de PERCEPCAO (nao e o limiar de reproducao do engine, que e absoluto = MIN_ENERGY_TO_MATE
# = 85). 0.85 espelha esse limiar sem acoplar sensors.py ao engine (evita import circular).
MATE_ATTRACTION_ENERGY_FRACTION = 0.85
```

Substituir o bloco final de `compute_vision()` (cálculo de `hunger`/`mate_drive` e preenchimento do
`vision`) por:

```python
    hunger = 1.0 - min(creature.energy / creature.max_energy, 1.0)
    energy_fraction = min(creature.energy / creature.max_energy, 1.0)
    is_adult = creature.life_stage == LifeStage.ADULT

    # Neutralizacao da repulsao (BIT-21): um adulto PRONTO para acasalar percebe outras criaturas como
    # sinal POSITIVO (atrativo) — assim a mesma semente de food-taxis o puxa na direcao de parceiros,
    # em vez de repeli-lo. Quem comer vs. acasalar no contato e resolvido pelo tipo de colisao no
    # engine, nao por este canal — logo "borrar" o sinal para um adulto pronto e inofensivo.
    observer_ready_to_mate = (
        is_adult
        and energy_fraction >= MATE_ATTRACTION_ENERGY_FRACTION
        and creature.reproduction_cooldown <= 0.0
    )
    mate_signal = energy_fraction if is_adult else 0.0
    creature_sign = 1.0 if observer_ready_to_mate else -1.0

    vision = [0.0] * NUM_VISION_SECTORS
    for i in range(NUM_VISION_SECTORS):
        if food_present[i]:
            vision[i] = hunger
        elif creature_present[i]:
            vision[i] = creature_sign * mate_signal
    return vision
```

> `creature.reproduction_cooldown` já é atributo da `Creature` (inicializado em `__init__`, decrementado
> em `update`). Em `compute_vision` ele carrega o valor do frame anterior — comportamento aceitável.

### 3. Testes

**`test_sensors.py`** — o comportamento de `test_creature_directly_ahead_within_fov_activates_center_cone`
muda: hoje um adulto **saciado** (energy=100) vê o parceiro como `-1.0`; agora, por estar *pronto para
acasalar*, vê `+1.0`. Atualizar essa asserção **e** adicionar um caso do observador NÃO pronto (energia
abaixo de `MATE_ATTRACTION_ENERGY_FRACTION`), que deve continuar vendo o sinal **negativo** (preserva o
design do BIT-13 para o caso comum):

```python
def test_ready_adult_perceives_partner_as_attractive():
    # BIT-21: adulto pronto para acasalar percebe outra criatura como sinal POSITIVO.
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.life_stage = LifeStage.ADULT
    creature.energy = 100.0            # >= 85% de max -> pronto
    creature.reproduction_cooldown = 0.0
    cx, cy = creature.body.position
    sim.add_creature(Creature(sim, x=cx + 50, y=cy))
    vision = compute_vision(creature, sim)
    assert vision[CENTER_SECTOR] == pytest.approx(1.0)
    assert sum(vision) == pytest.approx(1.0)


def test_not_ready_adult_still_perceives_creature_as_negative():
    # Observador ADULT mas com energia baixa (< limiar) -> sinal negativo preservado (design BIT-13).
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.life_stage = LifeStage.ADULT
    creature.energy = 50.0            # 0.5 < MATE_ATTRACTION_ENERGY_FRACTION
    cx, cy = creature.body.position
    sim.add_creature(Creature(sim, x=cx + 50, y=cy))
    vision = compute_vision(creature, sim)
    assert vision[CENTER_SECTOR] == pytest.approx(-0.5)
```

Substituir o corpo antigo de `test_creature_directly_ahead_within_fov_activates_center_cone` pelo novo
`test_ready_adult_perceives_partner_as_attractive` (ou renomear e ajustar). Importar
`MATE_ATTRACTION_ENERGY_FRACTION` de `simulation.sensors` (nunca hardcodar o valor).

**`test_food_and_mate_seeking.py`** — novo arquivo. Importar as constantes de
`simulation.rtneat_wrapper` e `simulation.sensors` (nunca hardcodar). Cobrir:

1. **Semente de food-taxis existe e tem o sinal certo** — sobre um genoma de `create_zero_genome()`,
   para cada `i` em `0..8`, `genome.connections[(-(i+1), MOTOR_TORQUE_NODE_KEY)].weight ==
   FOOD_TAXIS_STEER_GAIN*(i-4)`. Em particular o setor central (`i=4`) tem peso 0 e os pesos são
   estritamente crescentes de `i=0` (−4·gain) a `i=8` (+4·gain).
2. **Gen-0 vira em direção à comida** — monta um adulto faminto (`angle=0`) com comida a ~+40° do eixo
   frontal, roda `compute_vision` + `think`, afirma `motor_torque > 0` (vira CCW, na direção da comida).
   Espelhar para comida a −40° → `motor_torque < 0`. *Este é o teste que trava a regressão do sintoma.*
3. **Semente de `Action_Mate`** — sobre N genomas, `genome.nodes[ACTION_MATE_NODE_KEY].bias` está em
   `[ACTION_MATE_SEED_BIAS_MIN, ACTION_MATE_SEED_BIAS_MAX]`; e um adulto saciado sem nada em vista
   dispara `action_mate == True` após `think`.
4. **Neutralização puxa parceiros** — dois adultos saciados prontos: o observador com um parceiro a
   +40° gera `motor_torque > 0` (vira em direção ao parceiro, não para longe).
5. **Semente é evolutível, não global** — um filho criado via `clone_genome`/`organic_crossover` **não**
   é forçado a ter o peso semeado (i.e., a semente só se aplica em `create_zero_genome`). Basta afirmar
   que `clone_genome` preserva os pesos do pai (não re-semeia).

### 4. Validação

- `backend\venv\Scripts\python.exe -m pytest backend/tests/ -v` — suíte 100% verde.
- Smoke do loop real (importar `main`, rodar alguns segundos headless): sem exceções, payload do
  WebSocket inalterado.
- **Validação funcional (a que importa):** rodar via `manager.py` por alguns minutos e observar, desde o
  início, (a) criaturas **virando e indo em direção à comida** que aparece no campo de visão — inclusive
  desviando a trajetória para comer ao passar perto; (b) **acasalamentos acontecendo** quando dois
  adultos prontos se encontram (novos EGGs surgindo por encontro, não só por clonagem solitária).

## Contratos técnicos

### Backend (Simulação)

**`rtneat_wrapper.py`** — constantes novas: `MOTOR_TORQUE_NODE_KEY = 1`, `FOOD_TAXIS_STEER_GAIN = 1.0`,
`ACTION_MATE_NODE_KEY = 3`, `ACTION_MATE_SEED_BIAS_MIN = 1.5`, `ACTION_MATE_SEED_BIAS_MAX = 2.5`.
`create_zero_genome(genome_id, config)` mantém a assinatura; passa a semear os 9 pesos
`visão[i]→Motor_Torque` para `FOOD_TAXIS_STEER_GAIN*(i-4)` e `nodes[3].bias` em `U(1.5, 2.5)`.

**`sensors.py`** — constante nova `MATE_ATTRACTION_ENERGY_FRACTION = 0.85`. `compute_vision(creature,
engine)` mantém a assinatura e o formato de retorno (lista de 9 floats); muda apenas o **sinal** do
canal de criatura quando o observador é um adulto pronto para acasalar (passa de − para +).

### API/WebSocket
**Nenhuma mudança.** Nenhum campo novo, nenhum formato alterado. `to_dict()`/`get_state()` intactos.

### Frontend
**Nenhuma mudança.**

### Contrato de I/O do NEAT
**Inalterado** — 16 inputs, 4 outputs, mesma ordem e semântica. As sementes alteram apenas *valores
iniciais* de pesos/bias; genomas antigos permanecem compatíveis.

## Critérios de aceite

- [ ] Sobre um genoma de `create_zero_genome()`, os 9 pesos `visão[i]→Motor_Torque` valem exatamente
      `FOOD_TAXIS_STEER_GAIN*(i-4)` (setor central = 0; monotônicos de −4·gain a +4·gain).
- [ ] Um adulto faminto com comida a +40° do eixo frontal produz `motor_torque > 0` (vira em direção à
      comida); a −40°, `motor_torque < 0`. *(Trava a regressão do sintoma "passa perto e não vira".)*
- [ ] `nodes[ACTION_MATE_NODE_KEY].bias ∈ [1.5, 2.5]` em 100% dos genomas de `create_zero_genome()`, e
      um adulto saciado sem nada em vista dispara `action_mate == True` após `think()`.
- [ ] Um observador **adulto pronto** (ADULT, `energy_fraction ≥ 0.85`, cooldown 0) percebe outra
      criatura à frente como sinal **positivo**; um adulto **não pronto** (energia < limiar) continua
      percebendo como **negativo** (design do BIT-13 preservado para o caso comum).
- [ ] A semente é evolutível: filhos (`clone_genome`/`organic_crossover`) **não** são re-semeados.
- [ ] `pytest backend/tests/` 100% verde.
- [ ] **Validação funcional:** rodando via `manager.py`, desde os primeiros segundos as criaturas
      **desviam a trajetória para comer** ao enxergar comida, e **acasalam ao se encontrarem** (novos
      EGGs por encontro, não só por clonagem).

## Rollback

Reverter `backend/simulation/rtneat_wrapper.py` e `backend/simulation/sensors.py`, restaurar
`backend/tests/test_sensors.py` e deletar `backend/tests/test_food_and_mate_seeking.py`. Nenhuma
migração de dados, nenhum contrato externo tocado — `git checkout -- backend/simulation/ backend/tests/`
e remover o arquivo novo.

**Se o esterço sair errado** (criaturas girando demais / orbitando comida sem chegar), ajustar
`FOOD_TAXIS_STEER_GAIN` na escada `1.0 → 0.5` (menos esterço) sem mudar a estrutura. Se acasalamento
ainda for raro, subir `ACTION_MATE_SEED_BIAS_*` (ex.: `U(2.0, 3.0)` → ~100%) e/ou verificar a densidade
populacional/encontros nos oásis (fora do escopo desta task; candidato a um BIT seguinte sobre
`VISION_RADIUS`/densidade).
