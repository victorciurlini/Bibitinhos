# Evidência — BIT-22: Reprodução Sexuada Emergente

**Data de conclusão:** 2026-07-15
**Branch:** `BIT-22` (criada a partir do tip de `BIT-20`, que contém BIT-20+BIT-21; ver [[bibitinhos-git-workflow]])

## Demanda atendida

A reprodução sexuada — que estava em **0%** desde sempre — passou a **emergir de forma recorrente**
(~2 nascimentos sexuados por run de 5 min, contra 0), redesenhando o ecossistema para dar densidade e
prosperidade, com acasalamento por proximidade e fertilidade persistente. Resolve também o teste
pré-existente que falhava (`test_newborn_still_has_to_eat_before_mating`).

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/physics.py` | modificado | Mapa 2000→**1400×1400** (lever decisivo de densidade) |
| `backend/simulation/creature.py` | modificado | `FERTILITY_ENERGY_THRESHOLD=60.0`; atributos `has_eaten`/`is_fertile`; `sought_mate_this_frame` (no lugar de `collided_with_creature_this_frame`); promoção de fertilidade persistente em `update()` |
| `backend/simulation/engine.py` | modificado | Reprodução sexuada por **proximidade** (`MATING_RADIUS`) no `step()`; handler de colisão criatura×criatura e `MIN_ENERGY_TO_MATE` **removidos**; `has_eaten` no handler de comida; assexuada suprimida via `sought_mate_this_frame`; `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` 90→100, `ASEXUAL_REPRODUCTION_ENERGY_COST` 85→95 |
| `backend/simulation/oasis.py` | modificado | Comida mais farta: `MAX_ACTIVE_OASES=6`, `OASIS_FOOD_SPAWN_CHANCE=0.18`, `OASIS_FOOD_CAP=18`, `MAX_TOTAL_FOOD=110` |
| `backend/simulation/food.py` | modificado | `energy_value` default → 32.0 |
| `backend/simulation/sensors.py` | modificado | Só remoção de comentário obsoleto (lógica intacta) |
| `backend/tests/test_reproduction.py`, `test_exploration_pressure.py`, `test_asexual_reproduction.py`, `test_feeding.py` | modificados | Adaptados à nova mecânica (proximidade+fertilidade; novo invariante `has_eaten`; posições no mapa 1400) |
| `backend/tests/test_sexual_reproduction.py` | criado | 6 grupos: `has_eaten` gate, fertilidade persistente, proximidade (dentro/fora do raio), ambos precisam querer, supressão da assexuada, piso de sobrevivência |

## Divergências em relação à spec (todas validadas pelo revisor)

1. **`MATING_RADIUS` 120→150** — degrau 1 da escada de calibração da spec (passo 9). Com 120 a sexuada
   ficava ~1/run e zerava num seed; 150 tornou recorrente sem tocar mapa/comida/supressão.
2. **`food.py energy_value` alvo 32.0** — a nota da spec ("era 25.0") estava errada; o valor real era
   40.0 (BIT-20). Aplicado o alvo calibrado 32.0.
3. **`test_asexual_reproduction.py`** — não estava na lista da spec, mas dependia do handler removido;
   adaptado sem enfraquecer (ainda pega regressão da supressão).

## Resultados dos gates de qualidade

- `import main`: **OK**; `get_state().width/height == 1400`: **OK**
- `pytest tests/`: **127 passed** (6 warnings = DeprecationWarning pré-existente do neat-python)
- Ciclo de revisão: implementer → revisor (**APROVADO**, sem bloqueantes nem melhorias relevantes)
- `npm run test` / `npm run build`: **N/A** (frontend não tocado — auto-escala por `data.width/height`)

## Validação funcional (headless, engine real — reproduzida independentemente pelo revisor)

| seed | sexual | assexual | pop_min | pop_max | pop_end |
|---|---|---|---|---|---|
| 1 | 1 | 2 | 1 | 12 | 10 |
| 2 | 2 | 3 | 1 | 14 | 3 |
| 3 | 2 | 8 | 1 | 13 | 5 |

Reprodução **sexuada > 0 e recorrente** em todos os seeds (era 0); sem extinção (pop_min ≥ 1); sem
boom-bust. A assexuada continua como válvula (mais frequente, ~1:3), o que é aceitável — a demanda era
fazer a sexuada emergir, não dominar.

## Como validar

1. `manager.py` → Start Tudo → `http://localhost:5173`.
2. Observar o mundo **menor (1400)** renderizando corretamente (auto-escala).
3. Ao longo de alguns minutos, observar **novos EGGs surgindo entre pares de adultos que se aproximam**
   (reprodução sexuada), não só por clonagem solitária.
4. `pytest backend/tests/test_sexual_reproduction.py -v` → verde.
