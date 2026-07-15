# Spec — BIT-22: Reprodução Sexuada Emergente

**Linear:** N/A
**Risco:** high
**Camada(s):** Backend (Simulação)

---

## Demanda

A reprodução sexuada está em **0%** — toda reprodução é clonagem assexuada. O BIT-21 deixou 100% dos
adultos que se encontram *querendo* acasalar, mas o acasalamento nunca acontece. O objetivo é fazer a
reprodução **sexuada emergir de forma observável e recorrente** desde o início, redesenhando o
ecossistema para dar densidade e prosperidade suficientes, e resolvendo o teste pré-existente que falha
(`test_exploration_pressure.py::test_newborn_still_has_to_eat_before_mating`).

## Abordagem técnica

Investigação (18 experimentos headless, ver `research/simulation-core.md`) mostrou que a raiz **não é o
gate de acasalamento** — é **carrying capacity + esparsidade espacial** no mapa 2000×2000. Nenhum lever
isolado destrava; a combinação validada (spawn realista, 6 seeds × 6 min: **0 → 14 nascimentos
sexuados**) tem 5 frentes, todas em `backend/simulation/`:

1. **Mapa 2000→1400** (lever decisivo): metade da área ⇒ densidade suficiente para dois adultos férteis
   se aproximarem. No 2000 a sexuada fica em 0 mesmo com todos os outros levers.
2. **Acasalamento por PROXIMIDADE** (raio ~120px) no lugar de colisão física exata no mesmo frame — o
   evento "duas criaturas se tocando no mesmo instante" é raro demais em espaço contínuo esparso.
   Preserva o cérebro no comando (ambos ainda precisam `action_mate`).
3. **Fertilidade persistente + flag `has_eaten`**: a criatura vira fértil ao ser ADULT + já ter comido +
   energia ≥ limiar alcançável (60); mantém a fertilidade mesmo com a energia caindo no roaming, até
   acasalar. Isso desacopla o gate do instante da colisão. `has_eaten` preserva "comer antes de
   acasalar" (intenção do BIT-16) de forma ortogonal ao nível de energia — resolvendo o conflito que
   quebrou o teste (limiar > STARTING_ENERGY era inalcançável; limiar alcançável nascia satisfeito).
4. **Comida moderadamente mais farta**: sustenta mais adultos bem-nutridos simultâneos.
5. **Reprodução assexuada suprimida**: sem isso, a comida mais farta faz a clonagem explodir e abafar a
   sexuada, além de causar boom-bust populacional. Continua como válvula de emergência anti-extinção.

Dependência: nenhuma pendente. Constrói sobre BIT-20 (economia de energia) e BIT-21 (semente de
`action_mate` + food-taxis), ambos já commitados.

**Fora de escopo:** frontend (o canvas já auto-escala por `data.width/height`, confirmado em
`SimulationCanvas.jsx:94-96`), API/WebSocket (payload inalterado), contrato de I/O do NEAT (intacto).

## Arquivos a tocar

| Arquivo (path relativo à raiz) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/physics.py` | modificar | `map_width`/`map_height` 2000 → 1400 |
| `backend/simulation/creature.py` | modificar | Atributos `has_eaten`, `is_fertile`; constante `FERTILITY_ENERGY_THRESHOLD`; lógica de fertilidade em `update()` |
| `backend/simulation/engine.py` | modificar | `has_eaten` no handler de comida; reprodução sexuada por proximidade no `step()` (substitui o handler de colisão criatura×criatura); assexuada gated por "sem parceiro em alcance"; novas constantes; supressão da assexuada |
| `backend/simulation/oasis.py` | modificar | `MAX_TOTAL_FOOD` 50→110, `OASIS_FOOD_SPAWN_CHANCE` 0.08→0.18, `MAX_ACTIVE_OASES` 4→6, `OASIS_FOOD_CAP` 8→18 |
| `backend/simulation/food.py` | modificar | `energy_value` default 25→32 |
| `backend/tests/test_reproduction.py` | modificar | Adaptar à mecânica de proximidade + fertilidade (não mais colisão + `MIN_ENERGY_TO_MATE`) |
| `backend/tests/test_exploration_pressure.py` | modificar | Reescrever `test_newborn_still_has_to_eat_before_mating` para o invariante `has_eaten` |
| `backend/tests/test_sexual_reproduction.py` | criar | Testes da fertilidade, proximidade e supressão da assexuada |

## Passos de implementação

> Passos 1-5 são independentes entre si (constantes/atributos). Passo 6 (fluxo de reprodução no
> `engine.step`) depende de 1-3. Passos 7-8 (testes) dependem de todos. Passo 9 valida/calibra.

### 1. `physics.py` — mapa menor

Em `create_space()`, trocar as dimensões:

```python
    map_width = 1400   # BIT-22: era 2000 — 2000x2000 e esparso demais para reproducao sexuada emergir
    map_height = 1400  # (metade da area ~ dobro da densidade; frontend auto-escala por data.width/height)
