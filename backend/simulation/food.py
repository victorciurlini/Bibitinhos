import pymunk

from simulation.physics import COLLISION_CATEGORY_FOOD

class Food:
    def __init__(self, engine, x, y, energy_value=20.0):
        self.engine = engine
        self.energy_value = energy_value
        self.is_active = True
        
        # Pymunk Physics integration
        # Usar STATIC body para comida
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)
        
        self.shape = pymunk.Circle(self.body, 5.0)
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
            "color": "#ffff00" # Amarelo para representar comida
        }
