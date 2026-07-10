import math

import numpy as np
import pymunk

VISION_RADIUS = 200.0
NUM_VISION_SECTORS = 9


def compute_vision(creature, engine):
    """Retorna 9 cones binarios (1.0 presenca / 0.0 vazio) ao redor da criatura.

    Usa engine.physics.space.bb_query() para achar vizinhos num raio fixo e
    numpy.arctan2 para mapear o angulo relativo de cada vizinho ao cone
    correspondente. Nao diferencia tipo de vizinho (comida/criatura/parede).
    """
    vision = [0.0] * NUM_VISION_SECTORS
    space = engine.physics.space
    cx, cy = creature.body.position
    bb = pymunk.BB(cx - VISION_RADIUS, cy - VISION_RADIUS, cx + VISION_RADIUS, cy + VISION_RADIUS)
    shapes = space.bb_query(bb, pymunk.ShapeFilter())

    sector_width = 2 * np.pi / NUM_VISION_SECTORS

    for shape in shapes:
        if shape is creature.shape:
            continue
        nx, ny = shape.body.position
        dx, dy = nx - cx, ny - cy
        distance = math.hypot(dx, dy)
        if distance == 0 or distance > VISION_RADIUS:
            continue

        absolute_angle = np.arctan2(dy, dx)
        relative_angle = absolute_angle - creature.body.angle
        relative_angle = (relative_angle + np.pi) % (2 * np.pi) - np.pi
        shifted = (relative_angle + sector_width / 2) % (2 * np.pi)
        index = int(shifted // sector_width) % NUM_VISION_SECTORS
        vision[index] = 1.0

    return vision
