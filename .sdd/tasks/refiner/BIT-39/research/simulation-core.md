# Research — simulation-core (BIT-39: Seleção por Fitness no Acasalamento)

> Leitura direta de `backend/simulation/engine.py` e `backend/tests/test_reproduction.py`.

---

## Loop atual de acasalamento sexuado (`engine.py`, linhas 215–263)

```python
# 1.4. Reproducao sexuada por PROXIMIDADE (BIT-22)
for creature in self.creatures:
    creature.sought_mate_this_frame = False

sexual_children = []
alive_adults = [c for c in self.creatures
                if c.is_alive and c.life_stage in (LifeStage.ADULT, LifeStage.ELDER)]
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

---

## Análise do comportamento atual

**Estratégia de seleção:** O loop itera `alive_adults[i+1:]` e pega o **primeiro** candidato `b`
que satisfaça todos os gates (fértil, action_mate, fora de cooldown, energia suficiente, dentro
de MATING_RADIUS). O `break` ao final garante que `a` acasala com **um único parceiro por frame**.
Não há critério de preferência: o primeiro candidato ordenado por índice de inserção ganha.

**Problema:** A ordenação de `alive_adults` é a ordem de `self.creatures`, que é de inserção
(nascimento). Criaturas mais antigas ficam naturalmente à frente — mas isso é artifact de ordem
de lista, não uma pressão de seleção intencional. Com populações densas, `a` acasala sempre com
o parceiro que nasceu mais cedo e está dentro do raio, não com o mais apto.

**Impacto:** Deriva genética pura. Genomas de alta aptidão têm a mesma probabilidade de passar
genes que genomas de baixa aptidão, desde que ambos estejam dentro do MATING_RADIUS.

---

## Ponto de inserção da seleção ponderada

A mudança é cirúrgica: **apenas o `for j` interno precisa ser reestruturado**. Em vez de pegar o
primeiro `b` válido por ordem de índice, coletar todos os `b` válidos e escolher por peso.

```
for i in range(len(alive_adults)):
    a = ...elegibility gates...
    candidates = [b for j,b in ... if elegible(b) and within_radius(a, b)]
    if not candidates:
        continue
    b = _select_mate_weighted(candidates)   # <-- NOVO
    # mesmo bloco de acasalamento de antes
```

---

## Atributos disponíveis na Creature para o proxy score

| Atributo | Tipo | Fonte |
|---|---|---|
| `creature.age` | `float` | atualizado em `update()` a cada frame |
| `creature.children_count` | `int` | incrementado em cada reprodução (sexual + assexual) |
| `creature.food_eaten` | `int` | incrementado no handler de colisão comida |

**Fórmula proxy (idêntica ao Hall of Fame — `engine.py:166-168`):**
```python
score = creature.age + HALL_OF_FAME_CHILDREN_WEIGHT * creature.children_count + HALL_OF_FAME_FOOD_WEIGHT * creature.food_eaten
```

Constantes já existentes e importadas em `engine.py`:
- `HALL_OF_FAME_CHILDREN_WEIGHT = 20.0`
- `HALL_OF_FAME_FOOD_WEIGHT = 1.0`

---

## Método de ponderação: Opção A (peso proporcional simples)

**Opção A — Peso proporcional:**
```
weight_b = score_b / sum(scores)
```

**Opção B — Softmax:**
```
weight_b = exp(score_b / T) / sum(exp(scores / T))
```

**Decisão: Opção A.**

Justificativas:
1. **Testabilidade determinística:** com pesos fixos, `random.choices` com seed conhecido produz
   resultado verificável em teste unitário — ideal para `test_reproduction.py`.
2. **Sem hiperparâmetro novo:** temperatura `T` do softmax exigiria tuning e uma nova constante
   pública. Com N candidatos de scores similares (situação comum em populações jovens), softmax
   com T errado pode colapsar para escolha uniforme (T→∞) ou winner-take-all (T→0).
3. **Score zero não é problema:** se `score_b == 0` para todos os candidatos, a soma é zero e
   o peso seria indefinido. Solução: usar `max(score, 1.0)` como piso — qualquer criatura viva
   tem ao menos peso 1 (garante distribuição uniforme quando todos têm score 0, e.g. Gen 0).
4. **Complexidade:** O(n) sobre os candidatos, idêntica ao loop atual que também é O(n).

---

## Testes existentes afetados

`backend/tests/test_reproduction.py` tem 7 testes. Os que criam **exatamente 1 par** (`_make_adult_pair`)
não são afetados: com um único candidato, a seleção ponderada retorna o único elemento — comportamento
idêntico ao atual.

O smoke test (`test_smoke_full_simulation_runs_without_exception_with_reproduction_active`) cria 10
adultos no mesmo ponto — haverá múltiplos candidatos. Este teste só verifica que `len(creatures) < 200`,
que continua valendo. Nenhuma regressão esperada.

**Novos testes necessários:**
- `test_weighted_selection_favors_higher_score`: com 2 candidatos de scores muito diferentes, o de
  score maior deve ser selecionado com probabilidade significativamente maior (verificado por
  frequência em N trials com seed fixo ou usando `random.choices` monkeypatchado).
- `test_single_candidate_selects_it`: `_select_mate_weighted([c])` retorna `c` diretamente.
- `test_zero_score_candidates_select_uniformly`: todos com score 0 → distribuição uniforme.
