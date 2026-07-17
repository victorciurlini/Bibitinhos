# Modo headless (BIT-28): roda o engine sem servidor/frontend, em velocidade maxima.
# populate() e o bootstrap unico da populacao inicial (reutilizado pelo startup_event
# do main.py); HeadlessRunner empacota engine + loop sincrono + snapshots de metricas.

import random

from simulation.creature import Creature
from simulation.metrics import compute_metrics

SIM_DT = 1 / 30.0  # mesmo dt fixo do simulation_loop (BIT-24: dt nunca muda)


def populate(engine, count=10):
    """Bootstrap da populacao inicial (Gen 0)."""
    for _ in range(count):
        engine.add_creature(Creature(engine))


class HeadlessRunner:
    """Roda o engine sem servidor: loop sincrono em velocidade maxima."""

    def __init__(self, initial_creatures=10, seed=None):
        if seed is not None:
            random.seed(seed)
        # Import tardio: o seed precisa valer antes de qualquer aleatoriedade
        # consumida na construcao do engine/criaturas.
        from simulation.engine import SimulationEngine
        self.engine = SimulationEngine()
        populate(self.engine, initial_creatures)

    def run(self, ticks, snapshot_interval=300, on_snapshot=None):
        """Executa `ticks` steps de SIM_DT; snapshot de metricas a cada
        `snapshot_interval` ticks (e um final, sem duplicar quando o ultimo
        tick coincide com o intervalo). Retorna a lista de snapshots."""
        snapshots = [compute_metrics(self.engine)]  # tick 0
        for t in range(1, ticks + 1):
            self.engine.step(SIM_DT)
            if t % snapshot_interval == 0 or t == ticks:
                snap = compute_metrics(self.engine)
                snapshots.append(snap)
                if on_snapshot:
                    on_snapshot(t, snap)
        return snapshots
