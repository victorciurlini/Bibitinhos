# Testes do modo headless (BIT-28): populate(), HeadlessRunner e reprodutibilidade
# por seed. Convencao da suite: importar constantes/contratos, nunca hardcodar valores
# de balanceamento.

import random

import pytest

from simulation.engine import SimulationEngine
from simulation.runner import HeadlessRunner, populate, SIM_DT


@pytest.fixture(autouse=True)
def _preserva_random_global():
    """HeadlessRunner(seed=...) semeia o random GLOBAL (design do modo headless).
    Restaurar o estado apos cada teste evita que o resto da suite (que consome
    o stream global, ex.: spawn de oasis) veja um stream deslocado."""
    state = random.getstate()
    yield
    random.setstate(state)

# Contrato de compute_metrics() (BIT-26) — campos que todo snapshot deve ter.
METRICS_KEYS = {
    "time", "population", "stage_counts", "avg_energy", "avg_age",
    "births_total", "deaths_total", "food_count", "oases_count",
}


def test_populate():
    """populate(engine, 5) adiciona exatamente 5 criaturas."""
    engine = SimulationEngine()
    populate(engine, 5)
    assert len(engine.creatures) == 5


def test_runner_basic():
    """Run curto termina, retorna >= 2 snapshots com o contrato de metricas e time crescente."""
    runner = HeadlessRunner(seed=1)
    snapshots = runner.run(300)
    assert len(snapshots) >= 2
    for snap in snapshots:
        assert METRICS_KEYS.issubset(snap.keys())
    # tick 0 comeca em time=0; o ultimo snapshot avancou 300 * SIM_DT segundos simulados.
    assert snapshots[0]["time"] == 0.0
    assert abs(snapshots[-1]["time"] - 300 * SIM_DT) < 1e-6
    times = [s["time"] for s in snapshots]
    assert times == sorted(times)
    assert times[-1] > times[0]


def test_runner_snapshot_interval():
    """run(300, snapshot_interval=100) -> 4 snapshots (ticks 0/100/200/300), sem duplicata final."""
    runner = HeadlessRunner(seed=1)
    snapshots = runner.run(300, snapshot_interval=100)
    assert len(snapshots) == 4
    expected_times = [0.0, 100 * SIM_DT, 200 * SIM_DT, 300 * SIM_DT]
    for snap, expected in zip(snapshots, expected_times):
        assert abs(snap["time"] - expected) < 1e-6


def test_runner_deterministic():
    """Mesmo seed => series de snapshots identicas (toda aleatoriedade vem de random stdlib)."""
    snapshots_a = HeadlessRunner(seed=42).run(300)
    snapshots_b = HeadlessRunner(seed=42).run(300)
    assert snapshots_a == snapshots_b


def test_runner_on_snapshot_callback():
    """on_snapshot recebe (tick, snapshot) para cada snapshot periodico (tick 0 fora)."""
    runner = HeadlessRunner(seed=1)
    calls = []
    snapshots = runner.run(300, snapshot_interval=100,
                           on_snapshot=lambda t, s: calls.append((t, s)))
    assert [t for t, _ in calls] == [100, 200, 300]
    assert [s for _, s in calls] == snapshots[1:]
