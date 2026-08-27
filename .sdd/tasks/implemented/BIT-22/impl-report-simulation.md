# Impl Report — BIT-22: Reprodução Sexuada Emergente

## Status
CONCLUÍDO

## Passos executados
1. **`physics.py`** — `map_width`/`map_height` 2000 → 1400.
2. **`creature.py`** — constante de módulo `FERTILITY_ENERGY_THRESHOLD = 60.0`; atributos
   `has_eaten` e `is_fertile` no `__init__`; troca de `collided_with_creature_this_frame` por
   `sought_mate_this_frame`; promoção de fertilidade persistente no fim de `update()` (seta
   `is_fertile=True` quando ADULT + `has_eaten` + `energy >= FERTILITY_ENERGY_THRESHOLD`; nunca zera lá).
3. **`engine.py`** — `has_eaten=True` no handler de comida; REMOVIDO o handler
   `_on_creature_creature_collision` e seu registro `on_collision`; NOVO bloco de reprodução sexuada
   por PROXIMIDADE (`MATING_RADIUS`) no `step()`, antes do laço da assexuada; reset de
   `sought_mate_this_frame` movido para o início do scan sexual; gate da assexuada trocado de
   `collided_with_creature_this_frame` para `sought_mate_this_frame`; removida a constante
   `MIN_ENERGY_TO_MATE`; `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` 90→100 e
   `ASEXUAL_REPRODUCTION_ENERGY_COST` 85→95; nova constante `MATING_RADIUS`.
4. **`oasis.py`** — `MAX_ACTIVE_OASES=6`, `OASIS_FOOD_SPAWN_CHANCE=0.18`, `OASIS_FOOD_CAP=18`,
   `MAX_TOTAL_FOOD=110`.
5. **`food.py`** — `energy_value` default 40.0 → 32.0.
6. **`sensors.py`** — apenas o comentário obsoleto que citava `MIN_ENERGY_TO_MATE` foi atualizado
   (a lógica e `MATE_ATTRACTION_ENERGY_FRACTION` ficaram intactas; nenhum import de constante removida).
7. **Testes** — `test_reproduction.py` reescrito para a mecânica proximidade+fertilidade;
   `test_exploration_pressure.py` teve imports e os 3 testes que citavam `MIN_ENERGY_TO_MATE`
   reescritos (incluindo o `test_newborn_still_has_to_eat_before_mating` agora sobre o invariante
   `has_eaten`); `test_asexual_reproduction.py` adaptado (proximidade+fertilidade no lugar de colisão);
   `test_sexual_reproduction.py` criado com os 6 grupos da spec; `test_feeding.py` teve uma posição
   fora do novo mapa realocada (1900→1300) e o comentário atualizado.
8. **Calibração (passo 9)** — validação headless do engine real; `MATING_RADIUS` subiu de 120 para 150
   (degrau 1 da escada) porque 120 dava média ~1/run com um seed em 0.

## Arquivos modificados
- `backend/simulation/physics.py` — mapa 1400×1400.
- `backend/simulation/creature.py` — `FERTILITY_ENERGY_THRESHOLD`, `has_eaten`, `is_fertile`,
  `sought_mate_this_frame`, promoção de fertilidade em `update()`.
- `backend/simulation/engine.py` — reprodução sexuada por proximidade; remoção do handler de colisão
  criatura×criatura e de `MIN_ENERGY_TO_MATE`; supressão da assexuada via `sought_mate_this_frame`;
  `MATING_RADIUS=150`, custos/limiares da assexuada retunados.
- `backend/simulation/oasis.py` — comida mais farta (oases/cap/spawn/total).
- `backend/simulation/food.py` — `energy_value=32.0`.
- `backend/simulation/sensors.py` — atualização de comentário obsoleto (sem mudança de lógica).
- `backend/tests/test_reproduction.py` — mecânica de proximidade+fertilidade.
- `backend/tests/test_exploration_pressure.py` — imports e 3 testes; invariante `has_eaten`.
- `backend/tests/test_asexual_reproduction.py` — proximidade+fertilidade nos testes de supressão/prioridade.
- `backend/tests/test_sexual_reproduction.py` — NOVO, 6 grupos da spec.
- `backend/tests/test_feeding.py` — posição de comida realocada para dentro do mapa 1400.

