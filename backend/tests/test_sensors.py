import math

import pytest

from simulation import engine as engine_module
from simulation.creature import Creature, LifeStage
from simulation.engine import SimulationEngine
from simulation.food import Food
from simulation.sensors import NUM_VISION_SECTORS, VISION_RADIUS, compute_vision


def make_engine_with_creature(angle=0.0):
    sim = SimulationEngine()
    creature = Creature(sim, x=1000, y=1000)
    creature.body.angle = angle
    sim.add_creature(creature)
    return sim, creature


def test_no_neighbors_returns_all_zero():
    sim, creature = make_engine_with_creature()
    vision = compute_vision(creature, sim)
    assert vision == [0.0] * NUM_VISION_SECTORS


def test_food_directly_ahead_activates_cone_zero():
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.energy = 0.0  # fome = 1.0
    cx, cy = creature.body.position
    food = Food(sim, cx + 50, cy)
    sim.add_food(food)

    vision = compute_vision(creature, sim)

    assert vision[0] == pytest.approx(1.0)
    assert sum(vision) == pytest.approx(1.0)


def test_food_directly_ahead_but_creature_full_energy_gives_no_signal():
    # Comida presente, mas criatura saciada nao tem "fome" -> sem sinal.
    # Comportamento documentado, nao e regressao.
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.energy = 100.0  # fome = 0.0
    cx, cy = creature.body.position
    food = Food(sim, cx + 50, cy)
    sim.add_food(food)

    vision = compute_vision(creature, sim)

    assert vision[0] == 0.0
    assert vision == [0.0] * NUM_VISION_SECTORS


def test_creature_directly_behind_activates_opposite_cone():
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.life_stage = LifeStage.ADULT
    creature.energy = 100.0  # mate_drive = 1.0
    cx, cy = creature.body.position
    other = Creature(sim, x=cx - 50, y=cy)
    sim.add_creature(other)

    vision = compute_vision(creature, sim)

    assert sum(vision) == pytest.approx(-1.0)
    active_indices = [i for i, v in enumerate(vision) if v == pytest.approx(-1.0)]
    assert active_indices[0] in (4, 5)


def test_creature_directly_behind_but_not_adult_gives_no_signal():
    # Criatura presente, mas observadora nao ADULT nao tem "interesse" -> vazio.
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.life_stage = LifeStage.JUVENILE
    creature.energy = 100.0
    cx, cy = creature.body.position
    other = Creature(sim, x=cx - 50, y=cy)
    sim.add_creature(other)

    vision = compute_vision(creature, sim)

    assert vision == [0.0] * NUM_VISION_SECTORS


def test_neighbor_outside_radius_does_not_activate_any_cone():
    sim, creature = make_engine_with_creature()
    cx, cy = creature.body.position
    far_x = cx + VISION_RADIUS + 50
    food = Food(sim, far_x, cy)
    sim.add_food(food)

    vision = compute_vision(creature, sim)

    assert vision == [0.0] * NUM_VISION_SECTORS


def test_creature_never_detects_itself():
    sim, creature = make_engine_with_creature()
    vision = compute_vision(creature, sim)
    assert vision == [0.0] * NUM_VISION_SECTORS


def test_food_and_creature_same_sector_food_wins():
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.life_stage = LifeStage.ADULT
    creature.energy = 50.0  # fome = 0.5, mate_drive = 0.5
    cx, cy = creature.body.position
    food = Food(sim, cx + 50, cy)
    sim.add_food(food)
    other = Creature(sim, x=cx + 60, y=cy)
    sim.add_creature(other)

    vision = compute_vision(creature, sim)

    assert vision[0] == pytest.approx(0.5)
    assert all(v >= 0 for v in vision)


def test_wall_near_map_edge_does_not_activate_any_cone():
    sim = SimulationEngine()
    creature = Creature(sim, x=10, y=1000)
    sim.add_creature(creature)

    vision = compute_vision(creature, sim)

    assert vision == [0.0] * NUM_VISION_SECTORS


def test_engine_step_only_recomputes_vision_at_brain_tick_rate(monkeypatch):
    sim, _creature = make_engine_with_creature()
    call_count = {"n": 0}

    def counting_compute_vision(creature, engine):
        call_count["n"] += 1
        return [0.0] * NUM_VISION_SECTORS

    monkeypatch.setattr(engine_module, "compute_vision", counting_compute_vision)

    for _ in range(3):
        sim.step(1 / 30.0)

    assert call_count["n"] <= 1
