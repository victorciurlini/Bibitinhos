from simulation.physics import PhysicsEngine, COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD
from simulation.food import Food
from simulation.creature import Creature, LifeStage
from simulation.sensors import compute_vision, VISION_RADIUS, VISION_FOV_DEGREES
from simulation.rtneat_wrapper import organic_crossover, mutate_genome, clone_genome, load_neat_config
from simulation.params import get_params
from simulation.metrics import compute_metrics, METRICS_SAMPLE_INTERVAL, METRICS_HISTORY_MAX
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
from collections import deque
import math
import random

BRAIN_TICK_INTERVAL = 1 / 10.0
MATING_RADIUS = 200.0  # BIT-35: era 150 — encontros mais frequentes em mapa esparso
REPRODUCTION_ENERGY_COST = 20.0  # BIT-35: era 30 — mais oportunidades pós-parto
REPRODUCTION_COOLDOWN = 6.0      # BIT-35: era 10 — menos tempo entre acasalamentos
# MIN_ENERGY_TO_MATE removido (BIT-22): substituido por is_fertile. O unico piso de energia no
# acasalamento e a sobrevivencia (energia >= REPRODUCTION_ENERGY_COST, para nao acasalar ate a morte).
MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 100.0  # BIT-22: era 90 — assexuada exige energia cheia
ASEXUAL_REPRODUCTION_ENERGY_COST = 95.0    # BIT-22: era 85 — clonar vira aposta quase suicida (sobra 5)
ASEXUAL_REPRODUCTION_COOLDOWN = 45.0  # BIT-20: era 20 — 4.5x o cooldown sexuado. A clonagem segue viva
                                      # como via de emergencia contra extincao, mas nao pode dominar.

# BIT-24: velocidades de tempo permitidas (controle interativo). Nunca aumentamos o dt do step;
# a aceleracao acontece por SUBSTEPS de dt fixo (ver main.simulation_loop) — estabilidade do Pymunk
# e economia de energia dependem do dt constante.
ALLOWED_SPEEDS = (0.5, 1.0, 2.0, 4.0, 8.0, 50.0)

HALL_OF_FAME_SIZE = 20              # BIT-35: era 12 — mais diversidade genética preservada
HALL_OF_FAME_CHILDREN_WEIGHT = 20.0 # peso de cada filho no proxy de fitness (≈20 s de vida)
HALL_OF_FAME_FOOD_WEIGHT = 1.0      # BIT-35: peso por comida ingerida no score do HoF

