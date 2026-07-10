from simulation.creature import Creature
from simulation.engine import SimulationEngine
from simulation.food import Food


def test_collision_transfers_energy_and_consumes_food():
    engine = SimulationEngine()
    creature = Creature(engine, x=1000, y=1000)
    creature.energy = 50.0
    engine.add_creature(creature)
    food = Food(engine, 1000, 1000, energy_value=20.0)  # mesma posicao: shapes sobrepostos
    engine.add_food(food)

    engine.step(1 / 30.0)

    assert creature.energy == 70.0
    assert food not in engine.foods
    assert food.is_active is False


def test_energy_gain_capped_at_max_energy():
    engine = SimulationEngine()
    creature = Creature(engine, x=1000, y=1000)
    creature.energy = 95.0
    creature.max_energy = 100.0
    engine.add_creature(creature)
    food = Food(engine, 1000, 1000, energy_value=50.0)  # muito maior que o espaco livre ate o teto
    engine.add_food(food)

    engine.step(1 / 30.0)

    assert creature.energy == 100.0


def test_far_apart_creature_and_food_do_not_interact():
    engine = SimulationEngine()
    creature = Creature(engine, x=100, y=100)
    creature.energy = 50.0
    engine.add_creature(creature)
    food = Food(engine, 1900, 1900, energy_value=20.0)  # canto oposto do mapa 2000x2000
    engine.add_food(food)

    engine.step(1 / 30.0)

    assert creature.energy == 50.0
    assert food in engine.foods
    assert food.is_active is True


def test_smoke_full_simulation_runs_without_exception_with_feeding_active():
    engine = SimulationEngine()
    for _ in range(10):
        engine.add_creature(Creature(engine))
    for _ in range(15):
        engine.add_food(Food(engine, 1000, 1000))  # aglomeradas para forcar colisoes

    for _ in range(20):
        engine.step(1 / 30.0)
