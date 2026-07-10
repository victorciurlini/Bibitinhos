## Arquivos relevantes

- `backend/simulation/creature.py` — depende do que BIT-02 introduz: `self.genome`, `self.config`, `self.action_mate` (bool, output 3 do cérebro), `self.life_stage`
- `backend/simulation/rtneat_wrapper.py` — `organic_crossover(genome1, genome2, genome_id, config)` e `mutate_genome(genome, config)` já existentes e testados desde BIT-00
- `backend/simulation/engine.py` — depende do que BIT-03 introduz: padrão de `space.on_collision(...)` registrado no `__init__`, e do que BIT-02 introduz: `next_genome_id()`

## Conteúdo relevante para a demanda

### Dependências diretas (bloqueantes)
- **BIT-02** precisa estar mergeada: fornece `creature.action_mate` (saída do cérebro, sem isso não há critério de "quer acasalar") e `creature.genome`/`creature.config` (necessários para `organic_crossover`).
- **BIT-03** não é bloqueante tecnicamente, mas estabelece o padrão de collision handler (`space.on_collision`, back-reference `shape.owner`) que esta task reaproveita — fica mais consistente implementar depois dela.

### `organic_crossover`/`mutate_genome` (já prontos, BIT-00)
```python
child = organic_crossover(genome1, genome2, genome_id, config)  # exige fitness numerico nos pais, ja tratado com default 0.0
mutate_genome(child, config)  # aplica mutacao nas probabilidades do .ini
```
Testado e coberto por `backend/tests/test_rtneat_wrapper.py` — não precisa de mudança, só ser chamado no callback de colisão.

### Validação ao vivo: adicionar novo body/shape dentro de um callback de colisão (pymunk 7.2.0)
```python
def begin(arbiter, space, data):
    nb = pymunk.Body(1, 10); nb.position = (100, 100)
    ns = pymunk.Circle(nb, 5); ns.collision_type = 1
    space.add(nb, ns)
    return True
space.on_collision(1, 1, begin=begin)
space.step(1/30.0)  # -> funciona, body novo aparece em space.bodies imediatamente
```
Confirmado: instanciar uma nova `Creature` (que chama `engine.physics.space.add(...)` no seu `__init__`) dentro do callback `begin` de uma colisão criatura×criatura funciona sem erro nesta versão do pymunk. `begin` só dispara uma vez por *novo* contato (não refire a cada frame enquanto as duas shapes continuam se tocando), o que já evita reprodução em loop mesmo sem cooldown — mas um cooldown continua desejável para quando as criaturas se separam e se re-tocam.

### Collision handler: mesmo `collision_type` nos dois lados
Diferente de BIT-03 (creature×food, dois `collision_type` distintos), aqui os dois shapes envolvidos são `COLLISION_CATEGORY_CREATURE` — registrar `space.on_collision(COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_CREATURE, begin=...)`. `arbiter.shapes` ainda retorna as duas shapes envolvidas nessa colisão específica (não afeta o fato de ambas terem o mesmo `collision_type` registrado).

## O que precisa ser feito

1. Registrar um segundo handler `space.on_collision(COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_CREATURE, begin=_on_creature_creature_collision)` em `engine.py` (mesmo padrão de BIT-03, handler adicional, não substitui o de comida).
2. No callback: checar as condições de acasalamento (ambas ADULT, ambas `action_mate=True`, sem cooldown, energia suficiente) — se todas satisfeitas, debitar energia de ambos os pais, aplicar cooldown, gerar filho via `organic_crossover` + `mutate_genome`, instanciar novo `Creature(engine, x, y, genome=child_genome)` como `LifeStage.EGG` e adicionar via `engine.add_creature()`.
3. `Creature` precisa de um novo atributo `mate_cooldown` (segundos restantes até poder acasalar de novo), decrementado a cada `update()`.
4. Posição do filho: ponto médio entre os dois pais (simples, evita nascer dentro de uma parede ou sobrepondo demais os pais).

## Perguntas em aberto

- Custo de energia da reprodução (`REPRODUCTION_ENERGY_COST`) e cooldown (`REPRODUCTION_COOLDOWN`) não têm valor definido em nenhum doc — são constantes novas, propostas como valores razoáveis e tunáveis (não bloqueante, fácil de ajustar depois via playtesting).
- Limite de população: não há cap máximo de criaturas hoje (só o "Jardim do Éden" cuida do piso). Reprodução sem controle pode crescer sem limite — fora de escopo desta task adicionar um teto (mencionar como risco conhecido, não resolver aqui).
- Diet/espécie: crossover entre um `herbivore` e um `carnivore` (hoje é só um atributo cosmético/mockado, sem herança genética real) não é tratado — o filho herda `diet` por sorteio simples (50/50) como funcionava seguindo o padrão mockado atual, sem introduzir herança de DNA real (fora de escopo, é um `# TODO` aceitável).
