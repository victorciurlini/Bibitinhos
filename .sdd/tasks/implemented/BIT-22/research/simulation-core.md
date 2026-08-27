# Research — BIT-22: Reprodução Sexuada Emergente (camada Simulação)

## Arquivos relevantes
- `backend/simulation/engine.py` — constantes de reprodução (linhas 23-34), handler de colisão
  criatura×criatura (55-93, reprodução sexuada), laço de reprodução assexuada (129-160), spawn de
  comida/oásis no `step`.
- `backend/simulation/creature.py` — `STARTING_ENERGY=75`, energia/metabolismo, `is_alive`, estágios.
- `backend/simulation/food.py` — `Food.energy_value` (default 25 após BIT-20).
- `backend/simulation/oasis.py` — `MAX_TOTAL_FOOD=50`, `OASIS_FOOD_SPAWN_CHANCE=0.08`,
  `OASIS_FOOD_CAP=8`, `MAX_ACTIVE_OASES=4`, constantes do Éden.
- `backend/tests/test_exploration_pressure.py::test_newborn_still_has_to_eat_before_mating` — teste
  que FALHA hoje (`assert MIN_ENERGY_TO_MATE > STARTING_ENERGY`, 65 > 75 falso).

## Constantes de reprodução atuais (engine.py)
- `REPRODUCTION_ENERGY_COST = 30.0`, `REPRODUCTION_COOLDOWN = 10.0`
- `MIN_ENERGY_TO_MATE = 65.0` (comentário na linha 29 está DESATUALIZADO: diz "85 > STARTING_ENERGY",
  mas o valor é 65 < 75 — o retuning 85→65 quebrou o invariante e o comentário).
- `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 90.0`, `ASEXUAL_REPRODUCTION_ENERGY_COST = 85.0`,
  `ASEXUAL_REPRODUCTION_COOLDOWN = 45.0`.

## Diagnóstico (validado empiricamente — ~10 experimentos headless no engine real)

Sintoma: reprodução sexuada = **0%** (todos os nascimentos são clonagem assexuada).

Sequência de experimentos e o que cada um DESCARTOU:

1. **Funil de encontro** (3 seeds × 3 min): 878 frames de colisão entre dois ADULTs; ambos querem
   acasalar em 100% deles; mas "ambos com energia ≥ MIN_ENERGY_TO_MATE (65)" = **0**. O gate de
   energia instantânea é o bloqueio imediato.
2. **VISION_RADIUS 80→400**: sexuada segue 0 em todos os valores → encontro por visão NÃO é a raiz.
3. **Fertilidade persistente** (fica fértil ao atingir limiar alto, mantém até acasalar/piso): 0 sexual.
   Só ~11 criaturas chegam a ficar férteis em 4 min.
4. **Flag `has_eaten` + limiar de energia alcançável** (55-65, desacopla "comeu" do nível): 0 sexual,
   ainda ~11 férteis, **0 frames de colisão com ambos férteis**. O limiar não é o gargalo.
5. **Densidade** (spawn de 40 criaturas num cluster de 150px, mapa 2000): 0 sexual. Funil no denso:
   38962 frames de par adulto próximo, 99% querem acasalar, mas **`both_eaten = 0`** — 40 criaturas
   competindo pela mesma comida escassa quase nunca comem (coastam nos 75 iniciais e morrem). Densidade
   sem comida = fome.
6. **Economia de comida RICA** (`MAX_TOTAL_FOOD=200`, `OASIS_FOOD_SPAWN_CHANCE=0.35`,
   `MAX_ACTIVE_OASES=8`, oásis `food_cap=25`, `energy_value=40`) **+ densidade + fertilidade**:
   **sexuada finalmente > 0** (2 eventos em 20/400; 1 em 30/300, 3 seeds × 4 min). Criaturas férteis
   sobem para 44-81. **Mas ainda raro, e a população fica instável** (boom a maxpop 35, colapso a ~4).

Sanity-check do harness confirmado (cenário forçado → 1 mating contado), então os zeros são reais.

## Raiz
Não é o gate de acasalamento — é **carrying capacity + esparsidade espacial**. O ecossistema padrão
sustenta ~5-8 criaturas, a maioria pobre (adultos passam ~4% do tempo com energia ≥65, ~26% abaixo de
35). Duas adultas bem-nutridas praticamente nunca coexistem no mesmo ponto. Os levers são acoplados:
densidade sem comida = fome; comida sem densidade = esparsidade; só os dois juntos + um gate que tolere
a janela transiente (fertilidade persistente) produzem reprodução sexuada — e ainda assim rara/instável.

