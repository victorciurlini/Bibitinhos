## Arquivos relevantes

- `backend/simulation/creature.py` — `Creature.shape` sem `collision_type` definido (só `categories` via `ShapeFilter`)
- `backend/simulation/food.py` — `Food.shape` idem; `consume()` já existe e faz `is_active=False` + tenta remover do space (com try/except já defensivo)
- `backend/simulation/physics.py` — `COLLISION_CATEGORY_CREATURE=1`, `COLLISION_CATEGORY_FOOD=2`, `COLLISION_CATEGORY_WALL=4`; `PhysicsEngine.step()` só chama `space.step(dt)`, nenhum handler registrado
- `backend/simulation/engine.py` — `SimulationEngine.__init__` instancia `PhysicsEngine()`; nenhuma referência cruzada de shape→objeto Python hoje

## Conteúdo relevante para a demanda

### API de collision handler validada ao vivo (pymunk 7.2.0)
Pymunk 7.2.0 **não tem** `space.add_collision_handler` (API antiga). O método atual é:
```python
space.on_collision(
    collision_type_a, collision_type_b,
    begin=fn, pre_solve=fn, post_solve=fn, separate=fn, data=None,
)
```
Callbacks recebem `(arbiter, space, data)`. `arbiter.shapes` retorna as duas shapes **na ordem em que os `collision_type` foram registrados** (`shapes[0]` é sempre do tipo `collision_type_a`, `shapes[1]` do tipo `collision_type_b`).

Isso **exige** que `shape.collision_type` esteja setado nos shapes de `Creature` e `Food` — hoje nenhum dos dois define isso (só `categories`, que é usado para filtro físico via `ShapeFilter`, não para roteamento de handler).

### Back-reference shape → objeto Python
Testado ao vivo: `pymunk.Shape` aceita atribuição de atributo Python arbitrário (`shape.owner = self` funciona, não é bloqueado pela extensão C). Isso permite, dentro do callback, recuperar a instância `Food`/`Creature` a partir da shape (`arbiter.shapes[0].owner`) sem precisar de um dicionário auxiliar de lookup.

### Remoção de shape/body durante o step
Docstring de `space.add_post_step_callback` (pymunk 7.2.0): *"This function was more useful with earlier versions of pymunk where you weren't allowed to use the add and remove methods on the space during a simulation step. But this function is still available..."* — confirma que, na versão instalada, `space.remove()` **pode** ser chamado diretamente dentro do callback `begin`, sem precisar de post-step. `Food.consume()` já faz isso hoje (com try/except defensivo cobrindo `KeyError`/`Exception` genérica), então pode ser reaproveitado como está.

## O que precisa ser feito

1. Definir `shape.collision_type` em `Creature.__init__` e `Food.__init__`, reaproveitando as constantes já existentes em `physics.py` (`COLLISION_CATEGORY_CREATURE`/`COLLISION_CATEGORY_FOOD`) — mesmo valor inteiro, mas agora também usado como `collision_type` (namespace diferente do `categories`, sem conflito).
2. Adicionar back-reference: `self.shape.owner = self` em ambas as classes, para o callback conseguir achar o objeto Python a partir da shape do Arbiter.
3. Registrar `space.on_collision(COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD, begin=...)` — melhor lugar é `PhysicsEngine.__init__` (mesmo módulo que já cria o space e as paredes) ou em `SimulationEngine.__init__` logo após instanciar `self.physics` (mais fácil de importar `Food.consume`/energia sem import circular, já que `physics.py` não conhece `Food`/`Creature` hoje — importar lá criaria acoplamento novo. Melhor registrar em `engine.py`, que já importa `Food`/`Creature`).
4. No callback `begin`: pegar as duas shapes via `arbiter.shapes`, resolver `creature = shapes[0].owner`, `food = shapes[1].owner`; se `food.is_active`: somar `food.energy_value` a `creature.energy` (respeitando `creature.max_energy`, cap para não passar do teto) e chamar `food.consume()`.
5. Decidir resposta física da colisão (bounce vs. atravessar): fora do escopo estrito de "comer" funcionar — pode manter o comportamento físico padrão (elasticidade já configurada em ambos os shapes) sem mexer em `arbiter.process_collision`. Não é bloqueante para o critério de aceite (energia é transferida independente do resultado físico do encontro).

## Perguntas em aberto

- Cap de energia ao comer: `creature.energy` deve ser limitado a `creature.max_energy` (não ultrapassar), ou pode "estocar" excesso? Proponho cap simples (`min(creature.energy + food.energy_value, creature.max_energy)`), mais realista e evita valores fora do range usado em `Energy_Level` (input 9 do cérebro, BIT-02).
- Diet (`herbivore`/`carnivore`, já existe em `Creature`) não tem nenhuma regra hoje limitando quem come o quê — todas as criaturas comem `Food` igual. Diferenciação de dieta (ex. carnívoro comendo outra criatura) está fora do escopo desta task — mencionar como possível task futura, não implementar aqui.
