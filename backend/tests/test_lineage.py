import json

from simulation.creature import Creature, LifeStage
from simulation.engine import (
    SimulationEngine,
    MIN_ENERGY_TO_REPRODUCE_ASEXUALLY,
    ASEXUAL_REPRODUCTION_ENERGY_COST,
    MATING_RADIUS,
    REPRODUCTION_ENERGY_COST,
)
from simulation.food import Food
from simulation.metrics import compute_metrics

DT = 1 / 30.0


def _make_adult(engine, x=700, y=700, energy=100.0, action_mate=False):
    c = Creature(engine, x=x, y=y)
    c.life_stage = LifeStage.ADULT
    c.energy = energy
    c.action_mate = action_mate
    c.is_fertile = True
    c.has_eaten = True
    engine.add_creature(c)
    return c


# ---------------------------------------------------------------------------
# Atributos iniciais
# ---------------------------------------------------------------------------

def test_new_creature_defaults():
    engine = SimulationEngine()
    c = Creature(engine)
    assert c.generation == 0
    assert c.food_eaten == 0
    assert c.children_count == 0


def test_explicit_generation_zero():
    engine = SimulationEngine()
    c = Creature(engine, generation=0)
    assert c.generation == 0


def test_creature_with_positive_generation():
    engine = SimulationEngine()
    c = Creature(engine, generation=5)
    assert c.generation == 5


# ---------------------------------------------------------------------------
# Reprodução sexuada
# ---------------------------------------------------------------------------

def test_sexual_child_generation_is_max_parents_plus_one():
    engine = SimulationEngine()
    c1 = _make_adult(engine, x=700, y=700, energy=100.0, action_mate=True)
    c2 = _make_adult(engine, x=705, y=700, energy=100.0, action_mate=True)
    c1.generation = 3
    c2.generation = 5  # max = 5 → child deve ser 6

    engine.step(DT)

    children = [c for c in engine.creatures if c not in (c1, c2)]
    assert len(children) == 1
    assert children[0].generation == 6


def test_sexual_reproduction_increments_children_count_on_both_parents():
    engine = SimulationEngine()
    c1 = _make_adult(engine, x=700, y=700, energy=100.0, action_mate=True)
    c2 = _make_adult(engine, x=705, y=700, energy=100.0, action_mate=True)

    engine.step(DT)

    assert c1.children_count == 1
    assert c2.children_count == 1


# ---------------------------------------------------------------------------
# Reprodução assexuada
# ---------------------------------------------------------------------------

def test_asexual_child_generation_is_parent_plus_one():
    engine = SimulationEngine()
    c = _make_adult(engine, x=700, y=700,
                    energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY + 1.0,
                    action_mate=True)
    c.generation = 4
    # Garantir que nao haja parceiro para reproducao sexuada
    assert len([x for x in engine.creatures if x is not c]) == 0

    engine.step(DT)

    children = [x for x in engine.creatures if x is not c]
    assert len(children) == 1
    assert children[0].generation == 5


def test_asexual_reproduction_increments_children_count():
    engine = SimulationEngine()
    c = _make_adult(engine, x=700, y=700,
                    energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY + 1.0,
                    action_mate=True)

    engine.step(DT)

    assert c.children_count == 1


# ---------------------------------------------------------------------------
# Colisão com comida
# ---------------------------------------------------------------------------

def test_food_collision_increments_food_eaten():
    engine = SimulationEngine()
    c = Creature(engine, x=1000, y=1000)
    c.energy = 50.0
    engine.add_creature(c)
    food = Food(engine, 1000, 1000)
    engine.add_food(food)

    assert c.food_eaten == 0
    engine.step(DT)
    assert c.food_eaten == 1


def test_food_eaten_not_incremented_without_collision():
    engine = SimulationEngine()
    c = Creature(engine, x=100, y=100)
    c.energy = 50.0
    engine.add_creature(c)
    food = Food(engine, 1300, 1300)  # canto oposto do mapa
    engine.add_food(food)

    engine.step(DT)
    assert c.food_eaten == 0


