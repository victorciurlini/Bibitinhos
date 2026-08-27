## Arquivos relevantes

- `backend/simulation/engine.py` — `_on_creature_creature_collision` (reprodução sexuada, colisão + `Action_Mate`), `SimulationEngine.step()` (loop principal por frame)
- `backend/simulation/creature.py` — `Creature.__init__` (`mate_cooldown`, `action_mate`), `Creature.think()` (mapeia output 3 da rede para `action_mate`), `LifeStage`
- `backend/simulation/rtneat_wrapper.py` — contrato de I/O do NEAT (docstring), `organic_crossover`, `mutate_genome`
- `backend/tests/test_reproduction.py` — padrão de teste da reprodução sexuada existente (fixture `_make_adult_pair`, stub de `think()` para isolar de aleatoriedade)
- `README.md` linhas 40, 303-317 — reprodução assexuada ("clonagem") estava no roadmap original (Milestone 2) mas foi pulada quando o projeto foi direto para rtNEAT real; nunca foi implementada

## Conteúdo relevante para a demanda

### Reprodução sexuada atual (`engine.py:43-76`)

Collision handler `COLLISION_CATEGORY_CREATURE x COLLISION_CATEGORY_CREATURE`:
1. Ambos `is_alive`
2. Ambos `life_stage == ADULT`
3. Ambos `mate_cooldown <= 0`
4. Ambos `action_mate == True` (output 3 da rede, binário via threshold em `think()`)
5. Ambos `energy >= MIN_ENERGY_TO_MATE` (50.0)
6. Custo: `REPRODUCTION_ENERGY_COST` (30.0) de cada um; `mate_cooldown = REPRODUCTION_COOLDOWN` (10.0) para ambos
7. Filho: `organic_crossover(g1, g2, id, config)` + `mutate_genome(...)`, nasce em `EGG` no ponto médio dos dois pais

### Contrato de I/O do NEAT (`rtneat_wrapper.py`, docstring)

4 outputs fixos: `Motor_Forward`, `Motor_Torque`, `Action_Grab_Drop`, `Action_Mate` (índice 3). Mudar a topologia de saída (`neat_config.ini` + docstring) é tratado como mudança de alto risco no projeto (regra explícita no protocolo do implementer: "não mexer no contrato de I/O do NEAT... a menos que a spec explicitamente peça"). **Decisão tomada com o developer:** não adicionar output novo — reaproveitar `Action_Mate` como sinal geral de "quero reproduzir", resolvido para sexuada ou assexuada dependendo do contexto físico (colidiu com parceiro elegível vs. sozinho).

### Clonagem de genoma — validado ao vivo

`rtneat_wrapper.py` não tem função de clonagem (só `create_zero_genome` e `organic_crossover`, ambos exigem 0 ou 2 pais). Validei via Python real (venv do projeto) que `copy.deepcopy(genome)` + reatribuição de `.key` produz um genoma independente (conexões não compartilham referência) e que `mutate_genome()` funciona normalmente sobre o clone:

```
original key: 1 clone key: 2
same connections object? False
nodes equal before mutate: True
OK mutate after deepcopy clone
clone connections: 64 original connections: 64
```

### `mate_cooldown` — escopo do rename

`mate_cooldown` é referenciado em `creature.py`, `engine.py` e `tests/test_reproduction.py` apenas (não aparece no frontend nem no protocolo WebSocket/`to_dict()`). Rename seguro e contido ao backend.

## O que precisa ser feito

1. Nova função `clone_genome(genome, genome_id, config)` em `rtneat_wrapper.py` (deepcopy + reassign key), documentada como abstração pura ao lado de `create_zero_genome`/`organic_crossover`.
2. Renomear `mate_cooldown` → `reproduction_cooldown` em `creature.py`, `engine.py`, `test_reproduction.py` (cooldown único, compartilhado entre os dois caminhos de reprodução — evita que uma criatura reproduza duas vezes no mesmo frame por vias diferentes).
3. Novo passo em `SimulationEngine.step()` (loop por criatura, após a física do frame já ter resolvido colisões): para cada criatura `ADULT`, `action_mate == True`, `reproduction_cooldown <= 0` e `energy >= MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` — se **não** acabou de reproduzir sexuadamente neste mesmo frame (garantido pelo cooldown já setado pelo handler de colisão, que roda antes dentro de `physics.step()`), clona e muta o próprio genoma, debita `ASEXUAL_REPRODUCTION_ENERGY_COST`, seta `reproduction_cooldown`, nasce `EGG` na posição do pai/mãe.
4. Novas constantes em `engine.py`: `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`, `ASEXUAL_REPRODUCTION_ENERGY_COST`, `ASEXUAL_REPRODUCTION_COOLDOWN` (cooldown mais longo que o sexuado, para não tornar a via solo estritamente dominante).
5. Testes novos em `test_reproduction.py` (ou arquivo dedicado `test_asexual_reproduction.py`, mais alinhado ao padrão 1-arquivo-por-BIT já usado em `test_food_physics.py`/BIT-08).

## Perguntas em aberto

Nenhuma — decisão de arquitetura (gatilho via `Action_Mate` reaproveitado) já validada com o developer antes da consolidação da spec.