## Conflito de design embutido (precisa de decisão do developer)
"Comer antes de acasalar" (intenção do BIT-16) exige limiar > STARTING_ENERGY (75), que quase ninguém
atinge; baixar o limiar para algo alcançável viola a intenção (recém-nascido nasce com 75). **Solução
limpa: flag `has_eaten`** (setada no handler de colisão criatura×comida) desacopla "já comeu" do nível
de energia — o gate do BIT-16 vira `has_eaten`, e a fertilidade usa um limiar de energia alcançável.
Isso também resolve o teste que falha (o invariante passa a ser sobre a flag / um limiar de fertilidade
> STARTING_ENERGY, ou o teste é reescrito para a nova semântica).

## O que precisa ser feito (depende da direção escolhida)
- **Mecânica (baixo risco, necessária mas insuficiente sozinha):** flag `has_eaten` na `Creature`
  (setada ao comer); estado `is_fertile` persistente (ganho ao ser ADULT + `has_eaten` + energia ≥
  limiar alcançável; perdido ao acasalar / abaixo de um piso baixo); gate de acasalamento sexuado passa
  a exigir `is_fertile` em vez de energia instantânea ≥ MIN_ENERGY_TO_MATE. Reescrever/corrigir
  `test_newborn_still_has_to_eat_before_mating`.
- **Ecossistema (médio/alto risco — mexe no balanceamento do BIT-20):** aumentar a oferta de comida
  (algum subconjunto de `MAX_TOTAL_FOOD`, `OASIS_FOOD_SPAWN_CHANCE`, `OASIS_FOOD_CAP`,
  `MAX_ACTIVE_OASES`, `energy_value`) e/ou a densidade (mapa menor / população inicial maior) até a via
  sexuada emergir de forma observável, sem reintroduzir a exploração de ociosidade que o BIT-20 fechou
  nem causar boom-bust populacional.

## Calibração (harness paralelo, 12 núcleos — `scratchpad/sim_harness.py`)

Levers testados isoladamente dão 0 sexual; a combinação que funciona com **spawn realista**
(aleatório, sem cluster artificial), medida em 6 seeds × 6 min:

| Config | sexuada | assexuada | pop min/med/max |
|---|---|---|---|
| mapa 2000 + comida moderada + proximidade 120 + assex suprimida | **0** | 32 | 1/5/12 |
| **mapa 1400** + idem | **14** | 64 | 1/5/15 |
| mapa 1400 + comida um pouco maior + raio 140 | 10 | 63 | 1/5/16 |

**O tamanho do mapa é o lever decisivo para o jogo real**: 2000×2000 é esparso demais; 1400×1400
(≈ metade da área) fornece a densidade para dois adultos férteis se aproximarem. Levers secundários,
todos necessários juntos:
- **Acasalamento por PROXIMIDADE** (raio ~120) no lugar de colisão exata no mesmo frame — aumenta a
  sexuada monotonicamente (raio 22→60→100 ⇒ sex 0→2→5, medido). Preserva o cérebro decidindo
  (ambos precisam `action_mate`).
- **Fertilidade persistente + `has_eaten`**: fica fértil ao ser ADULT + já ter comido + energia ≥ 60
  (alcançável); mantém até acasalar. `has_eaten` preserva "comer antes de acasalar" ortogonal à energia.
- **Comida moderada**: `MAX_TOTAL_FOOD` 50→110, `OASIS_FOOD_SPAWN_CHANCE` 0.08→0.18,
  `MAX_ACTIVE_OASES` 4→6, `OASIS_FOOD_CAP` 8→18, `Food.energy_value` 25→32.
- **Assexuada suprimida** (senão abafa a sexuada e causa boom-bust): `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`
  90→100, `ASEXUAL_REPRODUCTION_ENERGY_COST` 85→95.

Frontend: lê `data.width/height` dinamicamente e auto-escala (`SimulationCanvas.jsx:94-96`) — reduzir o
mapa renderiza correto **sem tocar no frontend**. BIT-22 é backend-only.

## Perguntas em aberto
- **Ambição/risco** (decisão do developer): mecânica-só + boost moderado de comida (preserva BIT-20) vs.
  redesenho de ecossistema (mapa/densidade/comida) para reprodução sexuada dominante. Ver spec.
- Valores finais das constantes de comida/densidade dependem da direção e precisam de uma escada de
  calibração headless (como no BIT-20), medindo sexual vs. assexual, estabilidade populacional e
  regressão do anti-ociosidade.
