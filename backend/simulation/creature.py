import math
import random
import pymunk
import neat
from enum import Enum

from simulation.rtneat_wrapper import create_zero_genome, load_neat_config
from simulation.physics import COLLISION_CATEGORY_CREATURE

AGE_DEGRADATION_SCALE = 30.0
MOTOR_TORQUE_SCALE = 20.0
KINETIC_LINEAR_NORM = 200.0
KINETIC_ANGULAR_NORM = 10.0
LATERAL_GRIP_RATE = 20.0  # taxa de amortecimento lateral (1/segundo)
# Nota (BIT-17): mantido inalterado ao introduzir arrasto de agua - corrige derrapagem
# lateral por rotacao (BIT-07), ortogonal ao arrasto longitudinal; reduzi-lo abaixo de
# ~11.1 quebra test_locomotion.py::test_lateral_velocity_is_damped_towards_zero_over_frames.
CREATURE_MASS = 1.0
STARTING_ENERGY = 85.0  # BIT-35: era 75 — margem extra para alcançar a primeira comida

# BIT-22: reproducao sexuada por FERTILIDADE PERSISTENTE, nao por energia instantanea na colisao.
# A criatura vira fertil ao atingir este limiar (tendo comido) e MANTEM a fertilidade mesmo com a
# energia caindo no roaming, ate acasalar. O limiar e ALCANCAVEL de proposito (< max_energy); "comer
# antes de acasalar" (BIT-16) e garantido pela flag has_eaten, nao pelo nivel de energia.
FERTILITY_ENERGY_THRESHOLD = 50.0  # BIT-35: era 60 — mais criaturas alcançam fertilidade

# --- Economia de energia (BIT-20): explorar tem que ser mais barato que ficar parado ---
# O modelo antigo (thrust*speed*0.1 + |torque|*size*0.05) cobrava 5.0/s para andar e so 0.5/s
# para girar no lugar. Com o metabolismo em cima, ficar parado girando sobrevivia 77s e explorar
# sobrevivia 20s — a selecao natural estava otimizando corretamente para a paralisia, porque era
# isso que o ambiente premiava. Aqui o sinal se inverte: girar parado passa a ser a PIOR estrategia.
MOVEMENT_REFERENCE_SPEED = 35.0  # px/s: velocidade real a partir da qual a criatura conta como
                                 # "explorando de verdade". 75% da terminal de 46.8 px/s medida sob
                                 # damping=0.35 (BIT-17); folgada o bastante para nao punir os ~2.6s
                                 # de aceleracao a partir do repouso.
IDLE_PENALTY_RATE = 0.1          # energia/s de imposto de ociosidade, cheio quando parada.
MOTOR_FORWARD_COST = 0.05        # energia/s a full thrust (era efetivamente 5.0/s)
SPIN_COST = 0.3                  # energia/s a full torque, mas so quando parada: curvar enquanto se
                                 # move e de graca (a criatura precisa virar p/ perseguir comida)

HELD_FOOD_CONSUME_ENERGY_FRACTION = 0.5  # abaixo desta fração de energia, consome a comida carregada
HELD_FOOD_MOUTH_OFFSET = 15.0            # px à frente do centro onde a comida carregada é fixada

class LifeStage(Enum):
    EGG = 0
    JUVENILE = 1
    ADULT = 2
    ELDER = 3

# Custo metabolico passivo por segundo, so por estar viva (energia/segundo).
# Taxas tunaveis, estritamente crescentes: cria pressao real para aprender a comer
# e "longevidade" como metrica emergente (ELDER degrada mais rapido).
METABOLISM_RATE_BY_STAGE = {
    LifeStage.EGG: 0.0,
    LifeStage.JUVENILE: 0.1,
    LifeStage.ADULT: 0.2,    # BIT-35: era 0.8 — adulto sobrevive mais tempo sem comida
    LifeStage.ELDER: 1.0,
}

