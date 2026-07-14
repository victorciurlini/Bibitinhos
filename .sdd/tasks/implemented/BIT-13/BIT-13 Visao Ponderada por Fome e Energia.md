# Spec — BIT-13: Visão Ponderada por Fome e Energia

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação)

---

## Demanda

Os bibites hoje não têm nenhum incentivo perceptível para buscar comida — em parte porque ficar parado gasta menos energia (trade-off que o developer já entende e aceita), em parte porque o sensor de visão não distingue tipo de vizinho, então a rede neural não tem como priorizar "ir atrás de comida" de "ir atrás de outro bibite para reproduzir". A decisão tomada com o developer: em vez de um reward artificial de fitness (o projeto documenta seleção **puramente natural, sem pontuação artificial** — ver README seção 6.2), os cones de visão passam a carregar um sinal de **prioridade instintiva**, dependente do estado interno da própria criatura — um bibite com fome enxerga comida com mais intensidade; um bibite adulto e energético enxerga outras criaturas (parceiros em potencial) com mais intensidade. A rede evoluída continua livre para decidir como reagir a cada sinal; a mudança está em *o que* ela percebe, não em pontuá-la por agir de um jeito ou de outro.

## Abordagem técnica

Cada um dos 9 cones passa de um valor binário (0.0/1.0, sem tipo) para um valor com sinal em `[-1.0, 1.0]`: positivo quando há comida no cone (magnitude = fome, `1 - energy/max_energy`), negativo quando há outra criatura (magnitude = `energy/max_energy`, só diferente de zero se a própria criatura for `ADULT`), zero quando vazio. A distinção de tipo usa `shape.collision_type` (`COLLISION_CATEGORY_FOOD`/`COLLISION_CATEGORY_CREATURE`, já setados em `Food`/`Creature` desde suas respectivas criações) — sem precisar importar as classes `Food`/`Creature` em `sensors.py` e sem risco de import circular (validado ao vivo). Isso também corrige de graça um bug latente: hoje `compute_vision()` não filtra as paredes do mapa, que caem no `bb_query()` perto das bordas; com a checagem de `collision_type`, paredes (que nunca setam esse atributo, ficando no default `0` do pymunk) são automaticamente ignoradas. `num_inputs` continua `16` em `neat_config.ini` — nenhuma mudança na topologia da rede, só na semântica dos 9 primeiros inputs (mudança documentada na docstring de `rtneat_wrapper.py`).

