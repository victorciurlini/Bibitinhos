import math
import random

MAX_ACTIVE_OASES = 6          # BIT-22: era 4
MAX_TOTAL_OASES = 10  # teto duro, vale inclusive para o Jardim do Eden
OASIS_SPAWN_CHANCE_PER_FRAME = 0.01
OASIS_RADIUS = 150.0
OASIS_TTL_MIN = 25.0          # BIT-35: era 15.0 — oásis duram mais
OASIS_TTL_MAX = 60.0          # BIT-35: era 40.0 — oásis mais persistentes
OASIS_FOOD_CAP = 18           # BIT-22: era 8
OASIS_FOOD_SPAWN_CHANCE = 0.22  # BIT-35: era 0.18 — ligeiro aumento de densidade
MAX_TOTAL_FOOD = 150          # BIT-35: era 110 — mais comida no mapa

EDEN_POPULATION_THRESHOLD = 15  # BIT-35: era 10 — seguro ativa mais cedo
EDEN_OASIS_RADIUS = 200.0
EDEN_OASIS_TTL = 30.0
EDEN_OASIS_FOOD_CAP = 20
# BIT-20: o oasis do Eden nasce longe do sobrevivente, nao em cima dele — comida se conquista andando.
EDEN_OASIS_MIN_DISTANCE = 250.0
EDEN_OASIS_MAX_DISTANCE = 400.0  # continua dentro do alcance de exploracao, mas exige locomocao


class Oasis:
    """Zona de fertilidade invisivel (sem corpo Pymunk): delimita onde Food pode nascer."""

    def __init__(self, x, y, radius=OASIS_RADIUS, ttl=None, food_cap=OASIS_FOOD_CAP):
        self.x = x
        self.y = y
        self.radius = radius
        self.ttl = ttl if ttl is not None else random.uniform(OASIS_TTL_MIN, OASIS_TTL_MAX)
        self.ttl_initial = self.ttl
        self.food_cap = food_cap

    def random_point_inside(self):
        """Amostragem uniforme dentro do circulo (evita concentracao nos cantos)."""
        angle = random.uniform(0, 2 * math.pi)
        r = self.radius * math.sqrt(random.random())
        return self.x + r * math.cos(angle), self.y + r * math.sin(angle)

    def to_dict(self):
        return {
            "x": self.x, "y": self.y, "radius": self.radius, "ttl": self.ttl,
            "ttl_fraction": max(0.0, self.ttl / self.ttl_initial),
        }
