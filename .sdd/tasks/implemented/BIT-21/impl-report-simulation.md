# Relatório de Implementação — BIT-21 (Simulação)

## Status
CONCLUÍDO

## Passos executados
1. Li a spec completa e os quatro arquivos-alvo. Confirmei `MIN_ENERGY_TO_MATE = 65.0` em
   `engine.py` (retunado desde o valor 85 citado na spec).
2. `rtneat_wrapper.py`: adicionei as constantes de módulo (`MOTOR_TORQUE_NODE_KEY`,
   `FOOD_TAXIS_STEER_GAIN`, `ACTION_MATE_NODE_KEY`, `ACTION_MATE_SEED_BIAS_MIN/MAX`); em
   `create_zero_genome()`, após o seed de `Motor_Forward` e antes do `return`, semeei os 9 pesos
   `visão[i]→Motor_Torque` = `FOOD_TAXIS_STEER_GAIN*(i-4)` e o bias de `Action_Mate` em
   `U(1.5, 2.5)`; atualizei a docstring do módulo mencionando as duas sementes (contrato de I/O
   inalterado).
3. `sensors.py`: adicionei `MATE_ATTRACTION_ENERGY_FRACTION` e substituí o bloco final de
   `compute_vision()` pela lógica de neutralização condicional (adulto pronto → sinal positivo).
4. `test_sensors.py`: substituí `test_creature_directly_ahead_within_fov_activates_center_cone`
   por `test_ready_adult_perceives_partner_as_attractive` (+1.0) e adicionei
   `test_not_ready_adult_still_perceives_creature_as_negative` (energia abaixo do limiar → sinal
   negativo). Importei a constante em vez de hardcodar.
5. `test_food_and_mate_seeking.py`: criei o arquivo com os 5 grupos de teste, importando
   constantes de `rtneat_wrapper` e `sensors`.
6. Rodei os gates (import main + pytest), corrigi um índice de setor no meu próprio teste e
   validei.

## Arquivos modificados
- `backend/simulation/rtneat_wrapper.py` — sementes de food-taxis (9 pesos
  `visão[i]→Motor_Torque`) e de ímpeto reprodutivo (bias de `Action_Mate`) em
  `create_zero_genome()`; constantes de módulo novas; docstring atualizada. Contrato de I/O
  intacto (16/4).
- `backend/simulation/sensors.py` — constante `MATE_ATTRACTION_ENERGY_FRACTION` e neutralização
  condicional da repulsão em `compute_vision()` (só muda o SINAL do canal de criatura quando o
  observador é adulto pronto). Assinatura e formato de retorno inalterados.
- `backend/tests/test_sensors.py` — teste de sinal de criatura atualizado para o novo semantics
  (ready → +) e caso not-ready adicionado (mantém o negativo do design BIT-13).
- `backend/tests/test_food_and_mate_seeking.py` — novo; 5 grupos: (1) semente de food-taxis
  existe/sinal/monotonicidade; (2) Gen-0 vira para comida a ±40° (`motor_torque` >0 / <0);
  (3) bias de `Action_Mate` no range e adulto saciado dispara `action_mate`; (4) neutralização
  puxa parceiro (torque >0, sem sinal negativo); (5) `clone_genome` não re-semeia (preserva pesos
  do pai).

## Problemas encontrados
- **DIVERGÊNCIA da spec — `MATE_ATTRACTION_ENERGY_FRACTION = 0.65` (não 0.85):** a spec escreveu
  0.85 para espelhar o `MIN_ENERGY_TO_MATE` da época (85). Esse limiar foi retunado e hoje vale
  `MIN_ENERGY_TO_MATE = 65.0` (confirmado em `engine.py`). Para preservar a intenção declarada
  ("espelhar o limiar do engine sem acoplar sensors.py a ele"), usei 0.65 e deixei um comentário
  explicando que espelha o valor atual de 65 (a spec citava 0.85 por referenciar o antigo 85).
  Os testes importam a constante, então nada quebra com esse ajuste.
- **Falha PRÉ-EXISTENTE, fora do escopo:** `test_exploration_pressure.py::test_newborn_still_has_to_eat_before_mating`
  falha com `assert MIN_ENERGY_TO_MATE > STARTING_ENERGY` (65 > 75). É um invariante estático de
  outro BIT (retuning de `MIN_ENERGY_TO_MATE` de 85→65 abaixo de `STARTING_ENERGY=75`), no arquivo
  `test_exploration_pressure.py` que já estava untracked antes desta task. Não tem relação com as
  edições de BIT-21 (não toquei `engine.py` nem `creature.py`). NÃO enfraqueci esse teste — deixei
  a decisão para o orquestrador, pois mexe na semântica de outra área (metabolismo/reprodução).
- Ajuste no meu próprio teste `test_ready_adult_turns_toward_partner`: parceiro a +40° cai no
  setor 7 (não 6, pela largura de 13,33°/setor). Troquei a asserção fixa por
  `any(v>0 for v in vision[5:])` + `all(v>=0)`, que valida a atração sem depender do índice exato.

## Resultado dos gates
- `import main` → `OK`
- `pytest tests/`: **114 passed, 1 failed** (a única falha é a pré-existente
  `test_exploration_pressure.py::test_newborn_still_has_to_eat_before_mating`, fora do escopo
  BIT-21). Todos os 21 testes de BIT-21 (`test_food_and_mate_seeking.py` + `test_sensors.py`
  atualizado) passam.
