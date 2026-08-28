# Spec — BIT-39: Seleção por Fitness no Acasalamento

**Linear:** N/A
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

Atualmente, o loop de acasalamento sexuado (`engine.py`, linhas 215–263) seleciona o **primeiro candidato elegível** em ordem de iteração. Isso resulta em **seleção por artefato de ordem de inserção**, não em seleção por aptidão. Criaturas de alta fitness têm a mesma probabilidade de passar genes que criaturas de baixa fitness, desde que ambas estejam dentro de MATING_RADIUS.

**Objetivo:** Substituir a seleção determinística (primeiro válido) por **seleção ponderada por fitness**, de modo que criaturas com maior aptidão sejam parceiras preferidas.

**Métrica de aptidão:** Reutilizar a fórmula já estabelecida no Hall of Fame (linhas 166–168):
```
score = age + 20×children_count + 1×food_eaten
```

**Benefício:** Pressão seletiva direcional em favor de genomas que produzem criaturas que vivem mais, têm mais filhos e comem mais comida. Acelera seleção natural no simulador.

---

## Abordagem técnica

### Estratégia de ponderação: Peso Proporcional Simples

**Por que não Softmax?**
- Softmax exigiria um novo hiperparâmetro (temperatura `T`), que requer tuning.
- Com pesos simples e proporcionalidade direta, o método é:
  - **Testável deterministicamente** (com seed conhecido, result é reproduzível)
  - **Sem novo parâmetro público** (usa constantes já existentes)
  - **Robusto** contra casos patológicos (score 0 em todos os candidatos → distribuição uniforme)

### Fórmula de seleção

Para cada candidato `b` em `candidates`:
```
score_b = b.age + HALL_OF_FAME_CHILDREN_WEIGHT × b.children_count + HALL_OF_FAME_FOOD_WEIGHT × b.food_eaten
weight_b = max(score_b, 1.0)  # piso 1.0 para garantir distribuição válida (evita score 0)
```

Seleção com `random.choices`:
```python
selected = random.choices(candidates, weights=[max(score(c), 1.0) for c in candidates], k=1)[0]
```

**Piso 1.0:** Garante que Gen-0 (age ≈ 0, filhos = 0, comida = 0) não tenha peso zero. Com todos os candidatos em score 0, a soma de pesos é n (número de candidatos) e cada um tem probabilidade 1/n (uniforme).

---

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/simulation/engine.py` | modificar | Adicionar método `_select_mate_weighted()`; reestruturar inner loop do `for j` (linhas 232–260) |
| `backend/tests/test_reproduction.py` | modificar | Adicionar 3 novos testes para validar weighted selection |

---

## Passos de implementação

### 1. Adicionar método `_select_mate_weighted()` a SimulationEngine

Inserir após o método `_record_in_hall_of_fame()` (após linha 177) e antes de `_compute_food_multiplier()`:

```python
def _select_mate_weighted(self, candidates: list) -> Creature:
    """Seleciona um parceiro de acasalamento ponderado por fitness.
    
    Fórmula de score: age + HALL_OF_FAME_CHILDREN_WEIGHT×children_count + HALL_OF_FAME_FOOD_WEIGHT×food_eaten.
    Peso de cada candidato: max(score, 1.0) — piso 1.0 garante distribuição válida mesmo com score 0.
    
    Args:
        candidates: lista de Creature (já filtrados por elegibilidade e proximidade).
    
    Returns:
        Creature: um candidato selecionado proporcionalmente a seu fitness.
    
    Raises:
        IndexError se candidates está vazio. O chamador deve verificar.
    """
    if not candidates:
        raise IndexError("_select_mate_weighted: candidates vazio")
    
    # Calcular scores
    scores = []
    for candidate in candidates:
        score = (candidate.age
                 + HALL_OF_FAME_CHILDREN_WEIGHT * candidate.children_count
                 + HALL_OF_FAME_FOOD_WEIGHT * candidate.food_eaten)
        scores.append(max(score, 1.0))
    
    # Seleção ponderada
    selected = random.choices(candidates, weights=scores, k=1)[0]
    return selected
