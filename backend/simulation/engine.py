from simulation.physics import PhysicsEngine, COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD
from simulation.food import Food
from simulation.creature import Creature, LifeStage
from simulation.sensors import compute_vision
from simulation.rtneat_wrapper import organic_crossover, mutate_genome
import random

BRAIN_TICK_INTERVAL = 1 / 10.0
REPRODUCTION_ENERGY_COST = 30.0
REPRODUCTION_COOLDOWN = 10.0
MIN_ENERGY_TO_MATE = 50.0

class SimulationEngine:
    def __init__(self):
        self.physics = PhysicsEngine()

        def _on_creature_food_collision(arbiter, space, data):
            """Handler de colisao criatura x comida: transfere energia e consome a comida."""
            creature_shape, food_shape = arbiter.shapes
            creature = creature_shape.owner
            food = food_shape.owner
            if food.is_active and creature.is_alive:
                creature.energy = min(creature.energy + food.energy_value, creature.max_energy)
                food.consume()
            return True  # deixa a resolucao fisica normal acontecer (elasticity ja configurada nos shapes)

        self.physics.space.on_collision(
            COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD,
            begin=_on_creature_food_collision,
        )

        def _on_creature_creature_collision(arbiter, space, data):
            """Handler de colisao criatura x criatura: reproducao sexuada via Action_Mate."""
            shape_a, shape_b = arbiter.shapes
            c1, c2 = shape_a.owner, shape_b.owner
            if not (c1.is_alive and c2.is_alive):
                return True
            if c1.life_stage != LifeStage.ADULT or c2.life_stage != LifeStage.ADULT:
                return True
            if c1.mate_cooldown > 0 or c2.mate_cooldown > 0:
                return True
            if not (c1.action_mate and c2.action_mate):
                return True
            if c1.energy < MIN_ENERGY_TO_MATE or c2.energy < MIN_ENERGY_TO_MATE:
                return True

            c1.energy -= REPRODUCTION_ENERGY_COST
            c2.energy -= REPRODUCTION_ENERGY_COST
            c1.mate_cooldown = REPRODUCTION_COOLDOWN
            c2.mate_cooldown = REPRODUCTION_COOLDOWN

            child_id = self.next_genome_id()
            child_genome = organic_crossover(c1.genome, c2.genome, child_id, c1.config)
            mutate_genome(child_genome, c1.config)

            child_x = (c1.body.position.x + c2.body.position.x) / 2
            child_y = (c1.body.position.y + c2.body.position.y) / 2
            child = Creature(self, child_x, child_y, genome=child_genome)
            self.add_creature(child)
            return True

        self.physics.space.on_collision(
            COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_CREATURE,
            begin=_on_creature_creature_collision,
        )

        self.creatures = []
        self.foods = []
        self.width = self.physics.map_width
        self.height = self.physics.map_height
        self.current_generation = 1
        self.time_elapsed = 0
        self._brain_accumulator = 0.0
        self._next_genome_id = 0

    def add_creature(self, creature):
        self.creatures.append(creature)

    def add_food(self, food):
        self.foods.append(food)

    def next_genome_id(self):
        """Contador monotonico de genome id, usado para criar genomas zero (Gen 0)."""
        self._next_genome_id += 1
        return self._next_genome_id

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

        # 2. Brain tick (10 FPS, dissociado do tick de fisica): atualiza visao
        self._brain_accumulator += dt
        if self._brain_accumulator >= BRAIN_TICK_INTERVAL:
            self._brain_accumulator -= BRAIN_TICK_INTERVAL
            for creature in self.creatures:
                if creature.is_alive:
                    creature.vision = compute_vision(creature, self)
                    creature.think(self)

        # 3. Atualizar todas as criaturas
        for creature in self.creatures:
            creature.update(dt, self)

        # 4. Remover criaturas mortas
        alive_creatures = []
        for c in self.creatures:
            if c.is_alive:
                alive_creatures.append(c)
            else:
                c.die()
        self.creatures = alive_creatures

        # 5. Remover comida consumida
        self.foods = [f for f in self.foods if f.is_active]

        # 6. Respawn (Jardim do Éden)
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
