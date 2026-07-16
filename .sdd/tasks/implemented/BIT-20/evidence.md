# Evidência — BIT-20: Pressão Evolutiva para Exploração

**Data de conclusão:** 2026-07-14
**Branch:** `BIT-20`

## Demanda atendida

A economia de energia foi invertida: explorar o mapa deixou de ser a estratégia mais cara e passou a ser
a mais barata, e girar parado — o comportamento que o developer reclamou — passou a ser a **pior**
estratégia de sobrevivência disponível. Somam-se a isso o seed genético que faz 100% da Geração 0 nascer
capaz de andar, o destravamento da reprodução sexuada e o fim do subsídio de comida a quem fica parado.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | Nova economia: `MOVEMENT_REFERENCE_SPEED`, `IDLE_PENALTY_RATE`, `MOTOR_FORWARD_COST`, `SPIN_COST`. `update()` cobra imposto de ociosidade pela velocidade real do corpo. `EGG` isento. |
| `backend/simulation/rtneat_wrapper.py` | modificado | `create_zero_genome()` enviesa o bias do node `Motor_Forward` (key 0) em `U(0.3, 1.0)` |
| `backend/simulation/engine.py` | modificado | `MIN_ENERGY_TO_MATE` 100→85, `REPRODUCTION_ENERGY_COST` 50→40, `ASEXUAL_REPRODUCTION_ENERGY_COST` 70→85, `ASEXUAL_REPRODUCTION_COOLDOWN` 20→45. Oásis do Éden nasce longe do sobrevivente. |
| `backend/simulation/oasis.py` | modificado | `EDEN_OASIS_MIN_DISTANCE = 250.0`, `EDEN_OASIS_MAX_DISTANCE = 400.0` |
| `backend/simulation/food.py` | modificado | `energy_value` 20.0 → 25.0 |
| `backend/tests/test_exploration_pressure.py` | criado | 15 testes: economia, imposto de ociosidade, seed genético, reprodução, Éden |
| `backend/tests/test_metabolism.py` | modificado | Metabolismo isolado do imposto + novo teste do imposto por estágio |
| `backend/tests/test_creature_think.py` | modificado | Custo esperado passa a incluir o imposto de ociosidade |
| `backend/tests/test_reproduction.py` | modificado | Idem (criaturas paradas no frame do acasalamento) |
| `backend/tests/test_asexual_reproduction.py` | modificado | Idem |

## Resultados dos gates de qualidade

- `import main`: **OK**
- `pytest tests/`: **107 passed**
- Smoke do loop real do FastAPI (5s): **OK**, sem exceções, payload do WebSocket inalterado
- `npm run test` / `npm run build`: **N/A** (frontend não foi tocado)

## Validação funcional (headless, 5 seeds × 5 min simulados, comparada com o baseline)

| Métrica | Baseline (antes) | BIT-20 |
|---|---|---|
| **Parado girando** (o comportamento reclamado) | **66,2%** | **20,1%** |
| Velocidade média | 8,9 px/s | **30,6 px/s** |
| Amostras em movimento | 20,8% | **71,0%** |
| Idade máxima atingida | 57s | **77s** |
| Extinções totais (5 min) | 5,0 | **2,8** |
| Nascimentos | **0** | **16,8** |
| População final | 4,0 | **8,4** |

O comportamento reclamado era o **dominante** no baseline (66,2% das amostras), o que confirma
quantitativamente o relato do developer. Caiu para 20,1% — e o resíduo é majoritariamente criatura
desacelerando ou presa em parede, não a patologia de girar indefinidamente.

## Divergências em relação à spec

### 1. `IDLE_PENALTY_RATE` calibrado de 2.0 para 1.2 (degrau 1 da escada de ajuste prevista na spec)

Com 2.0 a população colapsava (13 extinções / 5 min). A 1.2 o ecossistema se sustenta (2,8 extinções,
contra 5,0 do código antigo) e girar parado **continua sendo a pior estratégia**, que é o objetivo.
Ajuste explicitamente autorizado pela seção *Rollback* da spec.

### 2. Bug corrigido durante a implementação: velocidade medida antes do impulso

A spec calculava `movement_factor` **depois** de `apply_impulse_at_local_point()`. Como o Pymunk aplica
o impulso na velocidade imediatamente, uma criatura travada contra a parede com thrust cheio aparentava
~1,7 px/s e escapava de parte do imposto — justamente o furo que o imposto existe para fechar. A medição
foi movida para **antes** do impulso (usa o deslocamento de fato alcançado no passo de física anterior).
Pego por `test_idle_penalty_is_not_gameable_by_motor_output`.

## Achado fora do escopo (requer decisão do developer)

**A reprodução sexuada continua em zero — e isso não é causado pelos limiares de energia.**

Medido: com o limiar em 85 as criaturas *alcançam* energia suficiente (há 16,8 nascimentos assexuados,
que exigem energia 100 — ou seja, o teto é atingível). O que não acontece é o **encontro**: com
`VISION_RADIUS = 80px`, ~8 criaturas e um mapa de 2000×2000 (4 milhões de px²), duas criaturas
praticamente nunca se cruzam. A reprodução sexuada está bloqueada por **probabilidade de encontro**,
não por energia.

Isso é anterior ao BIT-20 (o baseline também tem 0 nascimentos sexuados) e não é resolvível dentro do
escopo desta spec. Sugestão de próxima task: aumentar `VISION_RADIUS`, reduzir o mapa, ou elevar a
densidade populacional — qualquer uma ataca a probabilidade de encontro.

## Como validar

1. `manager.py` → Start Tudo → abrir o frontend em `http://localhost:5173`
2. Observar, desde os primeiros segundos: **as criaturas se deslocam pelo mapa** em vez de ficarem
   paradas girando no lugar (era ~2/3 do tempo antes, agora ~1/5).
3. Observar que surgem novos EGGs (antes, em 5 min simulados, nasciam zero).
4. Observar que o oásis do Jardim do Éden **não** nasce mais em cima do sobrevivente.
5. `manager.py` → Logs → confirmar `backend.log` sem tracebacks.
