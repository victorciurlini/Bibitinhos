class SimulationEngine:
    def __init__(self):
        self.creatures = []
        self.foods = []
        self.width = 800
        self.height = 600
        self.current_generation = 1
        self.time_elapsed = 0

    def add_creature(self, creature):
        self.creatures.append(creature)

    def add_food(self, food):
        self.foods.append(food)

    def step(self, dt):
        """Atualiza um frame da simulação."""
        self.time_elapsed += dt
        
        # 1. Spawn aleatório de comida
        if len(self.foods) < 50:
            # TODO: add chance of spawning food
            pass

        # 2. Atualizar todas as criaturas
        for creature in self.creatures:
            creature.update(dt, self)

        # 3. Remover criaturas mortas
        self.creatures = [c for c in self.creatures if c.is_alive]

        # 4. Remover comida consumida
        self.foods = [f for f in self.foods if f.is_active]

    def get_state(self):
        return {
            "time": self.time_elapsed,
            "generation": self.current_generation,
            "creatures": [c.to_dict() for c in self.creatures],
            "foods": [f.to_dict() for f in self.foods]
        }
