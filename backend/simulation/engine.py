from simulation.physics import PhysicsEngine
from simulation.food import Food
from simulation.creature import Creature
import random

class SimulationEngine:
    def __init__(self):
        self.physics = PhysicsEngine()
        self.creatures = []
        self.foods = []
        self.width = self.physics.map_width
        self.height = self.physics.map_height
        self.current_generation = 1
        self.time_elapsed = 0

    def add_creature(self, creature):
        self.creatures.append(creature)

    def add_food(self, food):
        self.foods.append(food)

    def step(self, dt):
        """Atualiza um frame da simulação."""
        self.time_elapsed += dt
        
        # Atualizar Física
        self.physics.step(dt)
        
        # 1. Spawn aleatório de comida
        if len(self.foods) < 50:
            if random.random() < 0.05: # 5% chance por frame
                x = random.uniform(0, self.width)
                y = random.uniform(0, self.height)
                self.add_food(Food(self, x, y))

        # 2. Atualizar todas as criaturas
        for creature in self.creatures:
            creature.update(dt, self)

        # 3. Remover criaturas mortas
        alive_creatures = []
        for c in self.creatures:
            if c.is_alive:
                alive_creatures.append(c)
            else:
                c.die()
        self.creatures = alive_creatures

        # 4. Remover comida consumida
        self.foods = [f for f in self.foods if f.is_active]

        # 5. Respawn (Jardim do Éden)
        if len(self.creatures) == 0:
            for _ in range(10):
                self.add_creature(Creature(self))


    def get_state(self):
        return {
            "time": self.time_elapsed,
            "generation": self.current_generation,
            "width": self.width,
            "height": self.height,
            "creatures": [c.to_dict() for c in self.creatures],
            "foods": [f.to_dict() for f in self.foods]
        }