```

### 2. `creature.py` — flags e limiar de fertilidade

Adicionar constante de módulo (perto de `STARTING_ENERGY`):

```python
# BIT-22: reproducao sexuada por FERTILIDADE PERSISTENTE, nao por energia instantanea na colisao.
# A criatura vira fertil ao atingir este limiar (tendo comido) e MANTEM a fertilidade mesmo com a
# energia caindo no roaming, ate acasalar. O limiar e ALCANCAVEL de proposito (< max_energy); "comer
# antes de acasalar" (BIT-16) e garantido pela flag has_eaten, nao pelo nivel de energia.
FERTILITY_ENERGY_THRESHOLD = 60.0
```

Em `Creature.__init__`, adicionar (junto de `self.reproduction_cooldown = 0.0`):

```python
        self.has_eaten = False   # BIT-22: setada ao comer (handler de colisao criatura x comida).
        self.is_fertile = False  # BIT-22: fertilidade persistente para reproducao sexuada.
```

Em `Creature.update()`, após atualizar `life_stage`/energia e **antes** do `return`, adicionar a
promoção de fertilidade (não zera aqui — só é zerada no acasalamento):

```python
        # Fertilidade persistente (BIT-22): vira fertil ao ser ADULT, ja ter comido e alcancar o limiar.
        # Uma vez fertil, permanece ate acasalar (o roaming faz a energia cair, mas nao tira a aptidao).
        if (self.life_stage == LifeStage.ADULT and self.has_eaten
                and self.energy >= FERTILITY_ENERGY_THRESHOLD):
            self.is_fertile = True
```

### 3. `engine.py` — `has_eaten` no handler de comida

No `_on_creature_food_collision`, ao transferir energia, marcar que comeu:

```python
            if food.is_active and creature.is_alive:
                creature.energy = min(creature.energy + food.energy_value, creature.max_energy)
                creature.has_eaten = True  # BIT-22: habilita fertilidade (comer antes de acasalar)
                food.consume()
```

### 4. `oasis.py` — comida mais farta

```python
MAX_ACTIVE_OASES = 6          # BIT-22: era 4
OASIS_FOOD_SPAWN_CHANCE = 0.18  # BIT-22: era 0.08
OASIS_FOOD_CAP = 8            # -> passa a 18 (ver abaixo)
MAX_TOTAL_FOOD = 110          # BIT-22: era 50
```
Ajustar `OASIS_FOOD_CAP = 18` (era 8). Manter as constantes do Éden inalteradas (o Éden segue como
seguro anti-extinção; suas distâncias 250-400 continuam válidas no mapa 1400).

### 5. `food.py` — comida vale mais

```python
    def __init__(self, engine, x, y, energy_value=32.0):  # BIT-22: era 25.0
```

### 6. `engine.py` — reprodução sexuada por proximidade + supressão da assexuada

Constantes (topo do módulo):

```python
MATING_RADIUS = 120.0  # BIT-22: acasalamento por PROXIMIDADE, nao por colisao exata no mesmo frame
                       # (evento raro demais em espaco continuo esparso). Ambos ainda precisam querer
                       # (action_mate) — o cerebro segue no comando.
