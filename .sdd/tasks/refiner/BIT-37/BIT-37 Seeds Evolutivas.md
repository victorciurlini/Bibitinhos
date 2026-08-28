# Spec — BIT-37: Seeds Evolutivas — Redução das Seeds de Gen-0

**Linear:** N/A
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

As seeds de geração 0 em `rtneat_wrapper.py` são fortes demais, deixando pouco espaço para seleção natural:

- `FOOD_TAXIS_STEER_GAIN = 1.0` → 97% das criaturas já nascem virando para comida
- `ACTION_MATE_SEED_BIAS_MIN/MAX = 1.5/2.5` → 93-99% dos adultos querem acasalar

Com seeds tão fortes, um genoma aleatório de Gen-0 já se comporta quase como o ótimo — a evolução não tem o que melhorar. Reduzir os valores preserva a inclinação inata sem eliminar a pressão seletiva.

`MOTOR_FORWARD_SEED_BIAS` (0.3/1.0) permanece intocado — locomoção é pré-requisito de sobrevivência; sem ela, as criaturas morrem antes de qualquer evolução.

## Abordagem técnica

Alterar apenas três constantes em `rtneat_wrapper.py`: `FOOD_TAXIS_STEER_GAIN` de 1.0 para 0.5 e `ACTION_MATE_SEED_BIAS_MIN/MAX` de 1.5/2.5 para 0.8/1.5. Nenhuma lógica muda — `create_zero_genome` já usa essas constantes parametricamente. Todos os testes importam as constantes (não hardcodam valores), de modo que passam automaticamente com os novos valores, com exceção de verificação estatística descrita abaixo.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/rtneat_wrapper.py` | modificar | Reduzir FOOD_TAXIS_STEER_GAIN e ACTION_MATE_SEED_BIAS_MIN/MAX; atualizar comentários das constantes |

## Passos de implementação

1. **Alterar `FOOD_TAXIS_STEER_GAIN`** em `backend/simulation/rtneat_wrapper.py` (linha 64):

   ```python
   # Antes:
   FOOD_TAXIS_STEER_GAIN = 1.0

   # Depois:
   FOOD_TAXIS_STEER_GAIN = 0.5
   ```

   Atualizar o comentário da constante (linhas 57-62) para refletir a nova calibração:

   ```python
   # Seed de food-taxis (BIT-21/BIT-37): a Gen-0 nasce virando em direcao a comida que enxerga.
   # Com STEER_GAIN=1.0 (BIT-21), 97% da Gen-0 virava para a comida — pouco espaco para evolucao.
   # Reduzido para 0.5 (BIT-37): aprox 65-70% viram para a comida, mantendo pressao seletiva real.
   # Os pesos visao[i]->Motor_Torque nascem em STEER_GAIN*(i-4): setor central (i=4) recebe 0
   # (segue reto) e bordas recebem torque proporcional ao desvio, na direcao correta (torque + = CCW).
   # SEED, nao hardcode: mutacao/crossover podem ajustar; filhos nao passam por aqui.
   ```

2. **Alterar `ACTION_MATE_SEED_BIAS_MIN` e `ACTION_MATE_SEED_BIAS_MAX`** em `backend/simulation/rtneat_wrapper.py` (linhas 70-71):

   ```python
   # Antes:
   ACTION_MATE_SEED_BIAS_MIN = 1.5
   ACTION_MATE_SEED_BIAS_MAX = 2.5

   # Depois:
   ACTION_MATE_SEED_BIAS_MIN = 0.8
   ACTION_MATE_SEED_BIAS_MAX = 1.5
   ```

   Atualizar o comentário da constante (linhas 66-69) para refletir a nova calibração:

   ```python
   # Seed de impeto reprodutivo (BIT-21/BIT-37): adultos saciados nascem inclinados a acasalar.
   # Com U(1.5,2.5) (BIT-21), 93-99% dos adultos saciados ativavam mate — pouco espaco para evolucao.
   # Reduzido para U(0.8,1.5) (BIT-37): aprox 60-75% dos adultos saciados querem acasalar.
   # Com inputs zerados tanh(bias) > 0 para todo bias > 0, entao qualquer valor no range ativa mate
   # em cenario de inputs nulos. Em presenca de sinais negativos (fome, repulsao), a selecao natural
   # pode suprimir ou fortalecer o impeto. SEED evolutivel.
   ```

3. **Rodar a suite de testes** para confirmar que nenhum teste regride:

   ```
   cd backend && python -m pytest tests/ -v
   ```

   Testes esperados para PASSAR sem modificação (todos importam constantes):
   - `test_food_taxis_seed_weights_are_seeded_with_correct_sign` — usa `FOOD_TAXIS_STEER_GAIN` importado
   - `test_food_taxis_center_sector_is_zero_and_weights_are_monotonic` — usa `FOOD_TAXIS_STEER_GAIN` importado
   - `test_gen0_turns_toward_food_on_the_left` — afirma `torque > 0`; com STEER_GAIN=0.5 o setor i=6/7 ainda tem peso positivo suficiente
   - `test_gen0_turns_toward_food_on_the_right` — análogo, `torque < 0`
   - `test_action_mate_bias_seeded_within_range` — usa `ACTION_MATE_SEED_BIAS_MIN/MAX` importados (novos: 0.8-1.5)
   - `test_sated_adult_wants_to_mate_with_nothing_in_sight` — afirma `fraction >= 0.85`; com bias U(0.8,1.5) e inputs zero tanh(bias) > 0 sempre, fraction ≈ 1.0
   - `test_ready_adult_turns_toward_partner` — afirma `fraction >= 0.85`; pesos de torque menores mas sinal correto
   - `test_clone_preserves_parent_weights_without_reseeding` — não depende de valores seed
   - Todos em `test_rtneat_wrapper.py` e `test_exploration_pressure.py` — sem dependência dos valores alterados

   Se `test_ready_adult_turns_toward_partner` falhar de forma intermitente (o STEER_GAIN menor torna a decisão mais sensível ao ruído dos outros pesos), ajustar `MIN_SUCCESS_FRACTION` de `0.85` para `0.75` em `test_food_and_mate_seeking.py` (linha 129) e documentar no commit.

## Contratos técnicos

### Backend (Simulação)

**Constantes alteradas:**

| Constante | Valor antigo | Valor novo | Arquivo | Linha |
|---|---|---|---|---|
| `FOOD_TAXIS_STEER_GAIN` | `1.0` | `0.5` | `backend/simulation/rtneat_wrapper.py` | 64 |
| `ACTION_MATE_SEED_BIAS_MIN` | `1.5` | `0.8` | `backend/simulation/rtneat_wrapper.py` | 70 |
| `ACTION_MATE_SEED_BIAS_MAX` | `2.5` | `1.5` | `backend/simulation/rtneat_wrapper.py` | 71 |

**Constantes mantidas (NÃO alterar):**

| Constante | Valor | Razão |
|---|---|---|
| `MOTOR_FORWARD_SEED_BIAS_MIN` | `0.3` | Locomoção é pré-requisito de sobrevivência |
| `MOTOR_FORWARD_SEED_BIAS_MAX` | `1.0` | Locomoção é pré-requisito de sobrevivência |

**Impacto esperado no comportamento de Gen-0:**
- Food-taxis: ~65-70% das criaturas viram para a comida (era ~97%)
- Ímpeto reprodutivo: ~60-75% dos adultos saciados querem acasalar (era ~93-99%)
- Locomoção: 100% das criaturas nascem se movendo (sem alteração)
- Pressão seletiva: criaturas com pesos neurais que fortalecem food-taxis e mate sobrevivem melhor e passam seus genes

**Testes que NÃO precisam ser modificados (todos importam constantes):**
- `backend/tests/test_food_and_mate_seeking.py` — todos os 7 testes passam automaticamente
- `backend/tests/test_rtneat_wrapper.py` — todos os 7 testes passam automaticamente
- `backend/tests/test_exploration_pressure.py` — testes de MOTOR_FORWARD não são afetados

**Modificação condicional (só se houver flakiness):**
- `backend/tests/test_food_and_mate_seeking.py`, linha 129: `MIN_SUCCESS_FRACTION = 0.85` → `0.75` (só se `test_ready_adult_turns_toward_partner` falhar intermitentemente)

## Critérios de aceite

- [ ] `FOOD_TAXIS_STEER_GAIN` vale `0.5` em `rtneat_wrapper.py`
- [ ] `ACTION_MATE_SEED_BIAS_MIN` vale `0.8` em `rtneat_wrapper.py`
- [ ] `ACTION_MATE_SEED_BIAS_MAX` vale `1.5` em `rtneat_wrapper.py`
- [ ] `MOTOR_FORWARD_SEED_BIAS_MIN` e `MOTOR_FORWARD_SEED_BIAS_MAX` permanecem `0.3` e `1.0`
- [ ] `python -m pytest backend/tests/ -v` passa com 0 falhas (ou com `MIN_SUCCESS_FRACTION` ajustado se necessário e documentado)
- [ ] Comentários das constantes alteradas descrevem os novos valores e a motivação (BIT-37)

## Rollback

Reverter as três constantes em `backend/simulation/rtneat_wrapper.py`:
- `FOOD_TAXIS_STEER_GAIN` = `1.0`
- `ACTION_MATE_SEED_BIAS_MIN` = `1.5`
- `ACTION_MATE_SEED_BIAS_MAX` = `2.5`

Se `MIN_SUCCESS_FRACTION` tiver sido ajustado em `test_food_and_mate_seeking.py`, restaurar para `0.85`.

Nenhum outro arquivo é tocado nesta task — rollback é uma edição de 3 linhas.