# ---------------------------------------------------------------------------
# Morte e lifespan
# ---------------------------------------------------------------------------

def test_death_accumulates_lifespan_sum():
    engine = SimulationEngine()
    c = Creature(engine, x=700, y=700)
    c.life_stage = LifeStage.ADULT
    c.age = 20.0
    c.energy = 0.001  # vai morrer no proximo step por energia
    c.is_alive = True
    engine.add_creature(c)

    assert engine._lifespan_sum == 0.0
    engine.step(DT)

    assert engine.deaths_total >= 1
    assert engine._lifespan_sum > 0.0


def test_avg_lifespan_in_metrics_after_death():
    engine = SimulationEngine()
    c = Creature(engine, x=700, y=700)
    c.life_stage = LifeStage.ADULT
    c.age = 15.0
    c.energy = 0.001
    c.is_alive = True
    engine.add_creature(c)
    engine.step(DT)

    metrics = compute_metrics(engine)
    assert metrics["avg_lifespan"] > 0.0
    assert metrics["avg_lifespan"] == engine._lifespan_sum / engine.deaths_total


# ---------------------------------------------------------------------------
# Extinção
# ---------------------------------------------------------------------------

def test_extinction_increments_extinctions_total():
    engine = SimulationEngine()
    # Nenhuma criatura → forcar extinção
    assert engine.extinctions_total == 0
    engine.step(DT)  # populacao == 0 no inicio do bloco do Eden → incrementa
    assert engine.extinctions_total == 1


def test_extinction_reseeds_with_generation_zero():
    engine = SimulationEngine()
    engine.step(DT)  # extincao: re-semeadura

    assert len(engine.creatures) == 10
    for c in engine.creatures:
        assert c.generation == 0


def test_multiple_extinctions_accumulate():
    engine = SimulationEngine()
    engine.step(DT)  # 1a extincao
    # matar todas as criaturas re-semeadas para forcar 2a extincao
    for c in engine.creatures:
        c.is_alive = False
    engine.step(DT)  # 2a extincao

    assert engine.extinctions_total == 2


# ---------------------------------------------------------------------------
# compute_metrics: 4 campos de linhagem
# ---------------------------------------------------------------------------

def test_compute_metrics_includes_lineage_fields():
    engine = SimulationEngine()
    c = _make_adult(engine, x=700, y=700)
    c.generation = 3

    metrics = compute_metrics(engine)

    assert "max_generation" in metrics
    assert "avg_generation" in metrics
    assert "extinctions_total" in metrics
    assert "avg_lifespan" in metrics


def test_compute_metrics_max_generation():
    engine = SimulationEngine()
    c1 = _make_adult(engine, x=700, y=700)
    c1.generation = 2
    c2 = _make_adult(engine, x=800, y=800)
    c2.generation = 7

    metrics = compute_metrics(engine)
    assert metrics["max_generation"] == 7


def test_compute_metrics_avg_generation():
    engine = SimulationEngine()
    c1 = _make_adult(engine, x=700, y=700)
    c1.generation = 2
    c2 = _make_adult(engine, x=800, y=800)
    c2.generation = 4

    metrics = compute_metrics(engine)
    assert metrics["avg_generation"] == 3.0


def test_compute_metrics_empty_population_zero_defaults():
    engine = SimulationEngine()
    metrics = compute_metrics(engine)
    assert metrics["max_generation"] == 0
    assert metrics["avg_generation"] == 0.0
    assert metrics["avg_lifespan"] == 0.0


def test_compute_metrics_json_serializable():
    engine = SimulationEngine()
    _make_adult(engine, x=700, y=700)
    metrics = compute_metrics(engine)
    json.dumps(metrics)  # nao deve levantar excecao


# ---------------------------------------------------------------------------
# to_dict expõe os campos de linhagem
# ---------------------------------------------------------------------------

def test_to_dict_exposes_lineage_fields():
    engine = SimulationEngine()
    c = Creature(engine, generation=3)
    c.food_eaten = 5
    c.children_count = 2

    d = c.to_dict()
    assert d["generation"] == 3
    assert d["food_eaten"] == 5
    assert d["children_count"] == 2
