# Metricas populacionais agregadas (BIT-26). O backend e a fonte canonica: os agregados
# correntes viajam no state_update e o historico amostrado (1 amostra por segundo simulado,
# deque com cap) fica no engine, exposto via GET /metrics/history para bootstrap do painel.
# Funcao pura sobre o estado do engine — sem estado proprio, sem dependencias novas.

METRICS_SAMPLE_INTERVAL = 1.0   # segundos simulados entre amostras do historico
METRICS_HISTORY_MAX = 600       # ~10 min de historia


def compute_metrics(engine):
    """Agregados populacionais do estado corrente do engine (JSON-safe)."""
    creatures = engine.creatures
    n = len(creatures)
    stage_counts = {"EGG": 0, "JUVENILE": 0, "ADULT": 0, "ELDER": 0}
    for c in creatures:
        stage_counts[c.life_stage.name] += 1
    return {
        "time": engine.time_elapsed,
        "population": n,
        "stage_counts": stage_counts,
        "avg_energy": (sum(c.energy for c in creatures) / n) if n else 0.0,
        "avg_age": (sum(c.age for c in creatures) / n) if n else 0.0,
        "births_total": engine.births_total,
        "deaths_total": engine.deaths_total,
        "food_count": len(engine.foods),
        "oases_count": len(engine.oases),
    }
