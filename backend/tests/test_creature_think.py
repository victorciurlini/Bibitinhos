import pytest

from simulation.creature import Creature, LifeStage, METABOLISM_RATE_BY_STAGE
from simulation.engine import SimulationEngine


def test_think_runs_without_exception_on_fresh_creature():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.think(engine)


def test_think_outputs_motor_within_tanh_range():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.think(engine)
    assert -1.0 <= creature.motor_forward <= 1.0
    assert -1.0 <= creature.motor_torque <= 1.0


def test_think_action_flags_are_bool():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.think(engine)
    assert isinstance(creature.action_grab_drop, bool)
    assert isinstance(creature.action_mate, bool)


def test_update_after_think_never_increases_energy():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.life_stage = creature.life_stage.__class__.ADULT  # sai do estagio EGG p/ mover
    creature.think(engine)
    energy_before = creature.energy
    creature.update(1 / 30.0, engine)
    assert creature.energy <= energy_before


def test_update_energy_cost_proportional_to_motor_magnitude():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.life_stage = creature.life_stage.__class__.ADULT
    creature.think(engine)

    # Zera os motores manualmente e mede o custo minimo (so vivo, sem torque/impulso)
    quiet = Creature(engine)
    quiet.life_stage = quiet.life_stage.__class__.ADULT
    quiet.motor_forward = 0.0
    quiet.motor_torque = 0.0
    quiet_energy_before = quiet.energy
    quiet.update(1 / 30.0, engine)
    quiet_cost = quiet_energy_before - quiet.energy
    expected_quiet_cost = (1 / 30.0) * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]
    assert quiet_cost == pytest.approx(expected_quiet_cost)

    active = Creature(engine)
    active.life_stage = active.life_stage.__class__.ADULT
    active.motor_forward = 1.0
    active.motor_torque = 1.0
    active_energy_before = active.energy
    active.update(1 / 30.0, engine)
    active_cost = active_energy_before - active.energy
    assert active_cost > quiet_cost


def test_egg_pays_no_motor_cost_even_with_strong_motor_output():
    engine = SimulationEngine()
    egg = Creature(engine)  # life_stage default = EGG
    egg.motor_forward = 1.0
    egg.motor_torque = 1.0
    energy_before = egg.energy
    egg.update(1 / 30.0, engine)
    assert egg.energy == energy_before


def test_think_runs_for_all_alive_creatures_via_engine_step():
    engine = SimulationEngine()
    for _ in range(5):
        engine.add_creature(Creature(engine))

    for _ in range(20):
        engine.step(1 / 30.0)
