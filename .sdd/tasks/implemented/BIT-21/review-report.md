# Review Report — BIT-21: Ímpeto de Busca de Comida e Acasalamento

## Veredito
APROVADO COM RESSALVAS

## Resultado dos gates (rodados por mim)
- `import main`: OK
- `pytest tests/`: 115 passed / 1 failed
  - A única falha é `test_exploration_pressure.py::test_newborn_still_has_to_eat_before_mating`
    (`assert MIN_ENERGY_TO_MATE > STARTING_ENERGY` → `65.0 > 75.0`).
  - **Confirmado PRÉ-EXISTENTE e FORA DE ESCOPO** (evidência abaixo).
- Todos os 21 testes de BIT-21 (`test_food_and_mate_seeking.py` + `test_sensors.py`) passam
  numa execução única.

## Achados

### [MELHORIA] test_food_and_mate_seeking.py:123 e :134 — dois testes de comportamento são FLAKY
Rodando cada teste 20x isoladamente:
- `test_sated_adult_wants_to_mate_with_nothing_in_sight` → 3/20 falharam (~15%).
- `test_ready_adult_turns_toward_partner` → 2/20 falharam (~10%).
- `test_gen0_turns_toward_food_on_the_left` e `_right` → 0/20 (estáveis).

Causa-raiz: `create_zero_genome()` usa `random.uniform` **sem seed** — cada genoma nasce com
pesos aleatórios nas outras 15 conexões input→output (Energy_Level, Kinetic_Feedback, etc.) e um
bias de `Action_Mate` sorteado em `[1.5, 2.5]`. Esses dois testes afirmam um comportamento que a
própria spec mede como **probabilístico (~93–99%)** como se fosse determinístico, sobre UM único
genoma:
- No teste de mate: `action_mate = outputs[3] > 0.0 = tanh(bias + Σ pesos·inputs) > 0`. Com adulto
  saciado e nada em vista, os canais não-visuais (Energy_Level=1.0, Kinetic, Load) entram por pesos
  aleatórios e ocasionalmente vencem o bias positivo → `action_mate == False`.
- No teste de atração ao parceiro: idem — o torque resultante depende também dos pesos aleatórios
  dos outros inputs para Motor_Torque, que às vezes invertem o sinal do único setor de visão ativo.

Os testes de food-taxis (grupos 1 e 2) NÃO têm esse problema: o grupo 1 checa pesos exatos (semente
pura, determinística) e o grupo 2 usa `energy=0.0` (fome máxima = sinal de visão forte = 1.0) que
domina o ruído — por isso ficam verdes 20/20.

Sugestão (não bloqueia o fechamento; decisão do orquestrador): tornar determinísticos com
`random.seed(...)` no setup, OU converter em teste estatístico (rodar N genomas e afirmar taxa ≥ ~90%,
espelhando o número que a spec cita), OU usar `create_zero_genome` + zerar manualmente os pesos
não-relevantes antes do `think`. Como estão, podem quebrar o CI intermitentemente.

### [MELHORIA] sensors.py:18 — divergência 0.85→0.65 é justificada, mas acopla um número mágico frágil
O implementer trocou `MATE_ATTRACTION_ENERGY_FRACTION = 0.85` (da spec) por `0.65` para "espelhar"
`MIN_ENERGY_TO_MATE = 65.0` (confirmado em engine.py:26). A intenção declarada na spec era espelhar o
limiar do engine sem acoplar sensors.py a ele — logo 0.65 é **coerente com a intenção** e o desvio é
justificável. Ressalva: é uma constante que precisa ser mantida à mão em sincronia com engine.py; se
`MIN_ENERGY_TO_MATE` mudar de novo, este 0.65 fica silenciosamente dessincronizado (o comentário
inclusive já registra que o valor da spec ficou obsoleto). Aceitável para esta task; candidato a
derivar o valor de uma fonte única no futuro. Não bloqueia.

### [OK] Sinal da semente de food-taxis está CORRETO
Verifiquei a cadeia de sinais independentemente:
- `rtneat_wrapper.py:107`: peso `visão[i]→Motor_Torque = FOOD_TAXIS_STEER_GAIN*(i-4)`; input node key
  `-(i+1)`, Motor_Torque = node 1. Correto conforme contrato.
- `sensors.py:57-64`: `relative_angle = arctan2 - body.angle` (normalizado); `shifted = rel + half_fov`;
  `index = shifted // sector_width`. Objeto à esquerda/CCW (`relative_angle > 0`) → índice maior → `i>4`.