REPRODUCTION_ENERGY_COST = 30.0        # inalterado
REPRODUCTION_COOLDOWN = 10.0           # inalterado
# MIN_ENERGY_TO_MATE removido: substituido por is_fertile (BIT-22). O unico piso de energia no
# acasalamento e a sobrevivencia (energia >= REPRODUCTION_ENERGY_COST, para nao acasalar ate a morte).
MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 100.0  # BIT-22: era 90 — assexuada exige energia cheia
ASEXUAL_REPRODUCTION_ENERGY_COST = 95.0    # BIT-22: era 85 — clonar vira aposta quase suicida
ASEXUAL_REPRODUCTION_COOLDOWN = 45.0       # inalterado
```

**Remover** o handler `_on_creature_creature_collision` e seu registro `on_collision(...CREATURE,
CREATURE...)` — a reprodução sexuada deixa de depender de colisão. A física de colisão entre criaturas
continua funcionando por padrão (shapes têm elasticidade); não é preciso callback. O atributo
`collided_with_creature_this_frame` deixa de ser necessário (era usado só pelo gate da assexuada);
substituído por `sought_mate_this_frame` (abaixo).

Em `Creature.__init__`, trocar `self.collided_with_creature_this_frame = False` por
`self.sought_mate_this_frame = False`.

No `step()`, **antes** do laço da assexuada (o atual bloco "1.5"), inserir o **scan de reprodução
sexuada por proximidade**:

```python
        # Reset da flag de "tinha parceiro viavel por perto" (usada para nao clonar quem podia acasalar)
        for creature in self.creatures:
            creature.sought_mate_this_frame = False

        # Reproducao sexuada por PROXIMIDADE (BIT-22): dois adultos FERTEIS, ambos querendo acasalar,
        # dentro de MATING_RADIUS, fora de cooldown e com energia para sobreviver ao parto -> cruzam.
        sexual_children = []
        alive_adults = [c for c in self.creatures
                        if c.is_alive and c.life_stage == LifeStage.ADULT]
        radius_sq = MATING_RADIUS * MATING_RADIUS
        for i in range(len(alive_adults)):
            a = alive_adults[i]
            if not (a.is_fertile and a.action_mate) or a.reproduction_cooldown > 0:
                continue
            if a.energy < REPRODUCTION_ENERGY_COST:
                continue
            for j in range(i + 1, len(alive_adults)):
                b = alive_adults[j]
                if not (b.is_fertile and b.action_mate) or b.reproduction_cooldown > 0:
                    continue
                if b.energy < REPRODUCTION_ENERGY_COST:
                    continue
                dx = a.body.position.x - b.body.position.x
                dy = a.body.position.y - b.body.position.y
                if dx * dx + dy * dy > radius_sq:
                    continue
                # Cruzam:
                a.sought_mate_this_frame = True
                b.sought_mate_this_frame = True
                a.energy -= REPRODUCTION_ENERGY_COST
                b.energy -= REPRODUCTION_ENERGY_COST
                a.reproduction_cooldown = REPRODUCTION_COOLDOWN
                b.reproduction_cooldown = REPRODUCTION_COOLDOWN
                a.is_fertile = False  # re-conquistar a fertilidade comendo de novo
                b.is_fertile = False
                child_id = self.next_genome_id()
                child_genome = organic_crossover(a.genome, b.genome, child_id, a.config)
                mutate_genome(child_genome, a.config)
                cx = (a.body.position.x + b.body.position.x) / 2
                cy = (a.body.position.y + b.body.position.y) / 2
                sexual_children.append(Creature(self, cx, cy, genome=child_genome))
                break  # 'a' ja acasalou neste frame (cooldown), passa para o proximo adulto
        for child in sexual_children:
            self.add_creature(child)
