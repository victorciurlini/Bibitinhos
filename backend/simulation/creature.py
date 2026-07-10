import math
import random
import pymunk
from enum import Enum

class LifeStage(Enum):
    EGG = 0
    JUVENILE = 1
    ADULT = 2
    ELDER = 3

class Creature:
    def __init__(self, engine, x=None, y=None):
        self.engine = engine
        
        # Pymunk Physics integration
        mass = 1.0
        moment = pymunk.moment_for_circle(mass, 0, 10.0)
        self.body = pymunk.Body(mass, moment)
        
        start_x = x if x is not None else random.uniform(0, engine.width)
        start_y = y if y is not None else random.uniform(0, engine.height)
        self.body.position = (start_x, start_y)
        self.body.angle = random.uniform(0, math.pi * 2)
        
        # Collision categories should match physics.py if available, 1 for CREATURE
        self.shape = pymunk.Circle(self.body, 10.0)
        self.shape.elasticity = 0.5
        self.shape.friction = 0.5
        self.shape.filter = pymunk.ShapeFilter(categories=1)
        
        # We assume engine.physics.space exists; add body and shape
        if hasattr(engine, 'physics') and engine.physics is not None:
            engine.physics.space.add(self.body, self.shape)
        
        # Atributos baseados em "DNA" (mockados por enquanto)
        self.speed = 50.0
        self.size = 10.0
        self.energy = 100.0
        self.max_energy = 100.0
        self.diet = 'herbivore' # ou 'carnivore'
        
        self.is_alive = True
        self.life_stage = LifeStage.EGG
        self.age = 0.0
        self.vision = [0.0] * 9
        
    def update(self, dt, engine):
        if not self.is_alive:
            return

        self.age += dt
        
        # Atualizar estágios de vida baseados na idade (mockado)
        if self.age > 30:
            self.life_stage = LifeStage.ELDER
        elif self.age > 10:
            self.life_stage = LifeStage.ADULT
        elif self.age > 2:
            self.life_stage = LifeStage.JUVENILE

        # Movimento básico: impulso para frente localmente
        # apply_impulse_at_local_point takes (impulse_x, impulse_y) relative to body
        if self.life_stage != LifeStage.EGG:
            forward_impulse = (self.speed * dt, 0)
            self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
            
        # Consumo de energia
        self.energy -= dt * (self.speed * 0.1 + self.size * 0.05)
        if self.energy <= 0:
            self.is_alive = False
            
    def die(self):
        self.is_alive = False
        if hasattr(self.engine, 'physics') and self.engine.physics is not None:
            if self.body in self.engine.physics.space.bodies:
                self.engine.physics.space.remove(self.body, self.shape)
            
    def to_dict(self):
        return {
            "x": self.body.position.x,
            "y": self.body.position.y,
            "rotation": self.body.angle,
            "radius": self.size,
            "color": "#00ff00" if self.diet == "herbivore" else "#ff0000",
            "energy": self.energy,
            "diet": self.diet,
            "life_stage": self.life_stage.name,
            "vision": self.vision
        }
