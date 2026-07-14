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


CENTER_SECTOR = NUM_VISION_SECTORS // 2  # setor 4: eixo central "para frente" do cone


def test_food_directly_ahead_activates_center_cone():
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.energy = 0.0  # fome = 1.0
    cx, cy = creature.body.position
    food = Food(sim, cx + 50, cy)
    sim.add_food(food)

    vision = compute_vision(creature, sim)

    assert vision[CENTER_SECTOR] == pytest.approx(1.0)
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

    assert vision[CENTER_SECTOR] == 0.0
    assert vision == [0.0] * NUM_VISION_SECTORS


def test_creature_directly_ahead_within_fov_activates_center_cone():
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.life_stage = LifeStage.ADULT
    creature.energy = 100.0  # mate_drive = 1.0
    cx, cy = creature.body.position
    other = Creature(sim, x=cx + 50, y=cy)
    sim.add_creature(other)

    vision = compute_vision(creature, sim)

    assert vision[CENTER_SECTOR] == pytest.approx(-1.0)
    assert sum(vision) == pytest.approx(-1.0)


def test_creature_directly_ahead_but_not_adult_gives_no_signal():
    # Criatura presente e dentro do cone, mas observadora nao ADULT nao tem
    # "interesse" -> vazio.
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.life_stage = LifeStage.JUVENILE
    creature.energy = 100.0
    cx, cy = creature.body.position
    other = Creature(sim, x=cx + 50, y=cy)
    sim.add_creature(other)

    vision = compute_vision(creature, sim)

    assert vision == [0.0] * NUM_VISION_SECTORS


def test_creature_directly_behind_is_outside_fov_no_signal():
    # Cone de visao e frontal (120 graus) — qualquer coisa as costas da
    # criatura (180 graus de diferenca) fica fora do cone, sem ativar setor.
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.life_stage = LifeStage.ADULT
    creature.energy = 100.0
    cx, cy = creature.body.position
    other = Creature(sim, x=cx - 50, y=cy)
    sim.add_creature(other)

    vision = compute_vision(creature, sim)

    assert vision == [0.0] * NUM_VISION_SECTORS


def test_food_just_outside_fov_edge_does_not_activate_any_cone():
    # 70 graus de uma criatura virada para angle=0.0 fica fora do cone de 120
    # graus (que cobre so ate +-60 graus a partir do eixo frontal).
    sim, creature = make_engine_with_creature(angle=0.0)
    creature.energy = 0.0  # fome maxima, para garantir que o teste realmente cobre o caso
    cx, cy = creature.body.position
    angle_rad = math.radians(70)
    food = Food(sim, cx + 50 * math.cos(angle_rad), cy + 50 * math.sin(angle_rad))
    sim.add_food(food)

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

    assert vision[CENTER_SECTOR] == pytest.approx(0.5)
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
