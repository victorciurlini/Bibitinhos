"""Testes de robustez evolutiva (BIT-35).

Cobre os novos limiares (Eden, HoF), o mecanismo de pressão adaptativa de
população e os valores de constantes ajustados.
"""
from simulation.creature import (
    Creature, LifeStage,
    STARTING_ENERGY, IDLE_PENALTY_RATE, FERTILITY_ENERGY_THRESHOLD,
    METABOLISM_RATE_BY_STAGE,
)
from simulation.engine import (
    SimulationEngine,
    HALL_OF_FAME_SIZE,
    HALL_OF_FAME_CHILDREN_WEIGHT,
    HALL_OF_FAME_FOOD_WEIGHT,
    LOW_POP_FOOD_THRESHOLD,
    HIGH_POP_FOOD_THRESHOLD,
    FOOD_MULTIPLIER_LOW_POP,
    FOOD_MULTIPLIER_HIGH_POP,
    REPRODUCTION_ENERGY_COST,
    REPRODUCTION_COOLDOWN,
    MATING_RADIUS,
)
from simulation.oasis import (
    EDEN_POPULATION_THRESHOLD,
    OASIS_TTL_MIN, OASIS_TTL_MAX,
    MAX_TOTAL_FOOD,
    OASIS_FOOD_SPAWN_CHANCE,
)

DT = 1 / 30.0


# ---------------------------------------------------------------------------
# Constantes — valores críticos do BIT-35
# ---------------------------------------------------------------------------

def test_starting_energy_is_85():
    assert STARTING_ENERGY == 85.0


def test_idle_penalty_rate_is_1_1():
    assert IDLE_PENALTY_RATE == 1.1


def test_fertility_energy_threshold_is_50():
    assert FERTILITY_ENERGY_THRESHOLD == 50.0


def test_metabolism_adult_is_0_5():
    assert METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] == 0.5


def test_oasis_ttl_min_is_25():
    assert OASIS_TTL_MIN == 25.0


def test_oasis_ttl_max_is_60():
    assert OASIS_TTL_MAX == 60.0


def test_max_total_food_is_150():
    assert MAX_TOTAL_FOOD == 150


def test_eden_threshold_is_15():
    assert EDEN_POPULATION_THRESHOLD == 15


def test_mating_radius_is_200():
    assert MATING_RADIUS == 200.0


def test_reproduction_energy_cost_is_20():
    assert REPRODUCTION_ENERGY_COST == 20.0


def test_reproduction_cooldown_is_6():
    assert REPRODUCTION_COOLDOWN == 6.0


def test_hall_of_fame_size_is_20():
    assert HALL_OF_FAME_SIZE == 20


# ---------------------------------------------------------------------------
# Pressão adaptativa de população
# ---------------------------------------------------------------------------

def test_food_multiplier_low_pop():
    engine = SimulationEngine()
    # pop < LOW_POP_FOOD_THRESHOLD
    for _ in range(LOW_POP_FOOD_THRESHOLD - 1):
        engine.add_creature(Creature(engine))
    assert engine._compute_food_multiplier() == FOOD_MULTIPLIER_LOW_POP


def test_food_multiplier_high_pop():
    engine = SimulationEngine()
    # pop > HIGH_POP_FOOD_THRESHOLD
    for _ in range(HIGH_POP_FOOD_THRESHOLD + 1):
        engine.add_creature(Creature(engine))
    assert engine._compute_food_multiplier() == FOOD_MULTIPLIER_HIGH_POP


def test_food_multiplier_neutral():
    engine = SimulationEngine()
    # pop entre LOW e HIGH (neutro)
    target = (LOW_POP_FOOD_THRESHOLD + HIGH_POP_FOOD_THRESHOLD) // 2
    for _ in range(target):
        engine.add_creature(Creature(engine))
    assert engine._compute_food_multiplier() == 1.0


def test_food_multiplier_boundary_low():
    engine = SimulationEngine()
    # pop == LOW_POP_FOOD_THRESHOLD → neutro (não é < threshold)
    for _ in range(LOW_POP_FOOD_THRESHOLD):
        engine.add_creature(Creature(engine))
    assert engine._compute_food_multiplier() == 1.0


def test_food_multiplier_boundary_high():
    engine = SimulationEngine()
    # pop == HIGH_POP_FOOD_THRESHOLD → neutro (não é > threshold)
    for _ in range(HIGH_POP_FOOD_THRESHOLD):
        engine.add_creature(Creature(engine))
    assert engine._compute_food_multiplier() == 1.0


# ---------------------------------------------------------------------------
# Hall of Fame — tamanho e score
# ---------------------------------------------------------------------------

def test_hall_of_fame_preserves_up_to_20():
    engine = SimulationEngine()
    config = engine.creatures[0].config if engine.creatures else None

    # Cria 25 criaturas mortas com idades distintas e registra no HoF
    for i in range(25):
        c = Creature(engine)
        c.age = float(i)
        c.children_count = 0
        c.food_eaten = 0
        engine._record_in_hall_of_fame(c)

    assert len(engine.hall_of_fame) == HALL_OF_FAME_SIZE  # 20, não 25


def test_hall_of_fame_score_includes_food_eaten():
    engine = SimulationEngine()

    c_comedor = Creature(engine)
    c_comedor.age = 10.0
    c_comedor.children_count = 0
    c_comedor.food_eaten = 20  # 20 × 1.0 = 20 pontos extras

    c_velho = Creature(engine)
    c_velho.age = 25.0  # 25 pontos de idade
    c_velho.children_count = 0
    c_velho.food_eaten = 0

    engine._record_in_hall_of_fame(c_comedor)
    engine._record_in_hall_of_fame(c_velho)

    # c_comedor: score = 10 + 20 = 30; c_velho: score = 25 → comedor deve ser melhor
    assert engine.hall_of_fame[0]["score"] > engine.hall_of_fame[1]["score"]
    # Score esperado do comedor
    expected_comedor = 10.0 + HALL_OF_FAME_FOOD_WEIGHT * 20
    assert engine.hall_of_fame[0]["score"] == expected_comedor


# ---------------------------------------------------------------------------
# Eden — gatilho antecipado (pop < 15) e respawn de 15 criaturas
# ---------------------------------------------------------------------------

def test_eden_triggers_at_14_creatures():
    """Com 14 criaturas vivas, Eden deve ativar (pop < EDEN_POPULATION_THRESHOLD=15)."""
    engine = SimulationEngine()
    for _ in range(14):
        c = Creature(engine)
        c.life_stage = LifeStage.ADULT
        c.energy = 50.0
        engine.add_creature(c)

    eden_was_inactive = not engine._eden_active
    engine.step(DT)
    assert eden_was_inactive
    assert engine._eden_active


def test_eden_does_not_trigger_at_15_creatures():
    """Com exatamente 15 criaturas, Eden NÃO deve ativar."""
    engine = SimulationEngine()
    for _ in range(15):
        c = Creature(engine)
        c.life_stage = LifeStage.ADULT
        c.energy = 50.0
        engine.add_creature(c)

    engine.step(DT)
    assert not engine._eden_active


def test_extinction_respawns_15_creatures():
    """Extinção total (pop=0) → respawn de 15 criaturas via HoF ou Gen-0."""
    engine = SimulationEngine()
    # Sem criaturas — extinguir explicitamente
    assert len(engine.creatures) == 0
    engine.step(DT)
    assert len(engine.creatures) == 15
