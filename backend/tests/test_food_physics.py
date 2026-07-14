import pytest

from simulation.creature import Creature, CREATURE_MASS
from simulation.engine import SimulationEngine
from simulation.food import Food, FOOD_MASS


def test_food_mass_is_one_percent_of_creature_mass():
    assert FOOD_MASS == pytest.approx(CREATURE_MASS * 0.01)


def test_food_is_displaced_when_hit_by_a_moving_creature():
    engine = SimulationEngine()
    food = Food(engine, 1000, 1010)
    engine.add_food(food)
    creature = Creature(engine, x=1000, y=1000)
    creature.body.velocity = (0, 300.0)  # arremessada direto contra a comida
    engine.add_creature(creature)

    original_position = (food.body.position.x, food.body.position.y)

    for _ in range(10):
        engine.step(1 / 30.0)

    if food.is_active:
        moved = (
            (food.body.position.x - original_position[0]) ** 2
            + (food.body.position.y - original_position[1]) ** 2
        ) ** 0.5
        assert moved > 1.0


def test_food_without_any_force_stays_put():
    # Usa engine.physics.step() direto (nao engine.step()) para isolar a fisica
    # pura, sem disparar spawn de criaturas do Jardim do Eden (populacao == 0).
    engine = SimulationEngine()
    food = Food(engine, 1000, 1000)
    engine.add_food(food)

    for _ in range(30):
        engine.physics.step(1 / 30.0)

    assert food.body.position.x == pytest.approx(1000)
    assert food.body.position.y == pytest.approx(1000)


def test_smoke_full_simulation_runs_without_exception_with_dynamic_food():
    engine = SimulationEngine()
    for _ in range(10):
        engine.add_creature(Creature(engine))
    for _ in range(15):
        engine.add_food(Food(engine, 1000, 1000))

    for _ in range(30):
        engine.step(1 / 30.0)