# Gradiente visual de ciclo de vida: azul (recem-nascido) -> verde (maduro) -> cinza/quase-preto
# (velhice, guiado pela energia restante, ja que nao ha teto de morte por idade).
LIFE_COLOR_EGG = (59, 130, 246)          # #3b82f6 azul — recem-nascido
LIFE_COLOR_MATURE = (34, 197, 94)        # #22c55e verde — maduro/pronto p/ reproduzir
LIFE_COLOR_ELDER_START = (107, 114, 128) # #6b7280 cinza — inicio da velhice, energia cheia
LIFE_COLOR_DEATH = (17, 24, 39)          # #111827 quase-preto — energia perto de zero

VISUAL_SCALE_EGG = 0.7
VISUAL_SCALE_ADULT = 1.0
VISUAL_SCALE_ELDER_MIN = 0.85


def _lerp_rgb(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


def _rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def compute_life_color(age, energy, max_energy):
    """Azul (0-2) -> verde (2-10) -> verde->cinza continuo (10-30) -> cinza/preto por energia (30+)."""
    if age <= 10:
        t = max(0.0, (age - 2) / 8.0) if age > 2 else 0.0
        rgb = _lerp_rgb(LIFE_COLOR_EGG, LIFE_COLOR_MATURE, t)
    elif age <= 30:
        t = (age - 10) / 20.0
        rgb = _lerp_rgb(LIFE_COLOR_MATURE, LIFE_COLOR_ELDER_START, t)
    else:
        energy_fraction = max(0.0, min(1.0, energy / max_energy))
        rgb = _lerp_rgb(LIFE_COLOR_DEATH, LIFE_COLOR_ELDER_START, energy_fraction)
    return _rgb_to_hex(rgb)


def compute_visual_scale(age, energy, max_energy):
    """0.7 (ovo) -> 1.0 (adulto) -> encolhe ate 0.85 conforme energia cai no estagio ELDER."""
    if age <= 2:
        return VISUAL_SCALE_EGG
    elif age <= 10:
        t = (age - 2) / 8.0
        return VISUAL_SCALE_EGG + (VISUAL_SCALE_ADULT - VISUAL_SCALE_EGG) * t
    elif age <= 30:
        return VISUAL_SCALE_ADULT
    else:
        energy_fraction = max(0.0, min(1.0, energy / max_energy))
        return VISUAL_SCALE_ADULT - (VISUAL_SCALE_ADULT - VISUAL_SCALE_ELDER_MIN) * (1.0 - energy_fraction)


class Creature:
    def __init__(self, engine, x=None, y=None, genome=None, generation=0):
        self.engine = engine
        
        # Pymunk Physics integration
        mass = CREATURE_MASS
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
        self.shape.collision_type = COLLISION_CATEGORY_CREATURE
        self.shape.owner = self

        # We assume engine.physics.space exists; add body and shape
        if hasattr(engine, 'physics') and engine.physics is not None:
            engine.physics.space.add(self.body, self.shape)
        
        # Atributos baseados em "DNA" (mockados por enquanto)
        self.speed = 50.0
        self.size = 10.0
        self.energy = STARTING_ENERGY
        self.max_energy = 100.0
        self.diet = 'herbivore' # ou 'carnivore'
        
        self.is_alive = True
        self.life_stage = LifeStage.EGG
        self.age = 0.0
        self.vision = [0.0] * 9
        self.reproduction_cooldown = 0.0
        self.sought_mate_this_frame = False  # BIT-22: substitui collided_with_creature_this_frame.
        self.has_eaten = False   # BIT-22: setada ao comer (handler de colisao criatura x comida).
        self.is_fertile = False  # BIT-22: fertilidade persistente para reproducao sexuada.

        self.generation = generation      # profundidade de linhagem (0 = Gen 0 / re-semeadura)
        self.food_eaten = 0               # comidas ingeridas na vida
        self.children_count = 0           # filhos gerados (sexuado + assexuado)

        # Cérebro NEAT: genoma injetado (reprodução futura) ou genoma zero (Gen 0)
        self.config = load_neat_config()
        self.genome = genome if genome is not None else create_zero_genome(engine.next_genome_id(), self.config)
        self.id = self.genome.key  # unico e monotonico via engine.next_genome_id()
        self.net = neat.nn.FeedForwardNetwork.create(self.genome, self.config)

        self.motor_forward = 0.0
        self.motor_torque = 0.0
        self.action_grab_drop = False
        self.action_mate = False
        self.is_holding = False
        self.held_food = None
        self.food_grabbed = 0

    def grab_food(self, food):
        """Pega um item: sai do space (vira inventário), TTL pausa, passa a seguir a boca."""
        space = self.engine.physics.space if getattr(self.engine, "physics", None) else None
        if space is not None and food.body in space.bodies:
            space.remove(food.body, food.shape)
        food.is_held = True
        self.held_food = food
        self.is_holding = True
        self.food_grabbed += 1

    def drop_food(self):
        """Solta o item de volta ao mundo na posição atual da criatura; TTL volta a correr."""
        food = self.held_food
        if food is None:
            return
        food.is_held = False
        food.ttl = food.max_ttl
        food.body.position = self.body.position
        food.body.velocity = (0, 0)
        space = self.engine.physics.space if getattr(self.engine, "physics", None) else None
        if space is not None and food.body not in space.bodies and food.is_active:
            space.add(food.body, food.shape)
        self.held_food = None
        self.is_holding = False

    def think(self, engine):
        """Roda a rede neural a 10 FPS (brain tick) e cacheia as 4 saidas de atuadores."""
        # BIT-38: Sensores de proximidade de parede (normalizados [0,1], 0=perto, 1=longe/limite oposto)
        cx, cy = self.body.position.x, self.body.position.y
        wall_north = min(1.0, max(0.0, cy / engine.height))
        wall_south = min(1.0, max(0.0, (engine.height - cy) / engine.height))
        wall_west = min(1.0, max(0.0, cx / engine.width))
        wall_east = min(1.0, max(0.0, (engine.width - cx) / engine.width))

        inputs = list(self.vision) + [
            min(self.energy / self.max_energy, 1.0),                                    # Energy_Level
            min(self.age / AGE_DEGRADATION_SCALE, 1.0),                                  # Age_Degradation
            0.0,                                                                         # Hormonal_Level (sistema nao existe ainda)
            0.0,                                                                         # Biological_Clock (sistema nao existe ainda)
            1.0 if self.is_holding else 0.0,                                             # Load_Sensor
            max(-1.0, min(1.0, self.body.velocity.length / KINETIC_LINEAR_NORM)),        # Kinetic_Feedback linear
            max(-1.0, min(1.0, self.body.angular_velocity / KINETIC_ANGULAR_NORM)),      # Kinetic_Feedback angular
            wall_north,  # Índice 16: Wall_North
            wall_south,  # Índice 17: Wall_South
            wall_west,   # Índice 18: Wall_West
            wall_east,   # Índice 19: Wall_East
        ]
        outputs = self.net.activate(inputs)
        self.motor_forward = outputs[0]
        self.motor_torque = outputs[1]
        self.action_grab_drop = outputs[2] > 0.0
        self.action_mate = outputs[3] > 0.0

    def update(self, dt, engine):
        if not self.is_alive:
            return

        self.age += dt
        self.reproduction_cooldown = max(0.0, self.reproduction_cooldown - dt)

        # Atualizar estágios de vida baseados na idade (mockado)
        if self.age > 30:
            self.life_stage = LifeStage.ELDER
        elif self.age > 10:
            self.life_stage = LifeStage.ADULT
        elif self.age > 2:
            self.life_stage = LifeStage.JUVENILE

        # Movimento vem da rede neural (cacheado em think(), 10 FPS), reaplicado a cada frame de fisica
        # EGG nao move nem paga custo de motor nem de ociosidade: o output do cerebro nunca e aplicado
        # fisicamente nesse estagio, entao multa-lo por estar parado seria puni-lo por existir.
        motor_cost = 0.0
        idle_cost = 0.0
        if self.life_stage != LifeStage.EGG:
            # Fator de movimento medido pela VELOCIDADE REAL do corpo, nao pelo output do motor: e isso
            # que torna a multa imburlavel (travar contra a parede => velocidade ~0 => paga o imposto cheio).
            # Medido ANTES do impulso deste frame, de proposito: o que interessa e o deslocamento que a
            # criatura de fato conseguiu no passo de fisica anterior, nao o empurrao que ela acabou de dar
            # (o Pymunk aplica o impulso na velocidade na hora, o que mascararia quem esta travado).
            movement_factor = min(1.0, self.body.velocity.length / MOVEMENT_REFERENCE_SPEED)
            idle_cost = IDLE_PENALTY_RATE * (1.0 - movement_factor)

            forward_thrust = max(0.0, self.motor_forward)  # sem propulsao deliberada pra tras
            forward_impulse = (forward_thrust * self.speed * dt, 0)
            self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
            self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE

            motor_cost = (
                MOTOR_FORWARD_COST * forward_thrust
                + SPIN_COST * abs(self.motor_torque) * (1.0 - movement_factor)
            )

            # Grip lateral: elimina deslizamento de lado por inercia, mantendo a fisica real
            # (colisoes ainda empurram a criatura; ela so nao desliza de lado por conta propria)
            local_velocity = self.body.velocity.rotated(-self.body.angle)  # x=frente, y=lado
            lateral_damping = max(0.0, 1.0 - LATERAL_GRIP_RATE * dt)
            damped_local_velocity = pymunk.Vec2d(local_velocity.x, local_velocity.y * lateral_damping)
            self.body.velocity = damped_local_velocity.rotated(self.body.angle)

        metabolism_cost = METABOLISM_RATE_BY_STAGE[self.life_stage]
        self.energy -= dt * (motor_cost + idle_cost + metabolism_cost)
        if self.energy <= 0:
            self.is_alive = False

        # Fertilidade persistente (BIT-22): vira fertil ao ser ADULT, ja ter comido e alcancar o limiar.
        # Uma vez fertil, permanece ate acasalar (o roaming faz a energia cair, mas nao tira a aptidao).
        if (self.life_stage in (LifeStage.ADULT, LifeStage.ELDER) and self.has_eaten
                and self.energy >= FERTILITY_ENERGY_THRESHOLD):
            self.is_fertile = True

        if self.is_alive and self.is_holding and self.held_food is not None:
            if self.energy < HELD_FOOD_CONSUME_ENERGY_FRACTION * self.max_energy:
                food = self.held_food
                self.energy = min(self.energy + food.energy_value, self.max_energy)
                self.has_eaten = True
                self.food_eaten += 1
                self.held_food = None
                self.is_holding = False
                food.is_held = False
                food.consume()
            elif not self.action_grab_drop:
                self.drop_food()

    def die(self):
        self.is_alive = False
        if self.held_food is not None:
            self.drop_food()
        if hasattr(self.engine, 'physics') and self.engine.physics is not None:
            if self.body in self.engine.physics.space.bodies:
                self.engine.physics.space.remove(self.body, self.shape)
            
    def to_dict(self):
        return {
            "id": self.id,
            "x": self.body.position.x,
            "y": self.body.position.y,
            "rotation": self.body.angle,
            "radius": self.size * compute_visual_scale(self.age, self.energy, self.max_energy),
            "color": compute_life_color(self.age, self.energy, self.max_energy),
            "energy": self.energy,
            "max_energy": self.max_energy,
            "age": self.age,
            "diet": self.diet,
            "life_stage": self.life_stage.name,
            "reproduction_cooldown": self.reproduction_cooldown,
            "vision": [] if self.life_stage == LifeStage.EGG else self.vision,
            "motor_forward": self.motor_forward,
            "motor_torque": self.motor_torque,
            "action_mate": self.action_mate,
            "action_grab_drop": self.action_grab_drop,
            "generation": self.generation,
            "food_eaten": self.food_eaten,
            "children_count": self.children_count,
        }