- `creature.py:205`: `body.torque = motor_torque * MOTOR_TORQUE_SCALE` (escala=20, positiva). Em Pymunk
  torque positivo = CCW = `body.angle` cresce.
- Encadeando: objeto em `i>4` (à esquerda) → peso positivo → Motor_Torque positivo → torque positivo →
  gira CCW → vira em direção ao objeto. Setor central `i=4` → peso 0 → segue reto. Sinais e índices
  consistentes. Os testes de ±40° (grupos 2) validam corretamente essa direção.

### [OK] Neutralização em compute_vision está correta
`sensors.py:79-92`: `observer_ready_to_mate = is_adult AND energy_fraction >= 0.65 AND cooldown <= 0`.
Adulto pronto → `creature_sign = +1.0` (positivo/atrativo); adulto não-pronto e não-adulto seguem o
comportamento antigo (negativo via `-1.0*mate_signal`, ou 0 se não-adulto pois `mate_signal=0`). Comida
mantém precedência (`if food_present[i]` antes de `elif creature_present[i]`), confirmado também por
`test_food_and_creature_same_sector_food_wins`. Os testes `test_ready_adult_perceives_partner_as_attractive`
e `test_not_ready_adult_still_perceives_creature_as_negative` cobrem os dois lados e importam a constante.

### [OK] Contrato de I/O do NEAT intacto
16 inputs / 4 outputs inalterados (docstring rtneat_wrapper.py:10-27). As sementes só reescrevem
valores iniciais de pesos/bias em conexões/nós já existentes (`if conn_key in genome.connections`,
`if ACTION_MATE_NODE_KEY in genome.nodes`); nenhuma topologia adicionada/removida. `import main` OK e
todos os testes de estrutura/think passam.

### [OK] Semente é evolutível, não global
`test_clone_preserves_parent_weights_without_reseeding` sabota os pesos do pai (42.0 / bias -10.0) e
confirma que `clone_genome` preserva-os — logo a semente só se aplica em `create_zero_genome`. Teste
sólido e não-tautológico.

### [OK] Falha de test_exploration_pressure é pré-existente e fora de escopo — CONFIRMADO com evidência
- `git ls-files backend/tests/test_exploration_pressure.py` → vazio: o arquivo é **untracked**, nunca
  foi commitado; já existia antes de BIT-21 (aparece no git status inicial).
- `git diff --stat` de BIT-21 toca **apenas** `rtneat_wrapper.py` e `sensors.py` (+ os 2 arquivos de
  teste). BIT-21 **não tocou** `engine.py` nem `creature.py`.
- O invariante quebrado (`MIN_ENERGY_TO_MATE > STARTING_ENERGY`) depende só de `engine.py:26` (65.0) e
  `creature.py:19` (75.0) — ambos território de BIT-20. O próprio comentário em engine.py:29 ("85 >
  STARTING_ENERGY") contradiz o valor 65.0 na linha 26: é uma inconsistência pré-existente do retuning
  de BIT-20, sem relação com as edições de BIT-21.
- Conclusão: FORA DE ESCOPO. Não deve bloquear o fechamento de BIT-21.

### [OK] Testes importam constantes em vez de hardcodar
Ambos os arquivos de teste importam `FOOD_TAXIS_STEER_GAIN`, `MOTOR_TORQUE_NODE_KEY`,
`ACTION_MATE_SEED_BIAS_MIN/MAX`, `MATE_ATTRACTION_ENERGY_FRACTION` das fontes reais. Nenhum valor
mágico duplicado. Convenção do projeto respeitada.

## Resumo
A implementação está correta no essencial: sinais de food-taxis, neutralização de repulsão e contrato
de I/O do NEAT verificados independentemente e corretos; a divergência 0.85→0.65 é justificada; e a
única falha de suíte é comprovadamente pré-existente (arquivo untracked, engine.py/creature.py não
tocados). **Pode fechar a task.** A única ressalva relevante é a **flakiness de 2 testes de
comportamento** (`test_sated_adult_wants_to_mate_with_nothing_in_sight`, `test_ready_adult_turns_toward_partner`),
que afirmam um comportamento probabilístico de forma determinística sobre 1 genoma sem seed (~10-15%
de falha ao rodar isolados). Recomendo o orquestrador decidir se estabiliza esses testes agora
(seed ou asserção estatística) antes de mergear no CI — não é um erro de corretude do código de
produção, e sim de robustez dos testes.
