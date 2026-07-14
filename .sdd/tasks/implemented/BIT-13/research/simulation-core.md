## Arquivos relevantes

- `backend/simulation/sensors.py` — `compute_vision()`, retorna hoje 9 floats binários (0.0/1.0), sem distinguir tipo de vizinho
- `backend/simulation/creature.py` — `Creature.think()` consome `self.vision` como os primeiros 9 inputs da rede; `energy`, `max_energy`, `life_stage` disponíveis no próprio objeto
- `backend/simulation/physics.py` — `COLLISION_CATEGORY_CREATURE = 1`, `COLLISION_CATEGORY_FOOD = 2`, `COLLISION_CATEGORY_WALL = 4`; paredes (`create_space()`) **não** setam `.collision_type` (default do pymunk)
- `backend/simulation/rtneat_wrapper.py` — docstring do contrato de I/O do NEAT (`Visual_Sectors`, índices 0-8)
- `backend/simulation/neat_config.ini` — `num_inputs = 16`, `num_outputs = 4`
- `backend/tests/test_sensors.py` — testes atuais de `compute_vision()`, todos assumem energia padrão (100.0, cheia) e valor binário 1.0

## Conteúdo relevante para a demanda

### Vision atual é "cega" a tipo (gap confirmado)

```python
def compute_vision(creature, engine):
    ...
    for shape in shapes:
        if shape is creature.shape:
            continue
        ...
        vision[index] = 1.0   # qualquer vizinho (comida OU criatura) vira 1.0, sem diferenciação
    return vision
```

Não há como a rede neural saber, hoje, se um cone contém comida ou outra criatura — pré-requisito ausente para priorizar diferente conforme fome/energia.

### Bug latente confirmado: paredes não são filtradas

`space.bb_query(bb, pymunk.ShapeFilter())` retorna qualquer shape na bounding box, incluindo os 4 segmentos de parede do mapa (`physics.py`, `create_space()`). Hoje isso é inofensivo (parede vira só mais um "1.0"), mas qualquer checagem de tipo baseada em `shape.owner` quebraria perto das bordas do mapa, pois paredes não têm `.owner` (`AttributeError`).

### Mecanismo de distinção de tipo, validado ao vivo

`Creature.shape.collision_type = COLLISION_CATEGORY_CREATURE` (1) e `Food.shape.collision_type = COLLISION_CATEGORY_FOOD` (2) já são setados na criação de cada shape. Paredes nunca setam `.collision_type`, então mantêm o default do pymunk. Validado no venv real do projeto:

```
default collision_type: 0
COLLISION_CATEGORY_CREATURE=1 COLLISION_CATEGORY_FOOD=2 COLLISION_CATEGORY_WALL=4
```

Ou seja, `shape.collision_type` já distingue os 3 casos (comida=2, criatura=1, parede/outro=0) sem precisar importar `Creature`/`Food` em `sensors.py` (evita qualquer risco de import circular) e sem tocar `neat_config.ini`.

### Testes existentes que quebram com a mudança

`test_sensors.py::test_food_directly_ahead_activates_cone_zero` cria a criatura com energia padrão (100.0 = cheia). Com a nova fórmula (sinal de comida = fome = `1 - energy/max_energy`), uma criatura saciada teria fome = 0.0 → sinal 0.0, não mais 1.0. Os testes precisam setar `creature.energy` explicitamente para valores que produzam a magnitude esperada (ex.: `energy = 0.0` → fome = 1.0, reproduz a asserção antiga numericamente).

## O que precisa ser feito

1. `sensors.py`: para cada shape encontrado, ler `shape.collision_type` em vez de assumir binário. Ignorar (`continue`) qualquer shape cujo `collision_type` não seja `COLLISION_CATEGORY_FOOD` nem `COLLISION_CATEGORY_CREATURE` (cobre paredes e qualquer objeto futuro sem tipo definido) — corrige o bug latente das paredes.
2. Calcular `hunger = 1.0 - min(creature.energy / creature.max_energy, 1.0)` e `mate_drive = (creature.energy / creature.max_energy) if creature.life_stage == LifeStage.ADULT else 0.0` (precisa de `creature.life_stage`, já disponível no objeto passado).
3. Acumular por setor, com comida tendo prioridade sobre criatura quando ambos caem no mesmo setor (ver "Contratos técnicos" na spec para a regra exata de precedência).
4. Atualizar a docstring do contrato de I/O em `rtneat_wrapper.py` (`Visual_Sectors`) para descrever a nova semântica com sinal — `num_inputs` continua 16, `neat_config.ini` não muda.
5. Atualizar `test_sensors.py` para os novos valores esperados (fome/mate_drive dependem de energia explícita, não mais fixos em 1.0).

## Perguntas em aberto

Nenhuma — fórmula de sinal (comida positiva ponderada por fome, criatura negativa ponderada por energia×maturidade ADULT) já confirmada com o developer; mecanismo de distinção de tipo via `collision_type` validado ao vivo.