**Precedência quando comida e criatura caem no mesmo setor:** comida vence (mostra o sinal positivo de fome) — comida é a necessidade mais imediata/vital, e sempre que possível a criatura já teria colidido com ela primeiro fisicamente de qualquer forma.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/sensors.py` | modificar | `compute_vision()` retorna sinal com tipo+prioridade em vez de binário |
| `backend/simulation/rtneat_wrapper.py` | modificar | Atualizar docstring do contrato de I/O (`Visual_Sectors`) |
| `backend/tests/test_sensors.py` | modificar | Atualizar asserções para a nova semântica |

## Passos de implementação

1. **`sensors.py`** — reescrever `compute_vision()`:
   ```python
   import math

   import numpy as np
   import pymunk

   from simulation.creature import LifeStage
   from simulation.physics import COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD

   VISION_RADIUS = 200.0
   NUM_VISION_SECTORS = 9


   def compute_vision(creature, engine):
       """Retorna 9 cones com sinal ao redor da criatura.

       Cada cone e positivo (comida, magnitude = fome), negativo (outra
       criatura, magnitude = energia normalizada, so se a propria criatura
       for ADULT) ou zero (vazio). Usa shape.collision_type para distinguir
       tipo sem precisar importar Food (evita ciclo de import); paredes nao
       setam collision_type e sao ignoradas automaticamente. Comida tem
       precedencia sobre criatura quando ambas caem no mesmo setor.
       """
       food_present = [False] * NUM_VISION_SECTORS
       creature_present = [False] * NUM_VISION_SECTORS

       space = engine.physics.space
       cx, cy = creature.body.position
       bb = pymunk.BB(cx - VISION_RADIUS, cy - VISION_RADIUS, cx + VISION_RADIUS, cy + VISION_RADIUS)
       shapes = space.bb_query(bb, pymunk.ShapeFilter())

       sector_width = 2 * np.pi / NUM_VISION_SECTORS

       for shape in shapes:
           if shape is creature.shape:
               continue
           if shape.collision_type not in (COLLISION_CATEGORY_FOOD, COLLISION_CATEGORY_CREATURE):
               continue  # paredes e qualquer shape sem tipo definido

           nx, ny = shape.body.position
           dx, dy = nx - cx, ny - cy
           distance = math.hypot(dx, dy)
           if distance == 0 or distance > VISION_RADIUS:
               continue

           absolute_angle = np.arctan2(dy, dx)
           relative_angle = absolute_angle - creature.body.angle
           relative_angle = (relative_angle + np.pi) % (2 * np.pi) - np.pi
           shifted = (relative_angle + sector_width / 2) % (2 * np.pi)
           index = int(shifted // sector_width) % NUM_VISION_SECTORS

           if shape.collision_type == COLLISION_CATEGORY_FOOD:
               food_present[index] = True
           else:
               creature_present[index] = True

       hunger = 1.0 - min(creature.energy / creature.max_energy, 1.0)
       mate_drive = (creature.energy / creature.max_energy) if creature.life_stage == LifeStage.ADULT else 0.0

       vision = [0.0] * NUM_VISION_SECTORS
       for i in range(NUM_VISION_SECTORS):
           if food_present[i]:
               vision[i] = hunger
           elif creature_present[i]:
               vision[i] = -mate_drive
       return vision
   ```
   Import de `LifeStage`/`COLLISION_CATEGORY_*` em `sensors.py` não cria ciclo: `creature.py` e `physics.py` não importam `sensors.py` (validado ao vivo no venv real do projeto).

2. **`rtneat_wrapper.py`** — atualizar só a linha do contrato referente a `Visual_Sectors`:
   ```
   0-8   Visual_Sectors   (9 cones; sinal em [-1,1]: positivo=comida (mag=fome),
                           negativo=outra criatura (mag=energia, so se ADULT), 0=vazio)
   ```
   `num_inputs`/`num_outputs` continuam inalterados — não tocar `neat_config.ini`.

3. **`test_sensors.py`** — atualizar para a nova semântica (energia precisa ser setada explicitamente, já que o valor esperado agora depende dela):
   - `test_no_neighbors_returns_all_zero`: inalterado (vazio continua `0.0` independente de energia).
   - `test_food_directly_ahead_activates_cone_zero`: setar `creature.energy = 0.0` antes de chamar `compute_vision` (fome = 1.0) → `vision[0] == pytest.approx(1.0)`, resto `0.0`. Adicionar teste irmão com `creature.energy = 100.0` (fome = 0.0) confirmando `vision[0] == 0.0` (comida presente mas sem fome não gera sinal — documentar esse comportamento no teste).
   - `test_creature_directly_behind_activates_opposite_cone`: setar `creature.life_stage = LifeStage.ADULT` e `creature.energy = 100.0` (mate_drive = 1.0) → sinal `-1.0` no cone oposto, não mais `1.0`. Adicionar variante com `life_stage != ADULT` confirmando sinal `0.0` (criatura presente, mas sem "interesse" — vazio do ponto de vista da rede).
   - `test_neighbor_outside_radius_does_not_activate_any_cone`, `test_creature_never_detects_itself`: inalterados na estrutura, só confirmam `[0.0] * 9`.
   - `test_engine_step_only_recomputes_vision_at_brain_tick_rate`: inalterado (não depende da semântica do valor, só da contagem de chamadas).
   - Novo teste: comida e criatura no mesmo setor → comida vence (`vision[i]` reflete fome, não `-mate_drive`).
   - Novo teste: parede próxima da borda do mapa não ativa nenhum cone (regressão do bug latente corrigido).

4. Rodar a suíte completa (`backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`) e confirmar 100% verde. `test_creature_think.py`/`test_locomotion.py`/outros que dependem indiretamente de `compute_vision` via `engine.step()` devem continuar passando sem alteração (não fazem asserção sobre valores específicos de `vision`).

## Contratos técnicos

### Backend (Simulação)
- `compute_vision(creature, engine) -> list[float]` — mesma assinatura, mesmo tamanho de retorno (9), semântica muda de binário para sinal ponderado `[-1.0, 1.0]`.
- Nenhuma mudança em `neat_config.ini` (`num_inputs` continua `16`).
- Docstring de `rtneat_wrapper.py` atualizada para refletir a nova semântica de `Visual_Sectors` (única mudança de contrato documentado; a forma — 9 valores float — não muda).

## Critérios de aceite

- [ ] Comida em um cone gera sinal positivo, com magnitude igual a `1 - energy/max_energy` da criatura observadora.
- [ ] Criatura em um cone gera sinal negativo, com magnitude igual a `energy/max_energy`, e apenas se a criatura observadora for `ADULT` (senão `0.0`).
- [ ] Criatura saciada (`energy == max_energy`) não gera sinal de comida (`0.0`) mesmo com comida visível — comportamento documentado, não é regressão.
- [ ] Comida e criatura no mesmo setor: comida tem precedência.
- [ ] Paredes do mapa nunca ativam nenhum cone (bug latente corrigido).
- [ ] `num_inputs` em `neat_config.ini` permanece `16` — nenhuma mudança de topologia do NEAT.
- [ ] `pytest backend/tests/test_sensors.py` 100% verde com os novos casos.
- [ ] Nenhuma regressão: suíte completa (`pytest backend/tests/`) 100% verde.

## Rollback

Reverter `sensors.py` para a versão binária (0.0/1.0, sem checagem de `collision_type`); reverter a docstring de `Visual_Sectors` em `rtneat_wrapper.py`; reverter `test_sensors.py` para as asserções binárias originais.
