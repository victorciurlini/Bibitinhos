## Arquivos relevantes

- `backend/simulation/food.py` — `Food.__init__`, hoje `pymunk.Body(body_type=pymunk.Body.STATIC)`
- `backend/simulation/creature.py` — `Creature.__init__`, `mass = 1.0` (local, não exposto como constante)
- `backend/simulation/engine.py` — collision handler `_on_creature_food_collision` (BIT-03), lógica de cap de comida por oásis (BIT-06)

## Conteúdo relevante para a demanda

`Food.body` é `STATIC` (massa infinita, pymunk nunca move) — por isso a comida se comporta "como um muro": uma criatura que colide com ela sofre a resposta elástica normal, mas a comida em si nunca é deslocada, não há troca de momento real. O developer quer física de ação-reação de verdade: comida deve ter massa finita, proporcional a 1% da massa da `Creature` (hoje `mass = 1.0` hardcoded em `creature.py`, não exposta como constante de módulo).

Verificado que nenhuma outra parte do código assume que `food.body.position` fica fixa entre steps:
- `engine.py` (BIT-06) recalcula `food_in_oasis` comparando `f.body.position` contra `oasis.x/y` a cada step — se a comida for empurrada por uma criatura e sair do raio do oásis, ela deixa de contar pro cap daquele oásis (o oásis pode "reabastecer" mais). Efeito colateral aceitável (ainda limitado pelo cap global `MAX_TOTAL_FOOD=50`), não é um bug — é inclusive um comportamento mais realista (comida empurrada se espalha).
- `backend/tests/test_oasis.py` usa `engine.creatures = []` nos testes que checam posição de comida — sem criaturas, nenhuma força atua sobre a comida, então ela fica parada mesmo sendo `DYNAMIC` (Newton: sem força, sem aceleração). Testes não quebram.
- `backend/tests/test_feeding.py` não faz nenhuma asserção sobre `food.body.position` — só sobre `creature.energy`/`food.is_active`/presença em `engine.foods`. O consumo acontece no `begin` do collision handler, disparado no primeiro contato, independente do tipo de corpo — não afetado pela mudança.

## O que precisa ser feito

1. Extrair `CREATURE_MASS = 1.0` como constante de módulo em `creature.py` (hoje é uma variável local dentro de `__init__`), e usá-la no lugar do literal `1.0`.
2. Em `food.py`: importar `CREATURE_MASS` de `simulation.creature` (sem import circular — `creature.py` não importa `food.py`), definir `FOOD_MASS = CREATURE_MASS * 0.01`, e trocar `Food.body` de `pymunk.Body(body_type=pymunk.Body.STATIC)` para um corpo dinâmico: `pymunk.Body(FOOD_MASS, pymunk.moment_for_circle(FOOD_MASS, 0, 5.0))`.
3. Manter `elasticity`/`friction`/`filter`/`collision_type`/`owner` como estão — só o tipo de corpo e a massa mudam.
4. `space.damping = 0.9` (já configurado em `physics.py`) garante que a comida empurrada não desliza pra sempre — desacelera e para, como esperado.

## Perguntas em aberto

Nenhuma — escopo pequeno e isolado, sem ambiguidade técnica (comportamento de `pymunk.Body` dinâmico com massa baixa é padrão, já usado em `creature.py`).
