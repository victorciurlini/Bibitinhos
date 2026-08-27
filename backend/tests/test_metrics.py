import json

from simulation.creature import Creature, LifeStage
from simulation.engine import SimulationEngine
from simulation.metrics import (
    compute_metrics,
    METRICS_SAMPLE_INTERVAL,
    METRICS_HISTORY_MAX,
)

DT = 1 / 30.0


def _make_solo_adult(engine, x=700, y=700, energy=100.0, action_mate=True):
    """Adulto isolado (sem parceiro em alcance) — dispara a via assexuada quando fertil de energia."""
    c = Creature(engine, x=x, y=y)
    c.life_stage = LifeStage.ADULT
    c.action_mate = action_mate
    c.energy = energy
    engine.add_creature(c)
    return c


def _make_nearby_adult_pair(engine, x=700, y=700, offset=5, energy=100.0):
    """Dois adultos ferteis dentro de MATING_RADIUS — dispara a via sexuada por proximidade."""
    c1 = Creature(engine, x=x, y=y)
    c2 = Creature(engine, x=x + offset, y=y)
    for c in (c1, c2):
        c.life_stage = LifeStage.ADULT
        c.action_mate = True
        c.energy = energy
        c.is_fertile = True
    engine.add_creature(c1)
    engine.add_creature(c2)
    return c1, c2


def test_compute_metrics_empty_engine_returns_zeros():
    # Engine recem-criado, sem criaturas/comida/oasis: agregados zerados, sem ZeroDivisionError.
    engine = SimulationEngine()
    m = compute_metrics(engine)

    assert m["population"] == 0
    assert m["stage_counts"] == {"EGG": 0, "JUVENILE": 0, "ADULT": 0, "ELDER": 0}
    assert m["avg_energy"] == 0.0
    assert m["avg_age"] == 0.0
    assert m["births_total"] == 0
    assert m["deaths_total"] == 0
    assert m["food_count"] == 0
    assert m["oases_count"] == 0
    assert m["time"] == engine.time_elapsed


def test_compute_metrics_counts_population_and_stages():
    engine = SimulationEngine()
    egg = Creature(engine, x=100, y=100)  # nasce EGG
    adult = Creature(engine, x=500, y=500)
    adult.life_stage = LifeStage.ADULT
    engine.add_creature(egg)
    engine.add_creature(adult)

    m = compute_metrics(engine)

    assert m["population"] == 2
    assert m["stage_counts"]["EGG"] == 1
    assert m["stage_counts"]["ADULT"] == 1
    assert m["avg_energy"] == (egg.energy + adult.energy) / 2


def test_deaths_total_increments_when_creature_starves():
    engine = SimulationEngine()
    doomed = _make_solo_adult(engine, energy=0.0, action_mate=False)
    # Energia 0: o update() do step desconta metabolismo, is_alive vira False e a remocao conta.
    engine.step(DT)

    assert not doomed.is_alive
    assert doomed not in engine.creatures
    assert engine.deaths_total == 1


def test_births_total_increments_on_asexual_reproduction():
    engine = SimulationEngine()
    _make_solo_adult(engine, energy=100.0)

    engine.step(DT)

    assert engine.births_total == 1


def test_births_total_increments_on_sexual_reproduction():
    engine = SimulationEngine()
    c1, c2 = _make_nearby_adult_pair(engine, energy=100.0)

    engine.step(DT)

    assert c1.sought_mate_this_frame and c2.sought_mate_this_frame
    assert engine.births_total == 1


def test_metrics_history_samples_once_per_simulated_second():
    engine = SimulationEngine()
    engine.add_creature(Creature(engine, x=700, y=700))

    # dt=0.5 e exato em binario: 3 s simulados sem acumulo de erro de float na amostragem.
    dt = 0.5
    steps = int(round(3.0 / dt))
    for _ in range(steps):
        engine.step(dt)

    expected_samples = int(3.0 / METRICS_SAMPLE_INTERVAL)
    assert len(engine.metrics_history) == expected_samples
    times = [sample["time"] for sample in engine.metrics_history]
    assert times == sorted(times)
    assert all(t2 > t1 for t1, t2 in zip(times, times[1:]))


def test_metrics_history_is_capped():
    engine = SimulationEngine()
    assert engine.metrics_history.maxlen == METRICS_HISTORY_MAX


def test_get_state_includes_json_serializable_metrics():
    engine = SimulationEngine()
    engine.add_creature(Creature(engine, x=700, y=700))
    engine.step(DT)

    state = engine.get_state()

    assert "metrics" in state
    m = state["metrics"]
    for key in ("time", "population", "stage_counts", "avg_energy", "avg_age",
                "births_total", "deaths_total", "food_count", "oases_count"):
        assert key in m
    json.dumps(m)  # nao pode levantar TypeError


def test_metrics_history_endpoint_payload():
    # Chama o handler REST direto (sem TestClient: starlette 0.27 + httpx 0.28 nao convivem).
    import main

    payload = main.metrics_history()

    assert "history" in payload
    assert isinstance(payload["history"], list)
    json.dumps(payload)
