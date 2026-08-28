import pytest

from simulation.creature import Creature, HELD_FOOD_CONSUME_ENERGY_FRACTION
from simulation.engine import SimulationEngine
from simulation.food import Food, FOOD_TTL, FOOD_ENERGY_VALUE


def _make_engine_with_creature_and_food(creature_energy=100.0, food_x=1000, food_y=1000):
    """Cria engine, criatura e comida sobrepostos para forçar colisão no primeiro step."""
    engine = SimulationEngine()
    creature = Creature(engine, x=1000, y=1000)
    creature.energy = creature_energy
    engine.add_creature(creature)
    food = Food(engine, food_x, food_y)
    engine.add_food(food)
    return engine, creature, food


def test_grab_instead_of_eat():
    """action_grab_drop=True + slot livre: pega em vez de comer."""
    engine, creature, food = _make_engine_with_creature_and_food(creature_energy=100.0)
    creature.action_grab_drop = True

    energy_before = creature.energy
    engine.step(1 / 30.0)

    assert creature.is_holding is True
    assert creature.held_food is food
    assert food.body not in engine.physics.space.bodies
    assert creature.energy == pytest.approx(energy_before, abs=1.0)  # energia não sobe por comer
    assert creature.food_grabbed == 1


def test_normal_eat_when_not_grabbing():
    """action_grab_drop=False: comer no contato (comportamento preservado)."""
    engine, creature, food = _make_engine_with_creature_and_food(creature_energy=50.0)
    creature.action_grab_drop = False

    engine.step(1 / 30.0)

    assert creature.is_holding is False
    assert creature.held_food is None
    assert food.is_active is False
    assert creature.energy > 50.0


def test_ttl_pauses_while_held():
    """Comida carregada não apodrece (TTL pausa)."""
    engine = SimulationEngine()
    creature = Creature(engine, x=1000, y=1000)
    creature.energy = 100.0
    creature.action_grab_drop = True
    engine.add_creature(creature)
    food = Food(engine, 1000, 1000)
    engine.add_food(food)

    # Pega a comida
    engine.step(1 / 30.0)
    assert creature.is_holding is True

    # Avança mais que o FOOD_TTL completo em steps
    steps = int(FOOD_TTL / (1 / 30.0)) + 10
    # Garante que não vai consumir por fome (mantém energia alta)
    for _ in range(steps):
        creature.energy = 100.0
        creature.action_grab_drop = True
        engine.step(1 / 30.0)

    assert food.is_active is True
    assert creature.is_holding is True


def test_consumes_held_food_when_hungry():
    """Carregando + energia abaixo do limiar: consome automaticamente."""
    engine = SimulationEngine()
    creature = Creature(engine, x=1000, y=1000)
    creature.energy = 100.0
    creature.action_grab_drop = True
    engine.add_creature(creature)
    food = Food(engine, 1000, 1000, energy_value=FOOD_ENERGY_VALUE)
    engine.add_food(food)

    # Pega a comida
    engine.step(1 / 30.0)
    assert creature.is_holding is True

    food_eaten_before = creature.food_eaten
    # Força energia abaixo do limiar de consumo
    creature.energy = HELD_FOOD_CONSUME_ENERGY_FRACTION * creature.max_energy - 1.0
    creature.action_grab_drop = True  # mantém ativo (consumo é por fome, não por drop)
    engine.step(1 / 30.0)

    assert creature.is_holding is False
    assert creature.held_food is None
    assert creature.energy > HELD_FOOD_CONSUME_ENERGY_FRACTION * creature.max_energy - 1.0
    assert creature.food_eaten == food_eaten_before + 1


def test_drops_when_signal_low():
    """action_grab_drop=False + energia acima do limiar: solta a comida de volta ao mundo."""
    engine = SimulationEngine()
    creature = Creature(engine, x=1000, y=1000)
    creature.energy = 100.0
    creature.action_grab_drop = True
    engine.add_creature(creature)
    food = Food(engine, 1000, 1000)
    engine.add_food(food)

    # Pega a comida
    engine.step(1 / 30.0)
    assert creature.is_holding is True

    # Sinal cai, energia alta (sem fome)
    creature.action_grab_drop = False
    creature.energy = 100.0
    engine.step(1 / 30.0)

    assert creature.is_holding is False
    assert creature.held_food is None
    assert food.is_held is False
    assert food.body in engine.physics.space.bodies


def test_drops_on_death():
    """Criatura que morre carregando solta a comida de volta ao mundo."""
    engine = SimulationEngine()
    creature = Creature(engine, x=1000, y=1000)
    creature.energy = 100.0
    creature.action_grab_drop = True
    engine.add_creature(creature)
    food = Food(engine, 1000, 1000)
    engine.add_food(food)

    # Pega a comida
    engine.step(1 / 30.0)
    assert creature.is_holding is True

    # Zera a energia e deixa o engine processar a morte
    creature.energy = 0.0
    creature.is_alive = False
    engine.step(1 / 30.0)

    assert food.is_active is True
    assert food.is_held is False
    assert food in engine.foods


def test_single_slot_no_swap():
    """Já carregando: novo contato com comida não substitui o item no slot."""
    engine = SimulationEngine()
    creature = Creature(engine, x=1000, y=1000)
    creature.energy = 100.0
    creature.action_grab_drop = True
    engine.add_creature(creature)

    food1 = Food(engine, 1000, 1000)
    engine.add_food(food1)

    # Pega o primeiro item
    engine.step(1 / 30.0)
    assert creature.is_holding is True
    held = creature.held_food

    # Adiciona segunda comida na mesma posição; slot já ocupado
    food2 = Food(engine, 1000, 1000)
    engine.add_food(food2)
    creature.energy = 100.0
    creature.action_grab_drop = True
    engine.step(1 / 30.0)

    # O item carregado não muda
    assert creature.held_food is held
    assert creature.food_grabbed == 1
