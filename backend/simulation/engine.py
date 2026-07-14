from simulation.physics import PhysicsEngine, COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD
from simulation.food import Food
from simulation.creature import Creature, LifeStage
from simulation.sensors import compute_vision, VISION_RADIUS, VISION_FOV_DEGREES
from simulation.rtneat_wrapper import organic_crossover, mutate_genome, clone_genome
from simulation.oasis import (
    Oasis,
    MAX_ACTIVE_OASES,
    OASIS_SPAWN_CHANCE_PER_FRAME,
    OASIS_FOOD_SPAWN_CHANCE,
    MAX_TOTAL_FOOD,
    EDEN_POPULATION_THRESHOLD,
    EDEN_OASIS_RADIUS,
    EDEN_OASIS_TTL,
    EDEN_OASIS_FOOD_CAP,
)
import random

BRAIN_TICK_INTERVAL = 1 / 10.0
REPRODUCTION_ENERGY_COST = 30.0
REPRODUCTION_COOLDOWN = 10.0
MIN_ENERGY_TO_MATE = 50.0
MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 70.0
ASEXUAL_REPRODUCTION_ENERGY_COST = 50.0
ASEXUAL_REPRODUCTION_COOLDOWN = 20.0  # 2x o cooldown sexuado: via solo nao deve dominar sobre achar parceiro

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
            # Marca "colidiu com outra criatura" independente do resultado abaixo —
            # usado pelo laco de reproducao assexuada para nao disparar quando a via
            # sexuada foi tentada mas falhou por causa do parceiro (nao e "estar sozinha").
            c1.collided_with_creature_this_frame = True
            c2.collided_with_creature_this_frame = True
            if c1.life_stage != LifeStage.ADULT or c2.life_stage != LifeStage.ADULT:
                return True
            if c1.reproduction_cooldown > 0 or c2.reproduction_cooldown > 0:
                return True
            if not (c1.action_mate and c2.action_mate):
                return True
            if c1.energy < MIN_ENERGY_TO_MATE or c2.energy < MIN_ENERGY_TO_MATE:
                return True

            c1.energy -= REPRODUCTION_ENERGY_COST
            c2.energy -= REPRODUCTION_ENERGY_COST
            c1.reproduction_cooldown = REPRODUCTION_COOLDOWN
            c2.reproduction_cooldown = REPRODUCTION_COOLDOWN

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
        self.oases = []
        self._eden_active = False

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
        
        # Reseta a flag de colisao antes da fisica rodar (o handler de colisao
        # criatura x criatura a re-marca durante o physics.step() abaixo).
        for creature in self.creatures:
            creature.collided_with_creature_this_frame = False

        # Atualizar Física
        self.physics.step(dt)

        # 1.5. Reproducao assexuada: Action_Mate reaproveitado como sinal geral de
        # "quero reproduzir" — se a criatura nao encontrou parceiro (colisao) neste
        # frame mas tem energia de sobra, clona o proprio genoma. Custo e cooldown
        # mais altos que o sexuado: via de emergencia, nao deve ser dominante.
        asexual_children = []
        for creature in self.creatures:
            if not creature.is_alive:
                continue
            if creature.life_stage != LifeStage.ADULT:
                continue
            if creature.collided_with_creature_this_frame:
                continue
            if creature.reproduction_cooldown > 0:
                continue
            if not creature.action_mate:
                continue
            if creature.energy < MIN_ENERGY_TO_REPRODUCE_ASEXUALLY:
                continue

            creature.energy -= ASEXUAL_REPRODUCTION_ENERGY_COST
            creature.reproduction_cooldown = ASEXUAL_REPRODUCTION_COOLDOWN

            child_id = self.next_genome_id()
            child_genome = clone_genome(creature.genome, child_id, creature.config)
            mutate_genome(child_genome, creature.config)
            asexual_children.append(
                Creature(self, creature.body.position.x, creature.body.position.y, genome=child_genome)
            )

        for child in asexual_children:
            self.add_creature(child)

        # 1. Ciclo de vida dos oasis: expira os antigos, nasce novos, comida so dentro deles
        for oasis in self.oases:
            oasis.ttl -= dt
        self.oases = [o for o in self.oases if o.ttl > 0]

        if len(self.oases) < MAX_ACTIVE_OASES and random.random() < OASIS_SPAWN_CHANCE_PER_FRAME:
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)
            self.oases.append(Oasis(x, y))

        if len(self.foods) < MAX_TOTAL_FOOD:
            for oasis in self.oases:
                food_in_oasis = sum(
                    1 for f in self.foods
                    if (f.body.position.x - oasis.x) ** 2 + (f.body.position.y - oasis.y) ** 2 <= oasis.radius ** 2
                )
                if food_in_oasis < oasis.food_cap and random.random() < OASIS_FOOD_SPAWN_CHANCE:
                    fx, fy = oasis.random_point_inside()
                    fx = max(0, min(self.width, fx))
                    fy = max(0, min(self.height, fy))
                    self.add_food(Food(self, fx, fy))
                    if len(self.foods) >= MAX_TOTAL_FOOD:
                        break

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

        # 6. Jardim do Eden: fallback de extincao total (populacao == 0, nao coberto pelo README)
        # + regra real do README (populacao < 10, com sobreviventes: oasis denso nas posicoes deles)
        if len(self.creatures) == 0:
            for _ in range(10):
                self.add_creature(Creature(self))
            self._eden_active = False
        elif len(self.creatures) < EDEN_POPULATION_THRESHOLD:
            if not self._eden_active:
                self._eden_active = True
                for creature in self.creatures:
                    self.oases.append(Oasis(
                        creature.body.position.x, creature.body.position.y,
                        radius=EDEN_OASIS_RADIUS, ttl=EDEN_OASIS_TTL, food_cap=EDEN_OASIS_FOOD_CAP,
                    ))
        else:
            self._eden_active = False


    def get_state(self):
        return {
            "time": self.time_elapsed,
            "generation": self.current_generation,
            "width": self.width,
            "height": self.height,
            "vision_radius": VISION_RADIUS,
            "vision_fov_degrees": VISION_FOV_DEGREES,
            "creatures": [c.to_dict() for c in self.creatures],
            "foods": [f.to_dict() for f in self.foods],
            "oases": [o.to_dict() for o in self.oases]
        }