```

No laço da **assexuada** (bloco "1.5"), trocar o gate `if creature.collided_with_creature_this_frame:
continue` por `if creature.sought_mate_this_frame: continue` — assim a criatura só clona se **não**
havia parceiro viável por perto neste frame (preserva a intenção "assexuada = estar sozinha").

Remover o bloco no início do `step()` que reseta `collided_with_creature_this_frame` (o reset de
`sought_mate_this_frame` agora vive no scan sexual acima).

### 7. `test_reproduction.py` e `test_exploration_pressure.py` — adaptar

- `test_reproduction.py`: os testes que montavam duas criaturas colidindo e setavam `action_mate` +
  energia ≥ `MIN_ENERGY_TO_MATE` precisam refletir a nova mecânica: posicionar dois adultos **dentro de
  `MATING_RADIUS`**, marcar `is_fertile = True` (ou levá-los a comer/atingir o limiar), `action_mate =
  True`, cooldown 0, e chamar `engine.step(dt)`; afirmar que nasceu um filho (população +1) e que
  `is_fertile` foi zerada e o cooldown setado. Ajustar/!substituir asserções que dependiam de
  `MIN_ENERGY_TO_MATE`. Importar `MATING_RADIUS`.
- `test_exploration_pressure.py::test_newborn_still_has_to_eat_before_mating`: reescrever para o novo
  invariante — um adulto recém-criado com `has_eaten == False` **não** fica fértil mesmo com energia
  cheia (`update()` não seta `is_fertile`); depois de comer (setar `has_eaten = True`) e atingir o
  limiar, fica fértil. Não depende mais de `MIN_ENERGY_TO_MATE > STARTING_ENERGY`.

### 8. `test_sexual_reproduction.py` — novo arquivo

Importar constantes de `simulation.engine` (`MATING_RADIUS`, custos, cooldowns) e
`simulation.creature` (`FERTILITY_ENERGY_THRESHOLD`) — nunca hardcodar. Cobrir:

1. **`has_eaten` gate**: adulto com `energy = max_energy`, `has_eaten = False` → após `update()`,
   `is_fertile` continua `False`. Setar `has_eaten = True` e `update()` → `is_fertile = True`. *(É o
   novo "comer antes de acasalar".)*
2. **Fertilidade persistente**: uma vez `is_fertile = True`, cair a energia abaixo do limiar (mas > 0)
   **não** zera `is_fertile`.
3. **Acasalamento por proximidade**: dois adultos férteis, `action_mate = True`, cooldown 0, a
   `< MATING_RADIUS` → `step()` cria +1 criatura e zera `is_fertile` de ambos + seta cooldown. A
   `> MATING_RADIUS` (mesmas condições) → nenhum filho.
4. **Ambos precisam querer**: um dos dois com `action_mate = False` → não acasala.
5. **Assexuada suprimida na presença de parceiro**: adulto fértil com energia ≥
   `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` e outro parceiro viável dentro de `MATING_RADIUS` → não clona
   (acasala sexuadamente); sozinho (parceiro fora do raio) e com energia cheia → clona.
6. **Sobrevivência**: adulto fértil com `energy < REPRODUCTION_ENERGY_COST` não acasala (evita parto
   suicida).

### 9. Validação e calibração (headless)

Rodar a suíte (`venv\Scripts\python.exe -m pytest tests/ -v`) — 100% verde. Depois validar
funcionalmente o comportamento emergente com múltiplos seeds (o harness paralelo do refino está em
`scratchpad/sim_harness.py`, mas basta um laço headless simples): rodar o engine real por ~5 min
simulados × vários seeds e **medir nascimentos sexuados > 0 e recorrentes**, população não-extinta e
sem boom-bust. Alvo medido na calibração: **≈ 2 nascimentos sexuados por run de 5-6 min** (contra 0
hoje). Se ficar abaixo do esperado, ajustar nesta ordem **sem** mudar a estrutura:
1. `MATING_RADIUS` 120 → 150 (mais encontros)
2. `map_width/height` 1400 → 1200 (mais densidade)
3. comida (`OASIS_FOOD_SPAWN_CHANCE`, `MAX_TOTAL_FOOD`) um degrau acima
Se a população colapsar (extinções em cadeia), afrouxar a supressão da assexuada
(`MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` 100 → 95).

## Contratos técnicos

### Backend (Simulação)

**`physics.py`** — `map_width = map_height = 1400`.

**`creature.py`** — constante `FERTILITY_ENERGY_THRESHOLD = 60.0`. `Creature` ganha
`has_eaten: bool = False` e `is_fertile: bool = False`. `update()` seta `is_fertile = True` quando
ADULT + `has_eaten` + `energy >= FERTILITY_ENERGY_THRESHOLD` (nunca zera aqui). `__init__` passa a ter
`sought_mate_this_frame` no lugar de `collided_with_creature_this_frame`.

**`engine.py`** — constante nova `MATING_RADIUS = 120.0`. Removidos: `MIN_ENERGY_TO_MATE` e o handler
`_on_creature_creature_collision` (+ seu registro). Alterados: `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`
90→100, `ASEXUAL_REPRODUCTION_ENERGY_COST` 85→95. `_on_creature_food_collision` seta `has_eaten`. Novo
bloco de reprodução sexuada por proximidade em `step()` (O(n²) sobre adultos vivos — trivial para a
população-alvo). Gate da assexuada passa a usar `sought_mate_this_frame`.

**`oasis.py`** — `MAX_ACTIVE_OASES=6`, `OASIS_FOOD_SPAWN_CHANCE=0.18`, `OASIS_FOOD_CAP=18`,
`MAX_TOTAL_FOOD=110`.

**`food.py`** — `Food.__init__(..., energy_value=32.0)`.

### API/WebSocket
**Nenhuma mudança de formato.** `get_state()` já emite `width`/`height` (agora 1400) e o mesmo schema de
criaturas/comida/oásis. Nenhum campo novo é exposto (fertilidade é estado interno; se desejável exibir
no futuro, é outra task).

### Frontend
**Nenhuma mudança.** `SimulationCanvas.jsx` já lê `data.width`/`data.height` e auto-escala.

### Contrato de I/O do NEAT
**Inalterado** — 16 inputs / 4 outputs. `action_mate` (output 3) continua sendo o sinal de "quero
acasalar"; muda apenas *quando/como* o acasalamento é disparado (proximidade + fertilidade, no engine).

## Critérios de aceite

- [ ] Mapa 1400×1400 (`get_state().width == 1400`); frontend renderiza corretamente (auto-escala).
- [ ] Um adulto recém-criado com `has_eaten == False` **não** fica fértil nem com energia cheia; após
      comer e atingir `FERTILITY_ENERGY_THRESHOLD`, fica fértil. (Novo "comer antes de acasalar".)
- [ ] `is_fertile`, uma vez `True`, **persiste** quando a energia cai (não é zerada até acasalar).
- [ ] Dois adultos férteis, ambos com `action_mate`, cooldown 0, dentro de `MATING_RADIUS` → `step()`
      gera **+1** criatura, zera `is_fertile` de ambos e seta o cooldown. Fora do raio → sem filho.
- [ ] Adulto com `energy < REPRODUCTION_ENERGY_COST` não acasala (sem parto suicida).
- [ ] Assexuada não dispara quando há parceiro viável dentro de `MATING_RADIUS`; continua funcionando
      como válvula quando a criatura está sozinha e com energia cheia (≥ `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`).
- [ ] `pytest backend/tests/` 100% verde (inclui o `test_newborn...` reescrito).
- [ ] **Validação funcional (a que importa):** rodando headless por ~5 min × vários seeds, **nascem
      criaturas por reprodução sexuada** (crossover entre dois pais), > 0 e recorrente (alvo ≈ 2/run),
      sem colapso populacional nem boom-bust. Observável no `manager.py` como novos EGGs surgindo entre
      pares de adultos que se aproximam, não só por clonagem solitária.

## Rollback

Reverter os 5 arquivos de `backend/simulation/` (`physics.py`, `creature.py`, `engine.py`, `oasis.py`,
`food.py`), restaurar `test_reproduction.py` e `test_exploration_pressure.py`, e deletar
`backend/tests/test_sexual_reproduction.py`. Nenhuma migração de dados; nenhum contrato externo tocado —
`git checkout -- backend/` e remover o arquivo novo. O mapa menor e a mecânica de proximidade são
puramente de simulação; genomas e payloads antigos permanecem compatíveis.
