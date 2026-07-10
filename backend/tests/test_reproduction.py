import pytest

import simulation.engine as engine_module
from simulation.creature import Creature, LifeStage, METABOLISM_RATE_BY_STAGE
from simulation.engine import SimulationEngine, REPRODUCTION_ENERGY_COST, MIN_ENERGY_TO_MATE

DT = 1 / 30.0


def _make_adult_pair(engine, x=1000, y=1000, offset=5, energy=100.0, action_mate=True):
    """Cria duas criaturas ADULT sobrepostas (mesma vizinhanca), prontas para colidir."""
    c1 = Creature(engine, x=x, y=y)
    c2 = Creature(engine, x=x + offset, y=y)
    for c in (c1, c2):
        c.life_stage = LifeStage.ADULT
        c.action_mate = action_mate
        c.energy = energy
    engine.add_creature(c1)
    engine.add_creature(c2)
    return c1, c2


def test_adult_pair_with_action_mate_reproduces_on_collision():
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine)

    count_before = len(engine.creatures)
    engine.step(1 / 30.0)

    assert len(engine.creatures) == count_before + 1
    child = [c for c in engine.creatures if c not in (c1, c2)][0]
    assert child.life_stage == LifeStage.EGG
    expected = 100.0 - REPRODUCTION_ENERGY_COST - DT * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]
    assert c1.energy == pytest.approx(expected)
    assert c2.energy == pytest.approx(expected)
    assert c1.mate_cooldown > 0
    assert c2.mate_cooldown > 0


def test_child_genome_comes_from_crossover_and_mutation_not_zero_genome(monkeypatch):
    # Espiona organic_crossover/mutate_genome (funcoes ja testadas isoladamente em
    # test_rtneat_wrapper.py) para confirmar que o handler realmente as invoca com
    # os genomas dos pais, em vez de comparar estrutura de conexoes — que seria
    # flaky, pois mutate_genome pode adicionar/remover conexoes estocasticamente.
    calls = {}
    original_crossover = engine_module.organic_crossover
    original_mutate = engine_module.mutate_genome

    def spy_crossover(genome1, genome2, genome_id, config):
        calls["crossover_parents"] = (genome1, genome2)
        result = original_crossover(genome1, genome2, genome_id, config)
        calls["crossover_result"] = result
        return result

    def spy_mutate(genome, config):
        calls["mutated_genome"] = genome
        return original_mutate(genome, config)

    monkeypatch.setattr(engine_module, "organic_crossover", spy_crossover)
    monkeypatch.setattr(engine_module, "mutate_genome", spy_mutate)

    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine)

    engine.step(1 / 30.0)

    # A ordem de arbiter.shapes nao e garantida pelo pymunk (pode vir (c1, c2) ou
    # (c2, c1)); o handler e simetrico, entao aceitamos as duas ordens.
    assert set(calls["crossover_parents"]) == {c1.genome, c2.genome}
    assert calls["mutated_genome"] is calls["crossover_result"]

    child = [c for c in engine.creatures if c not in (c1, c2)][0]
    assert child.genome is calls["mutated_genome"]


def test_action_mate_false_prevents_reproduction():
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine)
    c2.action_mate = False

    count_before = len(engine.creatures)
    engine.step(1 / 30.0)

    assert len(engine.creatures) == count_before
    assert c1.energy == pytest.approx(100.0 - DT * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])
    assert c2.energy == pytest.approx(100.0 - DT * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])


def test_juvenile_prevents_reproduction():
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine)
    c2.life_stage = LifeStage.JUVENILE

    count_before = len(engine.creatures)
    engine.step(1 / 30.0)

    assert len(engine.creatures) == count_before
    assert c1.energy == pytest.approx(100.0 - DT * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])
    assert c2.energy == pytest.approx(100.0 - DT * METABOLISM_RATE_BY_STAGE[LifeStage.JUVENILE])


def test_low_energy_prevents_reproduction():
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine)
    c2.energy = MIN_ENERGY_TO_MATE - 1.0

    count_before = len(engine.creatures)
    engine.step(1 / 30.0)

    assert len(engine.creatures) == count_before
    assert c1.energy == pytest.approx(100.0 - DT * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])
    assert c2.energy == pytest.approx(MIN_ENERGY_TO_MATE - 1.0 - DT * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])


def test_cooldown_prevents_repeated_reproduction_across_consecutive_steps():
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine)
    # think() roda no brain tick (10 FPS) e recalcularia action_mate a partir da
    # rede (saida estocastica no genoma zero) — stub para manter action_mate=True
    # fixo e testar isoladamente a logica de cooldown, nao a rede neural.
    c1.think = lambda engine: None
    c2.think = lambda engine: None

    count_before = len(engine.creatures)
    # Forca as duas criaturas a permanecerem sobrepostas por varios steps seguidos,
    # simulando "colisao continua" (pymunk chama begin novamente a cada novo contato).
    for _ in range(10):
        c1.body.position = (1000, 1000)
        c2.body.position = (1005, 1000)
        c1.body.velocity = (0, 0)
        c2.body.velocity = (0, 0)
        engine.step(1 / 30.0)

    children_born = len(engine.creatures) - count_before
    assert children_born == 1


def test_smoke_full_simulation_runs_without_exception_with_reproduction_active():
    engine = SimulationEngine()
    for _ in range(10):
        c = Creature(engine, x=1000, y=1000)
        c.life_stage = LifeStage.ADULT
        c.action_mate = True
        c.energy = 100.0
        # Idem: stub de think() para manter action_mate=True fixo, isolando o
        # smoke test da aleatoriedade da rede neural do genoma zero.
        c.think = lambda engine: None
        engine.add_creature(c)

    for _ in range(30):
        engine.step(1 / 30.0)

    # Cooldown deve impedir crescimento explosivo (uma nova criatura por colisao
    # a cada frame); a populacao cresce, mas de forma limitada.
    assert len(engine.creatures) < 200