```

### 2. Reestruturar o inner loop `for j` (linhas 232–260)

**Antes (seleção determinística — primeiro válido):**
```python
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
    a.is_fertile = False
    b.is_fertile = False
    a.children_count += 1
    b.children_count += 1
    child_id = self.next_genome_id()
    child_genome = organic_crossover(a.genome, b.genome, child_id, a.config)
    mutate_genome(child_genome, a.config)
    cx = (a.body.position.x + b.body.position.x) / 2
    cy = (a.body.position.y + b.body.position.y) / 2
    child_gen = max(a.generation, b.generation) + 1
    sexual_children.append(Creature(self, cx, cy, genome=child_genome, generation=child_gen))
    break  # 'a' ja acasalou neste frame, passa para o proximo adulto
```

**Depois (seleção ponderada):**
```python
# Coletar candidatos válidos
candidates = []
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
    candidates.append(b)

# Se há candidatos válidos, selecionar um ponderado por fitness
if not candidates:
    continue

b = self._select_mate_weighted(candidates)

# Cruzam:
a.sought_mate_this_frame = True
b.sought_mate_this_frame = True
a.energy -= REPRODUCTION_ENERGY_COST
b.energy -= REPRODUCTION_ENERGY_COST
a.reproduction_cooldown = REPRODUCTION_COOLDOWN
b.reproduction_cooldown = REPRODUCTION_COOLDOWN
a.is_fertile = False
b.is_fertile = False
a.children_count += 1
b.children_count += 1
child_id = self.next_genome_id()
child_genome = organic_crossover(a.genome, b.genome, child_id, a.config)
mutate_genome(child_genome, a.config)
cx = (a.body.position.x + b.body.position.x) / 2
cy = (a.body.position.y + b.body.position.y) / 2
child_gen = max(a.generation, b.generation) + 1
sexual_children.append(Creature(self, cx, cy, genome=child_genome, generation=child_gen))
```

**Nota:** Remover o `break` original; o loop continua (se há múltiplos candidatos coletados, _select_mate_weighted escolhe um, mas a criatura `a` acasala com um único parceiro — não há um novo `break` porque só iteramos uma vez sobre a chamada a `_select_mate_weighted`).

### 3. Adicionar 3 novos testes a `backend/tests/test_reproduction.py`

Inserir após o último teste existente (`test_smoke_full_simulation_runs_without_exception_with_reproduction_active`, linha 206):

```python
def test_weighted_selection_favors_higher_score():
    """BIT-39: _select_mate_weighted deve favorecer candidatos com score maior.
    
    Com 2 candidatos, A com fitness muito maior que B, em 1000 trials A deve ser
    selecionado significativamente mais vezes que B (validado com frequência).
    """
    engine = SimulationEngine()
    
    # Candidato B: score baixo (age ≈ 0, filhos=0, comida=0 → score ≈ 1 com piso)
    low_fitness = Creature(engine, x=700, y=700)
    low_fitness.life_stage = LifeStage.ADULT
    low_fitness.age = 0.1
    low_fitness.children_count = 0
    low_fitness.food_eaten = 0
    
    # Candidato A: score alto (age=100, filhos=5, comida=10 → score ≈ 100+100+10 = 210)
    high_fitness = Creature(engine, x=700, y=700)
    high_fitness.life_stage = LifeStage.ADULT
    high_fitness.age = 100.0
    high_fitness.children_count = 5
    high_fitness.food_eaten = 10
    
    engine.add_creature(low_fitness)
    engine.add_creature(high_fitness)
    
    candidates = [low_fitness, high_fitness]
    
    # Simular 1000 seleções
    random.seed(42)
    selections = [engine._select_mate_weighted(candidates) for _ in range(1000)]
    high_fitness_count = sum(1 for c in selections if c is high_fitness)
    
    # high_fitness_count deve ser >> 500 (muito mais de 50%).
    # Com score 210 vs 1, esperamos ~99.5% de chance para high_fitness a cada trial.
    # 1000 trials: esperamos ~995 seleções de high_fitness; assert > 950 para margem.
    assert high_fitness_count > 950, f"Expected high_fitness >> 500, got {high_fitness_count}"


def test_single_candidate_selects_it():
    """BIT-39: _select_mate_weighted com 1 único candidato retorna sempre ele."""
    engine = SimulationEngine()
    
    candidate = Creature(engine, x=700, y=700)
    candidate.life_stage = LifeStage.ADULT
    candidate.age = 50.0
    candidate.children_count = 2
    candidate.food_eaten = 5
    
    engine.add_creature(candidate)
    candidates = [candidate]
    
    random.seed(42)
    for _ in range(10):
        selected = engine._select_mate_weighted(candidates)
        assert selected is candidate