## Problemas encontrados / decisões
- **`food.py` divergia da spec**: a tabela da spec dizia "era 25.0", mas o valor real no arquivo era
  40.0 (BIT-20 havia subido de 20→40). O alvo calibrado da spec é `32.0`, então apliquei 32.0
  (a fonte da verdade é o valor final, não a nota "era 25.0"). Comentário do código reflete o real (era 40.0).
- **`test_asexual_reproduction.py` não estava na lista "Arquivos a tocar"** mas dependia do handler de
  colisão removido (`collided_with_creature_this_frame`, `_make_colliding_adult_pair`). Adaptei seus
  dois testes de supressão/prioridade para a mecânica nova (proximidade+fertilidade) preservando a
  intenção original. Sem isso a suíte não fecharia — decisão dentro do escopo (a mecânica que esses
  testes exercitam foi substituída por esta task).
- **`is_fertile` é re-promovida no mesmo `step()`**: o scan sexual zera `is_fertile`, mas o `update()`
  seguinte re-promove se a criatura ainda tem `has_eaten` e energia ≥ limiar (comportamento correto). Nos
  testes que verificam "zerou is_fertile", desliguei `has_eaten` nas cobaias para observar o efeito direto
  do acasalamento; a re-promoção natural é coberta pelos testes de fertilidade dedicados.
- **Testes negativos de sexual precisavam isolar da assexuada**: um adulto elegível que não acha parceiro
  e tem energia ≥ `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` clona sozinho. Nos testes "não acasala
  sexuadamente" usei energia abaixo do limiar da clonagem (`SUB_ASEXUAL_ENERGY`) para que o resultado
  meça só o gate sexual, sem um clone mascarando a contagem.
- **`sensors.py`**: não usa `MIN_ENERGY_TO_MATE` (usa `MATE_ATTRACTION_ENERGY_FRACTION` do BIT-21); só o
  comentário citava a constante removida — atualizado, lógica intacta.

## Resultado dos gates
- `import main` → `OK - app importa`.
- `pytest tests/` → **127 passed, 6 warnings** (warnings são DeprecationWarning do neat-python, pré-existentes).
- `get_state().width == 1400` e `height == 1400` confirmado.

## Validação funcional (engine real, 5 min simulados a 30 FPS, população inicial 10)
Contagem de nascimentos por via (spies em `organic_crossover` = sexuada / `clone_genome` = assexuada),
com `MATING_RADIUS=150` (valor commitado):

| seed | sexual | asexual | pop_min | pop_max | pop_end |
|-----:|-------:|--------:|--------:|--------:|--------:|
| 1 | 1 | 2 | 1 | 12 | 10 |
| 2 | 2 | 3 | 1 | 14 | 3 |
| 3 | 2 | 8 | 1 | 13 | 5 |

Corrida ampliada (5 seeds) durante a calibração com raio 150: sexual = 1, 2, 2, 5, 3 (média ≈ 2.6/run).

**Conclusão:** reprodução sexuada > 0 e recorrente em todos os seeds (nenhum em 0 com raio 150),
alvo ≈ 2/run atingido. Sem extinção (pop_min ≥ 1 em todos os seeds — o Jardim do Éden segura o piso) e
sem boom-bust (pop_max ~12-14). Antes desta task a sexuada era 0.

**Escada de calibração usada:** apenas o degrau 1 (`MATING_RADIUS` 120→150). Com 120 a média ficava
~1/run e um seed zerava; 150 destravou a recorrência sem tocar mapa/comida/supressão. Nenhum ajuste
adicional necessário.
