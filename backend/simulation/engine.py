from simulation.physics import PhysicsEngine, COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD
from simulation.food import Food
from simulation.creature import Creature, LifeStage
from simulation.sensors import compute_vision, VISION_RADIUS, VISION_FOV_DEGREES
from simulation.rtneat_wrapper import organic_crossover, mutate_genome, clone_genome
from simulation.oasis import (
    Oasis,
    MAX_ACTIVE_OASES,
    MAX_TOTAL_OASES,
    OASIS_SPAWN_CHANCE_PER_FRAME,
    OASIS_FOOD_SPAWN_CHANCE,
    MAX_TOTAL_FOOD,
    EDEN_POPULATION_THRESHOLD,
    EDEN_OASIS_RADIUS,
    EDEN_OASIS_TTL,
    EDEN_OASIS_FOOD_CAP,
    EDEN_OASIS_MIN_DISTANCE,
    EDEN_OASIS_MAX_DISTANCE,
)
import math
import random

BRAIN_TICK_INTERVAL = 1 / 10.0
MATING_RADIUS = 150.0  # BIT-22: acasalamento por PROXIMIDADE, nao por colisao exata no mesmo frame
                       # (evento raro demais em espaco continuo esparso). Ambos ainda precisam querer
                       # (action_mate) — o cerebro segue no comando.
                       # Calibracao (passo 9 da spec, degrau 1): 120 dava ~1/run com um seed em 0;
                       # subir para 150 leva a media a ~2.6/run e torna a sexuada recorrente em todos
                       # os 5 seeds testados (0 extincoes, Eden como seguro).
REPRODUCTION_ENERGY_COST = 30.0  # BIT-20: era 50 — recompensa reproduzir (pos-parto sobra 45, sobrevivivel)
REPRODUCTION_COOLDOWN = 10.0
# MIN_ENERGY_TO_MATE removido (BIT-22): substituido por is_fertile. O unico piso de energia no
# acasalamento e a sobrevivencia (energia >= REPRODUCTION_ENERGY_COST, para nao acasalar ate a morte).
MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 100.0  # BIT-22: era 90 — assexuada exige energia cheia
ASEXUAL_REPRODUCTION_ENERGY_COST = 95.0    # BIT-22: era 85 — clonar vira aposta quase suicida (sobra 5)
ASEXUAL_REPRODUCTION_COOLDOWN = 45.0  # BIT-20: era 20 — 4.5x o cooldown sexuado. A clonagem segue viva
                                      # como via de emergencia contra extincao, mas nao pode dominar.

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
                creature.has_eaten = True  # BIT-22: habilita fertilidade (comer antes de acasalar)
                food.consume()
            return True  # deixa a resolucao fisica normal acontecer (elasticity ja configurada nos shapes)

        self.physics.space.on_collision(
            COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD,
            begin=_on_creature_food_collision,
        )

        # BIT-22: o handler de colisao criatura x criatura foi removido — a reproducao sexuada
        # deixou de depender de colisao exata no mesmo frame e passou a ser por PROXIMIDADE (ver
        # step()). A fisica de colisao entre criaturas continua por padrao (shapes tem elasticidade).

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

        # Atualizar Física
        self.physics.step(dt)

        # 1.4. Reproducao sexuada por PROXIMIDADE (BIT-22): dois adultos FERTEIS, ambos querendo
        # acasalar (action_mate), dentro de MATING_RADIUS, fora de cooldown e com energia para
        # sobreviver ao parto -> cruzam. Substitui o antigo handler de colisao (evento raro demais
        # em espaco continuo esparso). O(n^2) sobre adultos vivos — trivial para a populacao-alvo.
        for creature in self.creatures:
            creature.sought_mate_this_frame = False

        sexual_children = []
        alive_adults = [c for c in self.creatures
                        if c.is_alive and c.life_stage == LifeStage.ADULT]
        radius_sq = MATING_RADIUS * MATING_RADIUS
        for i in range(len(alive_adults)):
            a = alive_adults[i]
            if not (a.is_fertile and a.action_mate) or a.reproduction_cooldown > 0:
                continue
            if a.energy < REPRODUCTION_ENERGY_COST:
                continue
            for j in range(i + 1, len(alive_adults)):
                b = alive_adults[j]
                if not (b.is_fertile and b.action_mate) or b.reproduction_cooldown > 0:
                    continue
                if b.energy < REPRODUCTION_ENERGY_COST:
                    continue
                dx = a.body.position.x - b.body.position.x
                dy = a.body.position.y - b.body.position.y
                if dx * dx + dy * dy > radius_sq:
                    continue
                # Cruzam:
                a.sought_mate_this_frame = True
                b.sought_mate_this_frame = True
                a.energy -= REPRODUCTION_ENERGY_COST
                b.energy -= REPRODUCTION_ENERGY_COST
                a.reproduction_cooldown = REPRODUCTION_COOLDOWN
                b.reproduction_cooldown = REPRODUCTION_COOLDOWN
                a.is_fertile = False  # re-conquistar a fertilidade comendo de novo
                b.is_fertile = False
                child_id = self.next_genome_id()
                child_genome = organic_crossover(a.genome, b.genome, child_id, a.config)
                mutate_genome(child_genome, a.config)
                cx = (a.body.position.x + b.body.position.x) / 2
                cy = (a.body.position.y + b.body.position.y) / 2
                sexual_children.append(Creature(self, cx, cy, genome=child_genome))
                break  # 'a' ja acasalou neste frame (cooldown), passa para o proximo adulto
        for child in sexual_children:
            self.add_creature(child)

        # 1.5. Reproducao assexuada: Action_Mate reaproveitado como sinal geral de
        # "quero reproduzir" — se a criatura nao tinha parceiro viavel por perto neste
        # frame mas tem energia de sobra, clona o proprio genoma. Custo e cooldown
        # mais altos que o sexuado: via de emergencia, nao deve ser dominante.
        asexual_children = []
        for creature in self.creatures:
            if not creature.is_alive:
                continue
            if creature.life_stage != LifeStage.ADULT:
                continue
            if creature.sought_mate_this_frame:
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

        # 0.5. Comida apodrece: TTL libera vaga no cap global (MAX_TOTAL_FOOD), sem isso
        # comida orfa de oasis expirados satura o mapa e a renovacao para (BIT-18).
        for food in self.foods:
            food.ttl -= dt
            if food.ttl <= 0 and food.is_active:
                food.consume()

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
                    if len(self.oases) >= MAX_TOTAL_OASES:
                        break
                    # O oasis nasce LONGE do sobrevivente (BIT-20): antes ele nascia em cima da posicao
                    # dele, fazendo chover comida de graca justamente sobre quem ficou parado — o que
                    # fechava o ciclo (parar -> populacao cai -> Eden -> comida gratis -> clonar).
                    # O Eden segue sendo o seguro contra extincao, mas a comida se conquista andando.
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(EDEN_OASIS_MIN_DISTANCE, EDEN_OASIS_MAX_DISTANCE)
                    ox = max(0.0, min(float(self.width), creature.body.position.x + dist * math.cos(angle)))
                    oy = max(0.0, min(float(self.height), creature.body.position.y + dist * math.sin(angle)))
                    self.oases.append(Oasis(
                        ox, oy,
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
