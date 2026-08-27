from simulation.creature import Creature, LifeStage, FERTILITY_ENERGY_THRESHOLD
from simulation.engine import (
    SimulationEngine,
    MATING_RADIUS,
    REPRODUCTION_ENERGY_COST,
    MIN_ENERGY_TO_REPRODUCE_ASEXUALLY,
    ASEXUAL_REPRODUCTION_ENERGY_COST,
)

DT = 1 / 30.0


def _make_elder(engine, x=700, y=700, energy=100.0, action_mate=False):
    c = Creature(engine, x=x, y=y)
    c.life_stage = LifeStage.ELDER
    c.energy = energy
    c.has_eaten = True
    c.action_mate = action_mate
    engine.add_creature(c)
    return c


def _make_adult(engine, x=700, y=700, energy=100.0, action_mate=False):
    c = Creature(engine, x=x, y=y)
    c.life_stage = LifeStage.ADULT
    c.energy = energy
    c.has_eaten = True
    c.action_mate = action_mate
    engine.add_creature(c)
    return c


# ---------------------------------------------------------------------------
# Fertilidade do ELDER
# ---------------------------------------------------------------------------

def test_elder_becomes_fertile_with_enough_energy():
    engine = SimulationEngine()
    c = _make_elder(engine, energy=FERTILITY_ENERGY_THRESHOLD + 1.0)
    c.update(DT, engine)
    assert c.is_fertile is True


def test_elder_below_threshold_stays_infertile():
    engine = SimulationEngine()
    c = _make_elder(engine, energy=FERTILITY_ENERGY_THRESHOLD - 1.0)
    c.is_fertile = False
    c.update(DT, engine)
    assert c.is_fertile is False


def test_elder_without_eating_stays_infertile():
    engine = SimulationEngine()
    c = _make_elder(engine, energy=FERTILITY_ENERGY_THRESHOLD + 5.0)
    c.has_eaten = False
    c.is_fertile = False
    c.update(DT, engine)
    assert c.is_fertile is False


# ---------------------------------------------------------------------------
# Reprodução sexuada com ELDER
# ---------------------------------------------------------------------------

def test_two_elders_reproduce_sexually():
    engine = SimulationEngine()
    c1 = _make_elder(engine, x=700, y=700, energy=100.0, action_mate=True)
    c2 = _make_elder(engine, x=705, y=700, energy=100.0, action_mate=True)
    c1.is_fertile = True
    c2.is_fertile = True

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before + 1


def test_elder_and_adult_reproduce_sexually():
    engine = SimulationEngine()
    elder = _make_elder(engine, x=700, y=700, energy=100.0, action_mate=True)
    adult = _make_adult(engine, x=705, y=700, energy=100.0, action_mate=True)
    elder.is_fertile = True
    adult.is_fertile = True

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before + 1


def test_sexual_reproduction_applies_cost_and_cooldown_to_elder():
    engine = SimulationEngine()
    c1 = _make_elder(engine, x=700, y=700, energy=100.0, action_mate=True)
    c2 = _make_elder(engine, x=705, y=700, energy=100.0, action_mate=True)
    c1.is_fertile = True
    c2.is_fertile = True

    engine.step(DT)

    assert c1.reproduction_cooldown > 0
    assert c2.reproduction_cooldown > 0
    assert c1.energy < 100.0
    assert c2.energy < 100.0


def test_elder_fertility_consumed_after_mating():
    # has_eaten=False: impede re-aquisicao de fertilidade no mesmo step (padrao dos testes de ADULT)
    engine = SimulationEngine()
    c1 = _make_elder(engine, x=700, y=700, energy=100.0, action_mate=True)
    c2 = _make_elder(engine, x=705, y=700, energy=100.0, action_mate=True)
    c1.has_eaten = False
    c2.has_eaten = False
    c1.is_fertile = True
    c2.is_fertile = True

    engine.step(DT)

    assert c1.is_fertile is False
    assert c2.is_fertile is False


# ---------------------------------------------------------------------------
# Reprodução assexuada com ELDER
# ---------------------------------------------------------------------------

def test_elder_reproduces_asexually_when_alone():
    engine = SimulationEngine()
    c = _make_elder(engine, x=700, y=700,
                    energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY + 1.0,
                    action_mate=True)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before + 1


def test_asexual_elder_cost_and_cooldown_applied():
    engine = SimulationEngine()
    c = _make_elder(engine, x=700, y=700,
                    energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY + 1.0,
                    action_mate=True)
    energy_before = c.energy

    engine.step(DT)

    assert c.reproduction_cooldown > 0
    assert c.energy < energy_before


# ---------------------------------------------------------------------------
# JUVENILE continua impedido (anti-regressão)
# ---------------------------------------------------------------------------

def test_juvenile_cannot_reproduce_sexually():
    engine = SimulationEngine()
    c1 = Creature(engine, x=700, y=700)
    c2 = Creature(engine, x=705, y=700)
    for c in (c1, c2):
        c.life_stage = LifeStage.JUVENILE
        c.energy = 100.0
        c.has_eaten = True
        c.action_mate = True
        c.is_fertile = True
        engine.add_creature(c)

    count_before = len(engine.creatures)
    engine.step(DT)

    children = [c for c in engine.creatures if c not in (c1, c2)]
    assert len(children) == 0


def test_juvenile_cannot_reproduce_asexually():
    engine = SimulationEngine()
    c = Creature(engine, x=700, y=700)
    c.life_stage = LifeStage.JUVENILE
    c.energy = MIN_ENERGY_TO_REPRODUCE_ASEXUALLY + 10.0
    c.action_mate = True
    engine.add_creature(c)

    count_before = len(engine.creatures)
    engine.step(DT)

    children = [x for x in engine.creatures if x is not c]
    assert len(children) == 0


def test_juvenile_stays_infertile_even_with_energy_and_food():
    engine = SimulationEngine()
    c = Creature(engine, x=700, y=700)
    c.life_stage = LifeStage.JUVENILE
    c.energy = FERTILITY_ENERGY_THRESHOLD + 10.0
    c.has_eaten = True
    c.is_fertile = False
    engine.add_creature(c)

    c.update(DT, engine)
    assert c.is_fertile is False
