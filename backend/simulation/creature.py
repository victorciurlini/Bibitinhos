import math
import random
import pymunk
import neat
from enum import Enum

from simulation.rtneat_wrapper import create_zero_genome, load_neat_config
from simulation.physics import COLLISION_CATEGORY_CREATURE

AGE_DEGRADATION_SCALE = 60.0
MOTOR_TORQUE_SCALE = 20.0
KINETIC_LINEAR_NORM = 200.0
KINETIC_ANGULAR_NORM = 10.0
LATERAL_GRIP_RATE = 20.0  # taxa de amortecimento lateral (1/segundo), tunavel

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
    LifeStage.JUVENILE: 0.3,
    LifeStage.ADULT: 0.8,
    LifeStage.ELDER: 2.0,
}

class Creature:
    def __init__(self, engine, x=None, y=None, genome=None):
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
        self.shape.collision_type = COLLISION_CATEGORY_CREATURE
        self.shape.owner = self

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
        self.mate_cooldown = 0.0

        # Cérebro NEAT: genoma injetado (reprodução futura) ou genoma zero (Gen 0)
        self.config = load_neat_config()
        self.genome = genome if genome is not None else create_zero_genome(engine.next_genome_id(), self.config)
        self.net = neat.nn.FeedForwardNetwork.create(self.genome, self.config)

        self.motor_forward = 0.0
        self.motor_torque = 0.0
        self.action_grab_drop = False
        self.action_mate = False
        self.is_holding = False  # placeholder do Load_Sensor; mecanica de grab fora de escopo desta task

    def think(self, engine):
        """Roda a rede neural a 10 FPS (brain tick) e cacheia as 4 saidas de atuadores."""
        inputs = list(self.vision) + [
            min(self.energy / self.max_energy, 1.0),                                    # Energy_Level
            min(self.age / AGE_DEGRADATION_SCALE, 1.0),                                  # Age_Degradation
            0.0,                                                                         # Hormonal_Level (sistema nao existe ainda)
            0.0,                                                                         # Biological_Clock (sistema nao existe ainda)
            1.0 if self.is_holding else 0.0,                                             # Load_Sensor
            max(-1.0, min(1.0, self.body.velocity.length / KINETIC_LINEAR_NORM)),        # Kinetic_Feedback linear
            max(-1.0, min(1.0, self.body.angular_velocity / KINETIC_ANGULAR_NORM)),      # Kinetic_Feedback angular
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
        self.mate_cooldown = max(0.0, self.mate_cooldown - dt)

        # Atualizar estágios de vida baseados na idade (mockado)
        if self.age > 30:
            self.life_stage = LifeStage.ELDER
        elif self.age > 10:
            self.life_stage = LifeStage.ADULT
        elif self.age > 2:
            self.life_stage = LifeStage.JUVENILE

        # Movimento vem da rede neural (cacheado em think(), 10 FPS), reaplicado a cada frame de fisica
        # EGG nao move nem paga custo de motor: o output do cerebro nunca e aplicado fisicamente nesse estagio
        motor_cost = 0.0
        if self.life_stage != LifeStage.EGG:
            forward_thrust = max(0.0, self.motor_forward)  # sem propulsao deliberada pra tras
            forward_impulse = (forward_thrust * self.speed * dt, 0)
            self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
            self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE
            motor_cost = forward_thrust * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05

            # Grip lateral: elimina deslizamento de lado por inercia, mantendo a fisica real
            # (colisoes ainda empurram a criatura; ela so nao desliza de lado por conta propria)
            local_velocity = self.body.velocity.rotated(-self.body.angle)  # x=frente, y=lado
            lateral_damping = max(0.0, 1.0 - LATERAL_GRIP_RATE * dt)
            damped_local_velocity = pymunk.Vec2d(local_velocity.x, local_velocity.y * lateral_damping)
            self.body.velocity = damped_local_velocity.rotated(self.body.angle)

        metabolism_cost = METABOLISM_RATE_BY_STAGE[self.life_stage]
        self.energy -= dt * (motor_cost + metabolism_cost)
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
