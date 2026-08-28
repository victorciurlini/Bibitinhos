# Research: Backend — Serialização de Criaturas e Dados Cinéticos

## Arquivos relevantes
- `backend/simulation/creature.py` — classe `Creature`, `to_dict()`, `compute_visual_scale`, `compute_life_color`
- `backend/simulation/engine.py` — `SimulationEngine.get_state()` (agrega criaturas para broadcast)
- `backend/main.py` — loop de broadcast WebSocket (30 FPS)

## Campos atuais em Creature.to_dict() (linhas 244-266)
```python
{
    "id": self.id,
    "x": self.body.position.x,
    "y": self.body.position.y,
    "rotation": self.body.angle,              # radianos, direção que olha
    "radius": self.size * compute_visual_scale(age, energy, max_energy),
    "color": compute_life_color(age, energy, max_energy),
    "energy": self.energy,
    "max_energy": self.max_energy,
    "age": self.age,
    "diet": self.diet,
    "life_stage": self.life_stage.name,       # EGG | JUVENILE | ADULT | ELDER
    "reproduction_cooldown": self.reproduction_cooldown,
    "vision": [...],                           # 9 sensores visuais
    "motor_forward": self.motor_forward,       # [0, 1]
    "motor_torque": self.motor_torque,         # [-1, 1]
    "action_mate": self.action_mate,
    "action_grab_drop": self.action_grab_drop,
    "generation": self.generation,
    "food_eaten": self.food_eaten,
    "children_count": self.children_count,
}
```

## Velocity / Speed no backend
- `self.body.velocity` (Pymunk Vec2d) está disponível na criatura
- `self.body.velocity.length` = magnitude escalar (px/s)
- Já usado internamente:
  - Linha 172: `self.body.velocity.length / KINETIC_LINEAR_NORM` (feedback neural)
  - Linha 207: `self.body.velocity.length / MOVEMENT_REFERENCE_SPEED` (fator de movimento)
- `MOVEMENT_REFERENCE_SPEED = 35.0` px/s — threshold de "está explorando"
- **NÃO é enviado no to_dict() atualmente**

## O que precisa ser feito
Adicionar ao `to_dict()` em `creature.py`:
```python
"speed": self.body.velocity.length,  # magnitude em px/s, para animação da cauda
```

Isso basta para a animação — direção do girino já vem via `rotation`.

## Testes a verificar
- `backend/tests/test_creature_life_visuals.py` — testa `to_dict()` (blast radius)
- `backend/tests/test_rtneat_wrapper.py` — pode usar `to_dict()` indiretamente
- Se algum teste faz `assertIn("speed", d)` ou compara chaves exatas do dict, precisa ser atualizado
