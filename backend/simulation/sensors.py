import math

import numpy as np
import pymunk

from simulation.creature import LifeStage
from simulation.physics import COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_FOOD

VISION_RADIUS = 80.0
NUM_VISION_SECTORS = 9
VISION_FOV_DEGREES = 120.0
VISION_FOV_RADIANS = math.radians(VISION_FOV_DEGREES)

# BIT-21: fracao de energia a partir da qual um adulto passa a ser considerado "pronto para acasalar"
# para efeito de PERCEPCAO (nao e o limiar de reproducao do engine, que e absoluto = MIN_ENERGY_TO_MATE).
# Espelha o MIN_ENERGY_TO_MATE = 65 atual do engine sem acoplar sensors.py a ele (evita import circular).
# (a spec citava 0.85 por referenciar o valor antigo de 85, retunado para 65 desde entao.)
MATE_ATTRACTION_ENERGY_FRACTION = 0.65


def compute_vision(creature, engine):
    """Retorna 9 cones com sinal, cobrindo um cone frontal de VISION_FOV_DEGREES
    graus a frente da criatura (setor 4, o do meio, e o eixo central "para
    frente"; setores 0 e 8 sao as bordas extremas do cone). Nada fora do
    cone (incluindo tudo atras da criatura) ativa qualquer setor.

    Cada cone e positivo (comida, magnitude = fome), negativo (outra
    criatura, magnitude = energia normalizada, so se a propria criatura
    for ADULT) ou zero (vazio/fora do cone). Usa shape.collision_type para
    distinguir tipo sem precisar importar Food (evita ciclo de import);
    paredes nao setam collision_type e sao ignoradas automaticamente.
    Comida tem precedencia sobre criatura quando ambas caem no mesmo setor.
    """
    food_present = [False] * NUM_VISION_SECTORS
    creature_present = [False] * NUM_VISION_SECTORS

    space = engine.physics.space
    cx, cy = creature.body.position
    bb = pymunk.BB(cx - VISION_RADIUS, cy - VISION_RADIUS, cx + VISION_RADIUS, cy + VISION_RADIUS)
    shapes = space.bb_query(bb, pymunk.ShapeFilter())

    half_fov = VISION_FOV_RADIANS / 2
    sector_width = VISION_FOV_RADIANS / NUM_VISION_SECTORS

    for shape in shapes:
        if shape is creature.shape:
            continue
        if shape.collision_type not in (COLLISION_CATEGORY_FOOD, COLLISION_CATEGORY_CREATURE):
            continue  # paredes e qualquer shape sem tipo definido

        nx, ny = shape.body.position
        dx, dy = nx - cx, ny - cy
        distance = math.hypot(dx, dy)
        if distance == 0 or distance > VISION_RADIUS:
            continue

        absolute_angle = np.arctan2(dy, dx)
        relative_angle = absolute_angle - creature.body.angle
        relative_angle = (relative_angle + np.pi) % (2 * np.pi) - np.pi
        if abs(relative_angle) > half_fov:
            continue  # fora do cone frontal (inclui tudo as costas)

        shifted = relative_angle + half_fov
        index = min(int(shifted // sector_width), NUM_VISION_SECTORS - 1)

        if shape.collision_type == COLLISION_CATEGORY_FOOD:
            food_present[index] = True
        else:
            creature_present[index] = True

    hunger = 1.0 - min(creature.energy / creature.max_energy, 1.0)
    energy_fraction = min(creature.energy / creature.max_energy, 1.0)
    is_adult = creature.life_stage == LifeStage.ADULT

    # Neutralizacao da repulsao (BIT-21): um adulto PRONTO para acasalar percebe outras criaturas como
    # sinal POSITIVO (atrativo) — assim a mesma semente de food-taxis o puxa na direcao de parceiros,
    # em vez de repeli-lo. Quem comer vs. acasalar no contato e resolvido pelo tipo de colisao no
    # engine, nao por este canal — logo "borrar" o sinal para um adulto pronto e inofensivo.
    observer_ready_to_mate = (
        is_adult
        and energy_fraction >= MATE_ATTRACTION_ENERGY_FRACTION
        and creature.reproduction_cooldown <= 0.0
    )
    mate_signal = energy_fraction if is_adult else 0.0
    creature_sign = 1.0 if observer_ready_to_mate else -1.0

    vision = [0.0] * NUM_VISION_SECTORS
    for i in range(NUM_VISION_SECTORS):
        if food_present[i]:
            vision[i] = hunger
        elif creature_present[i]:
            vision[i] = creature_sign * mate_signal
    return vision
