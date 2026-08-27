import pytest

from simulation.creature import (
    Creature,
    LifeStage,
    METABOLISM_RATE_BY_STAGE,
    IDLE_PENALTY_RATE,
    MOVEMENT_REFERENCE_SPEED,
)
from simulation.engine import SimulationEngine
from simulation.food import Food

DT = 1 / 30.0


@pytest.mark.parametrize("stage", [LifeStage.JUVENILE, LifeStage.ADULT, LifeStage.ELDER])
def test_passive_metabolism_cost_by_stage(stage):
    """Metabolismo puro, isolado do imposto de ociosidade do BIT-20.

    A criatura e posta em movimento (velocidade >= MOVEMENT_REFERENCE_SPEED, alinhada ao heading
    para o grip lateral nao interferir) justamente para zerar o idle_cost e deixar so o metabolismo.
    """
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.life_stage = stage
    creature.motor_forward = 0.0
    creature.motor_torque = 0.0
    creature.body.angle = 0.0
    creature.body.velocity = (MOVEMENT_REFERENCE_SPEED, 0.0)

    energy_before = creature.energy
    creature.update(DT, engine)
    cost = energy_before - creature.energy

    assert cost == pytest.approx(DT * METABOLISM_RATE_BY_STAGE[stage])


@pytest.mark.parametrize("stage", [LifeStage.JUVENILE, LifeStage.ADULT, LifeStage.ELDER])
def test_stationary_creature_pays_metabolism_plus_idle_penalty(stage):
    """BIT-20: parada, a criatura paga metabolismo + imposto de ociosidade cheio."""
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.life_stage = stage
    creature.motor_forward = 0.0
    creature.motor_torque = 0.0
    creature.body.velocity = (0.0, 0.0)

    energy_before = creature.energy
    creature.update(DT, engine)
    cost = energy_before - creature.energy

    assert cost == pytest.approx(DT * (METABOLISM_RATE_BY_STAGE[stage] + IDLE_PENALTY_RATE))


def test_egg_pays_no_metabolism_cost():
    engine = SimulationEngine()
    egg = Creature(engine)  # life_stage default = EGG
    egg.motor_forward = 0.0
    egg.motor_torque = 0.0

    energy_before = egg.energy
    egg.update(DT, engine)

    assert egg.energy == energy_before


def test_metabolism_rates_are_strictly_increasing_by_stage():
    assert METABOLISM_RATE_BY_STAGE[LifeStage.EGG] == 0.0
    assert (
        METABOLISM_RATE_BY_STAGE[LifeStage.EGG]
        < METABOLISM_RATE_BY_STAGE[LifeStage.JUVENILE]
        < METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]
        < METABOLISM_RATE_BY_STAGE[LifeStage.ELDER]
    )


def test_creature_dies_of_starvation_from_passive_metabolism_alone():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.life_stage = LifeStage.ADULT
    creature.motor_forward = 0.0
    creature.motor_torque = 0.0
    creature.energy = 10.0  # baixa o suficiente pra morrer rapido so de metabolismo

    for _ in range(1000):
        if not creature.is_alive:
            break
        creature.update(DT, engine)

    assert creature.is_alive is False


def test_eating_periodically_extends_survival_beyond_pure_metabolism():
    engine = SimulationEngine()

    starving = Creature(engine, x=100, y=100)
    starving.life_stage = LifeStage.ADULT
    starving.motor_forward = 0.0
    starving.motor_torque = 0.0
    starving.energy = 10.0

    steps_to_die_starving = 0
    while starving.is_alive and steps_to_die_starving < 10000:
        starving.update(DT, engine)
        steps_to_die_starving += 1

    fed = Creature(engine, x=200, y=200)
    fed.life_stage = LifeStage.ADULT
    fed.motor_forward = 0.0
    fed.motor_torque = 0.0
    fed.energy = 10.0

    steps_to_die_fed = 0
    while fed.is_alive and steps_to_die_fed < 10000:
        fed.update(DT, engine)
        # a cada ~1s simulado, come uma Food (mesma logica do handler de colisao BIT-03)
        if steps_to_die_fed % 30 == 0:
            food = Food(engine, fed.body.position.x, fed.body.position.y)
            fed.energy = min(fed.energy + food.energy_value, fed.max_energy)
            food.consume()
        steps_to_die_fed += 1

    assert steps_to_die_fed > steps_to_die_starving