def test_zero_score_candidates_select_uniformly():
    """BIT-39: Com todos candidatos em score 0 (Gen-0), distribuição deve ser uniforme.
    
    Piso de 1.0 garante que cada um tem peso 1.0, resultando em 1/n de probabilidade.
    Com 3 candidatos e 300 trials, cada deve ser selecionado ~100x (com margem).
    """
    engine = SimulationEngine()
    
    candidates = []
    for _ in range(3):
        c = Creature(engine, x=700, y=700)
        c.life_stage = LifeStage.ADULT
        c.age = 0.0  # Recém-nascido
        c.children_count = 0
        c.food_eaten = 0
        engine.add_creature(c)
        candidates.append(c)
    
    # 300 trials (100 por candidato esperado)
    random.seed(42)
    selections = [engine._select_mate_weighted(candidates) for _ in range(300)]
    
    # Cada candidato deve ser selecionado aprox. 100x (com margem: 50-150)
    for candidate in candidates:
        count = sum(1 for c in selections if c is candidate)
        assert 50 < count < 150, f"Candidate {candidate.id}: expected ~100 selections, got {count}"
```

---

## Contratos técnicos

### Backend (Simulação)

**Assinatura:**
```python
_select_mate_weighted(self, candidates: list[Creature]) -> Creature
```

**Pré-condição:** `candidates` não vazio (verificado pelo chamador).

**Cálculo de score (linha por linha):**
```
score = creature.age 
      + HALL_OF_FAME_CHILDREN_WEIGHT (20.0) × creature.children_count
      + HALL_OF_FAME_FOOD_WEIGHT (1.0) × creature.food_eaten
weight = max(score, 1.0)  # piso 1.0
```

**Seleção:** `random.choices(candidates, weights=[...], k=1)[0]`

**Invariantes:**
- Com 1 candidato: retorna sempre ele (trivial — `random.choices` com k=1).
- Com N candidatos, todos com score 0: distribuição uniforme 1/N (piso 1.0 garante).
- Com scores heterogêneos: probabilidade proporcional ao peso normalizado.

**Testes existentes não quebram:**
- `test_adult_pair_within_radius_reproduces()` e similares criam exatamente 1 par (`_make_adult_pair()`) — com 1 candidato, seleção retorna ele, comportamento idêntico ao `break` original.
- `test_smoke_full_simulation_runs_without_exception_with_reproduction_active()` cria 10 adultos no mesmo ponto — haverá múltiplos candidatos, mas o teste só verifica `len(creatures) < 200`, que continua válido.

---

## Critérios de aceite

- [ ] Método `_select_mate_weighted()` existe em `SimulationEngine` (linha ~178–198)
- [ ] Inner loop do `for j` foi reestruturado: coleta candidatos em lista, verifica `if not candidates: continue`, chama `_select_mate_weighted(candidates)`
- [ ] 3 novos testes adicionados e passam: `test_weighted_selection_favors_higher_score`, `test_single_candidate_selects_it`, `test_zero_score_candidates_select_uniformly`
- [ ] Todos os testes existentes de `test_reproduction.py` continuam passando (sem regressão)
- [ ] `pytest backend/tests/test_reproduction.py -v` → 0 falhas, 10 testes passam
- [ ] `pytest backend/tests/ -v` → 0 falhas (suite inteira)

---

## Rollback

Se o teste revelar regressões inesperadas:

1. Reverter `backend/simulation/engine.py`:
   - Remover método `_select_mate_weighted()` (linhas ~178–198)
   - Restaurar inner loop do `for j` ao formato original (reconstitua o `break` imediato)
   
2. Reverter `backend/tests/test_reproduction.py`:
   - Remover os 3 novos testes (`test_weighted_selection_favors_higher_score`, `test_single_candidate_selects_it`, `test_zero_score_candidates_select_uniformly`)
   
3. Verificar: `pytest backend/tests/test_reproduction.py -v` → 7 testes passam (original)

---

## Referências

- **Research document:** `.sdd/tasks/refiner/BIT-39/research/simulation-core.md`
- **Fitness proxy:** Hall of Fame formula (`engine.py` linhas 166–168) — idêntica ao usado em BIT-39
- **Constantes reutilizadas:** `HALL_OF_FAME_CHILDREN_WEIGHT = 20.0`, `HALL_OF_FAME_FOOD_WEIGHT = 1.0`
- **Teste base:** `_make_adult_pair()` helper em `test_reproduction.py` (linhas 19–35)
