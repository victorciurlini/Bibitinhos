import pymunk

from simulation.physics import COLLISION_CATEGORY_FOOD
from simulation.creature import CREATURE_MASS

FOOD_RADIUS = 5.0
FOOD_MASS = CREATURE_MASS * 0.01  # 1% da massa da Creature: acao-reacao real, nao se comporta como parede
FOOD_TTL = 30.0  # segundos ate a comida apodrecer e liberar vaga no cap global
FOOD_ENERGY_VALUE = 32.0  # BIT-22: era 40.0 (BIT-20 subira de 20.0) — recompensa por comer
                          # (tunavel em runtime, BIT-23)

class Food:
    def __init__(self, engine, x, y, energy_value=None):
        # Sentinel None em vez de default literal: default de funcao e congelado no `def`, entao
        # patchear FOOD_ENERGY_VALUE em runtime (BIT-23) nao afetaria comida nova se fosse default.
        self.engine = engine
        self.energy_value = FOOD_ENERGY_VALUE if energy_value is None else energy_value
        self.is_active = True
        self.ttl = FOOD_TTL
        self.max_ttl = FOOD_TTL
        self.is_held = False

        # Pymunk Physics integration: corpo dinamico leve, permite ser empurrada
        moment = pymunk.moment_for_circle(FOOD_MASS, 0, FOOD_RADIUS)
        self.body = pymunk.Body(FOOD_MASS, moment)
        self.body.position = (x, y)

        self.shape = pymunk.Circle(self.body, FOOD_RADIUS)
        self.shape.elasticity = 0.5
        self.shape.friction = 0.5
        self.shape.filter = pymunk.ShapeFilter(categories=COLLISION_CATEGORY_FOOD)
        self.shape.collision_type = COLLISION_CATEGORY_FOOD
        self.shape.owner = self

        if hasattr(engine, 'physics') and engine.physics is not None:
            engine.physics.space.add(self.body, self.shape)
            
    def consume(self):
        self.is_active = False
        if hasattr(self.engine, 'physics') and self.engine.physics is not None:
            try:
                self.engine.physics.space.remove(self.body, self.shape)
            except KeyError:
                pass
            except Exception:
                pass

    def to_dict(self):
        return {
            "x": self.body.position.x,
            "y": self.body.position.y,
            "energy_value": self.energy_value,
            "radius": self.shape.radius,
            "color": "#ffff00",
            "held": self.is_held,
        }