# BIT-35: pressão adaptativa de população — multiplica food spawn chance pela população atual.
# pop < LOW → comida abundante (suporte à recuperação); pop > HIGH → seleção natural mais intensa.
LOW_POP_FOOD_THRESHOLD = 15
HIGH_POP_FOOD_THRESHOLD = 50
FOOD_MULTIPLIER_LOW_POP = 1.5
FOOD_MULTIPLIER_HIGH_POP = 0.75

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
                creature.food_eaten += 1   # BIT-30: contador de linhagem
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

        # BIT-26: metricas populacionais. Contadores acumulados desde o boot do engine
        # (so reproducao conta como nascimento — respawn do Eden nao) e historico amostrado
        # a cada METRICS_SAMPLE_INTERVAL segundos simulados, com cap no proprio deque.
        self.births_total = 0
        self.deaths_total = 0
        self.metrics_history = deque(maxlen=METRICS_HISTORY_MAX)
        self._metrics_accumulator = 0.0

        # BIT-30: linhagem. extinctions_total conta resets completos (populacao zerou);
        # _lifespan_sum acumula idades dos mortos para calcular avg_lifespan = sum/deaths_total.
        self.extinctions_total = 0
        self._lifespan_sum = 0.0

        # BIT-31: hall of fame — lista ordenada desc. por score, cap HALL_OF_FAME_SIZE.
        # Cada entrada: {"score": float, "genome": DefaultGenome, "generation": int}.
        self.hall_of_fame = []

        # BIT-24: controle interativo de tempo e arrasto.
        self.paused = False
        self.speed = 1.0
        self._held_creature = None
        self._drag_target = None

    def set_time_control(self, paused=None, speed=None):
        """Ajusta pausa/velocidade. Valores invalidos de speed sao ignorados (no-op) — inclusive
        nao-numericos (ex: cliente adulterado mandando "abc"/lista), sem derrubar a conexao."""
        if paused is not None:
            self.paused = bool(paused)
        if speed is not None:
            try:
                speed = float(speed)
            except (TypeError, ValueError):
                return
            if speed in ALLOWED_SPEEDS:
                self.speed = speed

    def get_creature_by_id(self, creature_id):
        for c in self.creatures:
            if c.id == creature_id:
                return c
        return None

    def start_drag(self, creature_id):
        creature = self.get_creature_by_id(creature_id)
        if creature is None or not creature.is_alive:
            return False
        self._held_creature = creature
        self._drag_target = (creature.body.position.x, creature.body.position.y)
        return True

    def drag_to(self, x, y):
        """Move a criatura segurada. Aplica imediatamente (funciona tambem com a simulacao
        pausada, ja que o broadcast continua) e guarda o alvo para o re-pin de cada step."""
        if self._held_creature is None:
            return
        tx = max(0.0, min(float(self.width), float(x)))
        ty = max(0.0, min(float(self.height), float(y)))
        self._drag_target = (tx, ty)
        self._held_creature.body.position = self._drag_target
        self._held_creature.body.velocity = (0, 0)

    def end_drag(self):
        self._held_creature = None
        self._drag_target = None

    def add_creature(self, creature):
        self.creatures.append(creature)

    def add_food(self, food):
        self.foods.append(food)

    def next_genome_id(self):
        """Contador monotonico de genome id, usado para criar genomas zero (Gen 0)."""
        self._next_genome_id += 1
        return self._next_genome_id

    def _record_in_hall_of_fame(self, creature):
        score = (creature.age
                 + HALL_OF_FAME_CHILDREN_WEIGHT * creature.children_count
                 + HALL_OF_FAME_FOOD_WEIGHT * creature.food_eaten)  # BIT-35: inclui caça de comida
        if len(self.hall_of_fame) < HALL_OF_FAME_SIZE or score > self.hall_of_fame[-1]["score"]:
            entry = {
                "score": score,
                "genome": clone_genome(creature.genome, creature.genome.key, creature.config),
                "generation": creature.generation,
            }
            self.hall_of_fame.append(entry)
            self.hall_of_fame.sort(key=lambda e: e["score"], reverse=True)
            del self.hall_of_fame[HALL_OF_FAME_SIZE:]

    def _compute_food_multiplier(self) -> float:
        """BIT-35: homeostase ecológica — ajusta densidade de comida pela população atual."""
        pop = len(self.creatures)
        if pop < LOW_POP_FOOD_THRESHOLD:
            return FOOD_MULTIPLIER_LOW_POP
        elif pop > HIGH_POP_FOOD_THRESHOLD:
            return FOOD_MULTIPLIER_HIGH_POP
        return 1.0

    def _spawn_from_hall_of_fame(self, count):
        config = load_neat_config()
        spawned = []
        for i in range(count):
            entry = self.hall_of_fame[i % len(self.hall_of_fame)]
            child_id = self.next_genome_id()
            genome = clone_genome(entry["genome"], child_id, config)
            mutate_genome(genome, config)
            spawned.append(Creature(self, genome=genome, generation=entry["generation"]))
        return spawned

    def step(self, dt):
        """Atualiza um frame da simulação."""
        self.time_elapsed += dt

        # BIT-24: re-fixar a criatura segurada imediatamente antes da fisica — senao o motor dela
        # continuaria aplicando impulsos e ela escaparia da mao. Se morreu, solta.
        if self._held_creature is not None:
            if not self._held_creature.is_alive:
                self.end_drag()
            else:
                self._held_creature.body.position = self._drag_target
                self._held_creature.body.velocity = (0, 0)

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
                        if c.is_alive and c.life_stage in (LifeStage.ADULT, LifeStage.ELDER)]
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
                a.children_count += 1  # BIT-30
                b.children_count += 1
                child_id = self.next_genome_id()
                child_genome = organic_crossover(a.genome, b.genome, child_id, a.config)
                mutate_genome(child_genome, a.config)
                cx = (a.body.position.x + b.body.position.x) / 2
                cy = (a.body.position.y + b.body.position.y) / 2
                child_gen = max(a.generation, b.generation) + 1
                sexual_children.append(Creature(self, cx, cy, genome=child_genome, generation=child_gen))
                break  # 'a' ja acasalou neste frame (cooldown), passa para o proximo adulto
        for child in sexual_children:
            self.add_creature(child)
        self.births_total += len(sexual_children)

        # 1.5. Reproducao assexuada: Action_Mate reaproveitado como sinal geral de
        # "quero reproduzir" — se a criatura nao tinha parceiro viavel por perto neste
        # frame mas tem energia de sobra, clona o proprio genoma. Custo e cooldown
        # mais altos que o sexuado: via de emergencia, nao deve ser dominante.
        asexual_children = []
        for creature in self.creatures:
            if not creature.is_alive:
                continue
            if creature.life_stage not in (LifeStage.ADULT, LifeStage.ELDER):
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
            creature.children_count += 1  # BIT-30

            child_id = self.next_genome_id()
            child_genome = clone_genome(creature.genome, child_id, creature.config)
            mutate_genome(child_genome, creature.config)
            asexual_children.append(
                Creature(self, creature.body.position.x, creature.body.position.y,
                         genome=child_genome, generation=creature.generation + 1)
            )

        for child in asexual_children:
            self.add_creature(child)
        self.births_total += len(asexual_children)

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
            _food_mult = self._compute_food_multiplier()  # BIT-35: homeostase adaptativa
            for oasis in self.oases:
                food_in_oasis = sum(
                    1 for f in self.foods
                    if (f.body.position.x - oasis.x) ** 2 + (f.body.position.y - oasis.y) ** 2 <= oasis.radius ** 2
                )
                if food_in_oasis < oasis.food_cap and random.random() < OASIS_FOOD_SPAWN_CHANCE * _food_mult:
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
            # Ovo e dormante: sem visao e sem think, coerente com motor/metabolismo zero do estagio.
            # A visao so passa a existir no bibite nascido (JUVENILE+), primeiro brain tick pos-hatch.
            for creature in self.creatures:
                if creature.is_alive and creature.life_stage != LifeStage.EGG:
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
                self._lifespan_sum += c.age  # BIT-30: acumula antes de die() zerar estado
                self._record_in_hall_of_fame(c)  # BIT-31
                c.die()
                self.deaths_total += 1
        self.creatures = alive_creatures

        # 5. Remover comida consumida
        self.foods = [f for f in self.foods if f.is_active]

        # 6. Jardim do Eden: fallback de extincao total (populacao == 0, nao coberto pelo README)
        # + regra real do README (populacao < 10, com sobreviventes: oasis denso nas posicoes deles)
        if len(self.creatures) == 0:
            self.extinctions_total += 1  # BIT-30
            if self.hall_of_fame:
                for child in self._spawn_from_hall_of_fame(15):  # BIT-35: era 10
                    self.add_creature(child)
            else:
                for _ in range(15):  # BIT-35: era 10
                    self.add_creature(Creature(self, generation=0))  # fallback: sem histórico ainda
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

        # 7. Amostragem do historico de metricas (BIT-26): 1 amostra por segundo simulado.
        # Amostrado no fim do step, depois da limpeza de mortos — o snapshot reflete o estado
        # que o get_state() deste frame veria. Com dt=1/30 o while nunca acumula 2 intervalos.
        self._metrics_accumulator += dt
        while self._metrics_accumulator >= METRICS_SAMPLE_INTERVAL:
            self._metrics_accumulator -= METRICS_SAMPLE_INTERVAL
            self.metrics_history.append(compute_metrics(self))


    def get_state(self):
        return {
            "paused": self.paused,
            "speed": self.speed,
            "time": self.time_elapsed,
            "generation": self.current_generation,
            "width": self.width,
            "height": self.height,
            "vision_radius": VISION_RADIUS,
            "vision_fov_degrees": VISION_FOV_DEGREES,
            "creatures": [c.to_dict() for c in self.creatures],
            "foods": [f.to_dict() for f in self.foods],
            "oases": [o.to_dict() for o in self.oases],
            "params": get_params(self),
            "metrics": compute_metrics(self),
        }
