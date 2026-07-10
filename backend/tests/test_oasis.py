import random

import pytest

from simulation.engine import SimulationEngine
from simulation.oasis import Oasis
from simulation.food import Food
from simulation.creature import Creature, LifeStage


def test_oasis_expires_when_ttl_reaches_zero():
    engine = SimulationEngine()
    engine.oases.append(Oasis(100, 100, ttl=0.05))

    engine.step(1 / 30.0)
    assert len(engine.oases) == 1

    engine.step(1 / 30.0)
    assert len(engine.oases) == 0


def test_food_only_spawns_inside_active_oasis(monkeypatch):
    engine = SimulationEngine()
    engine.creatures = []
    engine.oases = [Oasis(500, 500, radius=50.0, ttl=100.0, food_cap=10)]

    # Impede o nascimento de novos oasis aleatorios e garante spawn de comida
    # a cada frame (enquanto sob o cap), isolando o teste ao unico oasis controlado.
    monkeypatch.setattr("simulation.engine.OASIS_SPAWN_CHANCE_PER_FRAME", 0.0)
    monkeypatch.setattr("simulation.engine.OASIS_FOOD_SPAWN_CHANCE", 1.0)

    for _ in range(5):
        engine.step(1 / 30.0)

    assert len(engine.foods) > 0
    for food in engine.foods:
        dx = food.body.position.x - 500
        dy = food.body.position.y - 500
        assert dx * dx + dy * dy <= 50.0 ** 2 + 1e-6


def test_no_food_spawns_without_active_oasis(monkeypatch):
    engine = SimulationEngine()
    engine.creatures = []
    engine.oases = []

    # Impede o nascimento de qualquer oasis novo: o teste cobre especificamente
    # "sem oasis ativo, nao nasce comida" (nao "oasis nunca nasce sozinho").
    monkeypatch.setattr("simulation.engine.OASIS_SPAWN_CHANCE_PER_FRAME", 0.0)

    for _ in range(10):
        engine.step(1 / 30.0)

    assert len(engine.foods) == 0


def test_oasis_food_cap_is_respected():
    engine = SimulationEngine()
    engine.creatures = []
    oasis = Oasis(500, 500, radius=50.0, ttl=100.0, food_cap=2)
    engine.oases = [oasis]

    engine.add_food(Food(engine, 500, 500))
    engine.add_food(Food(engine, 505, 505))

    # Cap ja atingido (2/2): a checagem "food_in_oasis < food_cap" e exata,
    # nao probabilistica, entao nenhuma comida nova deve nascer nesse oasis
    # independente de quantos frames rodarem.
    random.seed(1)
    for _ in range(30):
        engine.step(1 / 30.0)

    foods_in_oasis = [
        f for f in engine.foods
        if (f.body.position.x - 500) ** 2 + (f.body.position.y - 500) ** 2 <= 50.0 ** 2
    ]
    assert len(foods_in_oasis) == 2


def test_eden_triggers_dense_oasis_per_survivor_below_threshold():
    engine = SimulationEngine()
    engine.creatures = [Creature(engine, x=100 + i * 10, y=100) for i in range(5)]
    for c in engine.creatures:
        c.life_stage = LifeStage.ADULT

    engine.step(1 / 30.0)

    assert len(engine.oases) == 5
    assert engine._eden_active is True


def test_eden_does_not_retrigger_every_frame_while_population_stays_low():
    engine = SimulationEngine()
    engine.creatures = [Creature(engine, x=100 + i * 10, y=100) for i in range(5)]
    for c in engine.creatures:
        c.life_stage = LifeStage.ADULT

    engine.step(1 / 30.0)
    oases_after_first_trigger = len(engine.oases)

    for _ in range(10):
        engine.step(1 / 30.0)

    # nenhum oasis novo do Jardim do Eden deve ter sido empilhado (histerese)
    assert len([o for o in engine.oases if o.radius == pytest.approx(200.0)]) <= oases_after_first_trigger


def test_eden_retriggers_after_population_recovers_above_threshold():
    engine = SimulationEngine()
    engine.creatures = [Creature(engine, x=100 + i * 10, y=100) for i in range(5)]
    for c in engine.creatures:
        c.life_stage = LifeStage.ADULT

    engine.step(1 / 30.0)
    assert engine._eden_active is True

    for i in range(10):
        engine.add_creature(Creature(engine, x=200 + i * 10, y=200))
    engine.step(1 / 30.0)
    assert engine._eden_active is False

    engine.creatures = engine.creatures[:5]
    for c in engine.creatures:
        c.life_stage = LifeStage.ADULT
    engine.step(1 / 30.0)
    assert engine._eden_active is True


def test_population_zero_fallback_still_respawns_ten_creatures():
    engine = SimulationEngine()
    engine.creatures = []

    engine.step(1 / 30.0)

    assert len(engine.creatures) == 10
    assert engine._eden_active is False


def test_get_state_includes_oases_field():
    engine = SimulationEngine()
    engine.oases.append(Oasis(10, 10, ttl=5.0))

    state = engine.get_state()

    assert "oases" in state
    assert state["oases"] == [{"x": 10, "y": 10, "radius": 150.0, "ttl": 5.0}]
