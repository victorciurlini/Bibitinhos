import math
import random

MAX_ACTIVE_OASES = 4
OASIS_SPAWN_CHANCE_PER_FRAME = 0.01
OASIS_RADIUS = 150.0
OASIS_TTL_MIN = 15.0
OASIS_TTL_MAX = 40.0
OASIS_FOOD_CAP = 8
OASIS_FOOD_SPAWN_CHANCE = 0.08
MAX_TOTAL_FOOD = 50

EDEN_POPULATION_THRESHOLD = 10
EDEN_OASIS_RADIUS = 200.0
EDEN_OASIS_TTL = 30.0
EDEN_OASIS_FOOD_CAP = 20


class Oasis:
    """Zona de fertilidade invisivel (sem corpo Pymunk): delimita onde Food pode nascer."""

    def __init__(self, x, y, radius=OASIS_RADIUS, ttl=None, food_cap=OASIS_FOOD_CAP):
        self.x = x
        self.y = y
        self.radius = radius
        self.ttl = ttl if ttl is not None else random.uniform(OASIS_TTL_MIN, OASIS_TTL_MAX)
        self.food_cap = food_cap

    def random_point_inside(self):
        """Amostragem uniforme dentro do circulo (evita concentracao nos cantos)."""
        angle = random.uniform(0, 2 * math.pi)
        r = self.radius * math.sqrt(random.random())
        return self.x + r * math.cos(angle), self.y + r * math.sin(angle)

    def to_dict(self):
        return {"x": self.x, "y": self.y, "radius": self.radius, "ttl": self.ttl}
