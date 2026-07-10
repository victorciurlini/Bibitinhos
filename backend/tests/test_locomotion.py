import math

import pymunk

from simulation.creature import Creature, LifeStage
from simulation.engine import SimulationEngine


def _make_adult(engine, angle=0.0):
    creature = Creature(engine)
    creature.life_stage = LifeStage.ADULT
    creature.body.angle = angle
    creature.body.velocity = (0, 0)
    creature.body.angular_velocity = 0.0
    return creature


def test_negative_motor_forward_produces_no_backward_thrust():
    engine = SimulationEngine()
    creature = _make_adult(engine)
    creature.motor_forward = -1.0
    creature.motor_torque = 0.0

    creature.update(1 / 30.0, engine)

    local_velocity = creature.body.velocity.rotated(-creature.body.angle)
    assert local_velocity.x >= 0.0


def test_lateral_velocity_is_damped_towards_zero_over_frames():
    engine = SimulationEngine()
    creature = _make_adult(engine)
    # Velocidade puramente lateral (perpendicular ao heading, que esta em angle=0 -> eixo Y)
    creature.body.velocity = (0, 100.0)
    creature.motor_forward = 0.0
    creature.motor_torque = 0.0

    lateral_speeds = []
    for _ in range(10):
        creature.update(1 / 30.0, engine)
        local_velocity = creature.body.velocity.rotated(-creature.body.angle)
        lateral_speeds.append(abs(local_velocity.y))

    for earlier, later in zip(lateral_speeds, lateral_speeds[1:]):
        assert later <= earlier + 1e-9
    assert lateral_speeds[-1] < 1.0


def test_forward_velocity_is_preserved_by_grip():
    engine = SimulationEngine()
    creature = _make_adult(engine)
    creature.motor_forward = 1.0
    creature.motor_torque = 0.0

    creature.update(1 / 30.0, engine)

    local_velocity = creature.body.velocity.rotated(-creature.body.angle)
    assert local_velocity.x > 0.0


def test_egg_has_no_locomotion_or_grip_logic():
    engine = SimulationEngine()
    egg = Creature(engine)  # life_stage default = EGG
    egg.body.velocity = (0, 100.0)
    egg.motor_forward = 1.0
    egg.motor_torque = 1.0

    egg.update(1 / 30.0, engine)

    assert egg.body.velocity == pymunk.Vec2d(0, 100.0)


def test_smoke_full_simulation_runs_without_exception_with_grip_active():
    engine = SimulationEngine()
    for _ in range(10):
        engine.add_creature(Creature(engine))

    for _ in range(30):
        engine.step(1 / 30.0)
