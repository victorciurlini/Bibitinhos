import math
import random

class Creature:
    def __init__(self, engine, x=None, y=None):
        self.engine = engine
        self.x = x if x is not None else random.uniform(0, engine.width)
        self.y = y if y is not None else random.uniform(0, engine.height)
        self.rotation = random.uniform(0, math.pi * 2)
        
        # Atributos baseados em "DNA" (mockados por enquanto)
        self.speed = 50.0
        self.size = 10.0
        self.energy = 100.0
        self.max_energy = 100.0
        self.diet = 'herbivore' # ou 'carnivore'
        
        self.is_alive = True
        
    def update(self, dt, engine):
        if not self.is_alive:
            return

        # Movimento básico: sempre para frente
        self.x += math.cos(self.rotation) * self.speed * dt
        self.y += math.sin(self.rotation) * self.speed * dt
        
        # Bouncing nas bordas
        if self.x < 0 or self.x > engine.width:
            self.rotation = math.pi - self.rotation
            self.x = max(0, min(self.x, engine.width))
        if self.y < 0 or self.y > engine.height:
            self.rotation = -self.rotation
            self.y = max(0, min(self.y, engine.height))
            
        # Consumo de energia
        self.energy -= dt * (self.speed * 0.1 + self.size * 0.05)
        if self.energy <= 0:
            self.is_alive = False
            
    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "radius": self.size,
            "color": "#00ff00" if self.diet == "herbivore" else "#ff0000",
            "energy": self.energy,
            "diet": self.diet
        }
