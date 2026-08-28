## Arquivos relevantes

- `backend/simulation/rtneat_wrapper.py` — contém todas as constantes seed e a função `create_zero_genome`
- `backend/tests/test_food_and_mate_seeking.py` — testes de comportamento emergente das seeds (food-taxis + mate)
- `backend/tests/test_rtneat_wrapper.py` — testes estruturais do genoma (sem dependência de valores seed)
- `backend/tests/test_exploration_pressure.py` — importa MOTOR_FORWARD_SEED_BIAS_MIN/MAX e MOTOR_FORWARD_NODE_KEY

## Conteúdo relevante para a demanda

### Constantes em `rtneat_wrapper.py` (linhas 53-71)

```python
# Seed de locomoção (BIT-20) — NÃO ALTERAR
MOTOR_FORWARD_NODE_KEY = 0
MOTOR_FORWARD_SEED_BIAS_MIN = 0.3   # mantém
MOTOR_FORWARD_SEED_BIAS_MAX = 1.0   # mantém

# Seed de food-taxis (BIT-21) — REDUZIR
MOTOR_TORQUE_NODE_KEY = 1
FOOD_TAXIS_STEER_GAIN = 1.0         # será 0.5

# Seed de ímpeto reprodutivo (BIT-21) — REDUZIR
ACTION_MATE_NODE_KEY = 3
ACTION_MATE_SEED_BIAS_MIN = 1.5     # será 0.8
ACTION_MATE_SEED_BIAS_MAX = 2.5     # será 1.5
```

### Função `create_zero_genome` (linhas 102-126)

Aplica as três seeds ao criar genomas de Gen-0. Os filhos (clone/crossover) não passam por aqui — a seed é evolutível. A lógica permanece intacta; só os valores das constantes mudam.

### Testes afetados em `test_food_and_mate_seeking.py`

**Grupo 1 — testes de estrutura da seed (linhas 60-81):**
- `test_food_taxis_seed_weights_are_seeded_with_correct_sign` (linha 60): verifica que o peso de cada conexão = `FOOD_TAXIS_STEER_GAIN * (i - 4)`. Como o teste importa a constante (não hardcoda 1.0), continuará passando com STEER_GAIN=0.5.
- `test_food_taxis_center_sector_is_zero_and_weights_are_monotonic` (linha 71): testa `weights[0] == approx(-4 * FOOD_TAXIS_STEER_GAIN)` e `weights[8] == approx(4 * FOOD_TAXIS_STEER_GAIN)`. Como importa a constante, passará com 0.5.

**Grupo 2 — testes de comportamento emergente (linhas 94-111):**
- `test_gen0_turns_toward_food_on_the_left` (linha 94): afirma `motor_torque > 0.0` com comida a +40 graus. Com STEER_GAIN=0.5, o torque cai pela metade mas continua positivo (o setor i=6 ou i=7 terá peso ~1.0-1.5, ainda dominante). PASSA SEM ALTERAÇÃO.
- `test_gen0_turns_toward_food_on_the_right` (linha 104): análogo, afirma `motor_torque < 0.0`. PASSA SEM ALTERAÇÃO.

**Grupo 3 — seed de Action_Mate (linhas 116-144):**
- `test_action_mate_bias_seeded_within_range` (linha 116): verifica `ACTION_MATE_SEED_BIAS_MIN <= bias <= ACTION_MATE_SEED_BIAS_MAX`. Como importa as constantes, passará automaticamente com os novos valores (0.8-1.5).
- `test_sated_adult_wants_to_mate_with_nothing_in_sight` (linha 132): afirma `fraction >= MIN_SUCCESS_FRACTION` (0.85) com N=200. Com bias U(0.8, 1.5), a taxa de Action_Mate ativado precisa ser recalibrada.

**Análise crítica de `test_sated_adult_wants_to_mate_with_nothing_in_sight`:**

O threshold tanh é 0.0 (neat-python usa `tanh` para os outputs e o output_threshold padrão para binário em `creature.py`). Com bias U(0.8, 1.5), a ativação `tanh(bias + weight*0 + ...)` com todos os inputs zero:
- bias=0.8 → tanh(0.8) ≈ 0.664 > 0 → Action_Mate=True
- bias=1.5 → tanh(1.5) ≈ 0.905 > 0 → Action_Mate=True
- Todo o range U(0.8, 1.5) produz tanh > 0 → 100% de ativação com inputs zerados.

Portanto `fraction >= 0.85` (MIN_SUCCESS_FRACTION) continuará passando sem alteração — na prática, fraction ≈ 1.0 pois qualquer bias > 0 em cenário de inputs zero ativa o mate.

**Grupo 4 — neutralização de parceiros (linhas 149-173):**
- `test_ready_adult_turns_toward_partner` (linha 149): afirma `fraction >= MIN_SUCCESS_FRACTION (0.85)`. Com STEER_GAIN=0.5, os pesos de torque são menores mas ainda corretos em sinal. O resultado depende de aleatoriedade dos outros pesos do genoma — análise conservadora: o limiar 0.85 pode ficar mais apertado.

**Grupo 5 — seed é evolutível (linha 178):**
- `test_clone_preserves_parent_weights_without_reseeding` (linha 178): sem dependência de valores específicos. PASSA SEM ALTERAÇÃO.

### Testes em `test_exploration_pressure.py`

- Linha 201-202: `assert MOTOR_FORWARD_SEED_BIAS_MIN <= bias <= MOTOR_FORWARD_SEED_BIAS_MAX` — MOTOR_FORWARD não muda. PASSA.
- Nenhum outro assert depende de FOOD_TAXIS ou ACTION_MATE.

### Testes em `test_rtneat_wrapper.py`

Nenhum assert depende de valores de seeds food-taxis ou action_mate. TUDO PASSA.

## O que precisa ser feito

1. Alterar `FOOD_TAXIS_STEER_GAIN` de `1.0` para `0.5` em `rtneat_wrapper.py` (linha 64)
2. Alterar `ACTION_MATE_SEED_BIAS_MIN` de `1.5` para `0.8` em `rtneat_wrapper.py` (linha 70)
3. Alterar `ACTION_MATE_SEED_BIAS_MAX` de `2.5` para `1.5` em `rtneat_wrapper.py` (linha 71)
4. Atualizar os comentários das constantes para refletir as novas porcentagens calibradas
5. Verificar que nenhum teste hardcoda os valores antigos (todos importam as constantes — confirmado)

## Perguntas em aberto

- `test_ready_adult_turns_toward_partner` com STEER_GAIN=0.5: o limiar MIN_SUCCESS_FRACTION=0.85 pode ficar mais justo, mas com seed.42 e N=200 o risco é baixo dado que o sinal ainda está correto. Se flaky aparecer, MIN_SUCCESS_FRACTION pode ser reduzido para 0.75.
- Nenhuma outra pergunta em aberto — todos os testes importam constantes, não hardcodam valores.
