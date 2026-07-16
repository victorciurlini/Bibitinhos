# Evidência — BIT-21: Ímpeto de Busca de Comida e Acasalamento

**Data de conclusão:** 2026-07-15
**Branch:** `BIT-20` (workspace atual; ver [[bibitinhos-git-workflow]] para o merge)

## Demanda atendida

Semear reflexos inatos evolutíveis na Gen-0 para garantir, desde o início, o **ímpeto direcionado**:
(a) virar em direção à comida enxergada (food-taxis) e (b) querer acasalar quando adulto e saciado,
neutralizando a repulsão entre parceiros. A **busca de comida foi entregue e validada**; o **ímpeto de
acasalar está no lugar e correto**, mas a reprodução sexuada só se concretiza após um ajuste de
balanceamento fora do escopo desta task (ver "Achado funcional" abaixo → BIT-22).

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/rtneat_wrapper.py` | modificado | Em `create_zero_genome()`: semente de food-taxis (9 pesos `visão[i]→Motor_Torque = FOOD_TAXIS_STEER_GAIN*(i-4)`) e semente de bias de `Action_Mate` em `U(1.5, 2.5)`. Constantes novas + docstring. Contrato de I/O do NEAT (16/4) intacto. |
| `backend/simulation/sensors.py` | modificado | `MATE_ATTRACTION_ENERGY_FRACTION = 0.65` + neutralização condicional em `compute_vision()`: observador adulto pronto percebe criaturas como sinal positivo (atrativo). |
| `backend/tests/test_sensors.py` | modificado | Teste do sinal de criatura atualizado (adulto pronto → +) + caso do adulto não pronto (segue −). |
| `backend/tests/test_food_and_mate_seeking.py` | criado | 5 grupos de teste (semente food-taxis, esterço, bias de mate, neutralização, semente-não-global). Os 2 testes de comportamento probabilístico usam asserção estatística determinística (`random.seed(42)`, N=200, fração ≥ 0.85). |

## Divergências em relação à spec

1. **`MATE_ATTRACTION_ENERGY_FRACTION = 0.65`** (spec dizia 0.85). A constante espelha o
   `MIN_ENERGY_TO_MATE` do `engine.py`, que foi retunado de 85→65 entre o refino e a implementação;
   0.65 preserva a intenção declarada ("espelhar o limiar de acasalamento").
2. **Testes de comportamento viraram estatísticos.** A semente é probabilística (~93–99%, medido); os
   testes originais afirmavam determinismo sobre 1 genoma → flaky (~10–15%). Convertidos para asserção
   estatística determinística (achado do revisor, corrigido no ciclo implementer→revisor).

## Resultados dos gates de qualidade

- `import main`: **OK**
- `pytest tests/`: **115 passed / 1 failed**. A única falha é **pré-existente e de outra task**
  (`test_exploration_pressure.py::test_newborn_still_has_to_eat_before_mating`, invariante
  `MIN_ENERGY_TO_MATE > STARTING_ENERGY` quebrado pelo retuning 85→65 do BIT-20; arquivo untracked,
  não tocado por BIT-21). Confirmado independentemente pelo revisor (BIT-21 só alterou
  `rtneat_wrapper.py`/`sensors.py` + 2 testes).
- Ciclo de revisão: implementer → revisor (APROVADO COM RESSALVAS: 2 testes flaky) → implementer
  (correção) → revisor (**APROVADO**, sem achados restantes).
- `npm run test` / `npm run build`: **N/A** (frontend não tocado).

## Validação funcional (headless, engine real)

**Busca de comida — ENTREGUE.** Esterço em direção à comida visível fora do centro: **70–86%** dos
casos (4 seeds × 4 min), contra o baseline de **47,5%** (puro acaso, medido no refino). A semente de
food-taxis funciona no ecossistema vivo, não só no teste unitário.

**Acasalamento — ímpeto correto, mas reprodução sexuada ainda 0% (gargalo de energia).** Funil de
encontro (3 seeds × 3 min):

| Etapa | Ocorrências |
|---|---|
| Colisões entre criaturas | 2942 |
| Ambas ADULT | 878 |
| ...ambas querem acasalar (`action_mate`) | **878 (100%)** |
| ...ambas fora de cooldown | 607 |
| ...ambas com energia ≥ 65 | **0** |
| ...todos os gates juntos | **0** |

A semente de `Action_Mate` é 100% eficaz (todo adulto que colide quer acasalar) e os adultos colidem
bastante — o bloqueio é o **gate de energia**: com a economia do BIT-20, dois adultos ambos ≥65 no
mesmo instante de colisão nunca coexistem. Aumentar `VISION_RADIUS` (80→400) **não** destrava
(sexuada = 0 em todos os valores) — confirma que a raiz é energia/economia, não encontro. Isso está
entrelaçado com o teste pré-existente que falha (subir `MIN_ENERGY_TO_MATE` pioraria).
**Encaminhado para BIT-22 (refiner).**

## Como validar

1. `manager.py` → Start Tudo → abrir `http://localhost:5173`.
2. Observar, desde os primeiros segundos: criaturas **desviam a trajetória para comer** ao enxergar
   comida no campo de visão (não passam mais reto ignorando).
3. `pytest backend/tests/test_food_and_mate_seeking.py -v` → 21 verdes.
4. Reprodução: por ora ocorre por **clonagem assexuada**; a via sexuada depende do BIT-22.
