import pytest

import simulation.engine as engine_module
from simulation.creature import Creature, LifeStage, METABOLISM_RATE_BY_STAGE, IDLE_PENALTY_RATE
from simulation.engine import (
    SimulationEngine,
    REPRODUCTION_ENERGY_COST,
    MATING_RADIUS,
    MIN_ENERGY_TO_REPRODUCE_ASEXUALLY,
)

DT = 1 / 30.0

# Energia elegivel para acasalar (> piso de sobrevivencia) mas ABAIXO do limiar da clonagem, para que
# os testes de "nao acasala sexuadamente" nao sejam mascarados por um filho assexuado.
SUB_ASEXUAL_ENERGY = MIN_ENERGY_TO_REPRODUCE_ASEXUALLY - 5.0


def _make_adult_pair(engine, x=700, y=700, offset=5, energy=100.0, action_mate=True,
                     is_fertile=True):
    """Cria duas criaturas ADULT ferteis dentro de MATING_RADIUS, prontas para acasalar.

    BIT-22: a reproducao sexuada passou a ser por PROXIMIDADE + fertilidade persistente, nao mais
    por colisao fisica exata no mesmo frame. offset << MATING_RADIUS mantem o par dentro do raio.
    """
    c1 = Creature(engine, x=x, y=y)
    c2 = Creature(engine, x=x + offset, y=y)
    for c in (c1, c2):
        c.life_stage = LifeStage.ADULT
        c.action_mate = action_mate
        c.energy = energy
        c.is_fertile = is_fertile
    engine.add_creature(c1)
    engine.add_creature(c2)
    return c1, c2


def test_adult_pair_within_radius_reproduces():
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before + 1
    child = [c for c in engine.creatures if c not in (c1, c2)][0]
    assert child.life_stage == LifeStage.EGG
    expected = 100.0 - REPRODUCTION_ENERGY_COST - DT * (METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] + IDLE_PENALTY_RATE)
    assert c1.energy == pytest.approx(expected)
    assert c2.energy == pytest.approx(expected)
    assert c1.reproduction_cooldown > 0
    assert c2.reproduction_cooldown > 0
    # A fertilidade e consumida no acasalamento; re-conquista-se comendo de novo.
    assert not c1.is_fertile
    assert not c2.is_fertile


def test_child_genome_comes_from_crossover_and_mutation_not_zero_genome(monkeypatch):
    # Espiona organic_crossover/mutate_genome (funcoes ja testadas isoladamente em
    # test_rtneat_wrapper.py) para confirmar que o scan sexual realmente as invoca com
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

    engine.step(DT)

    assert set(calls["crossover_parents"]) == {c1.genome, c2.genome}
    assert calls["mutated_genome"] is calls["crossover_result"]

    child = [c for c in engine.creatures if c not in (c1, c2)][0]
    assert child.genome is calls["mutated_genome"]


def test_action_mate_false_prevents_reproduction():
    # Energia abaixo do limiar da clonagem para que o resultado isole o gate sexual (sem filho
    # assexuado mascarando). c1 quer acasalar mas c2 recusa -> ninguem nasce.
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine, energy=SUB_ASEXUAL_ENERGY)
    c2.action_mate = False

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before
    assert c1.energy == pytest.approx(SUB_ASEXUAL_ENERGY - DT * (METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] + IDLE_PENALTY_RATE))
    assert c2.energy == pytest.approx(SUB_ASEXUAL_ENERGY - DT * (METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] + IDLE_PENALTY_RATE))


def test_juvenile_prevents_reproduction():
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine, energy=SUB_ASEXUAL_ENERGY)
    c2.life_stage = LifeStage.JUVENILE

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before
    assert c1.energy == pytest.approx(SUB_ASEXUAL_ENERGY - DT * (METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] + IDLE_PENALTY_RATE))
    assert c2.energy == pytest.approx(
        SUB_ASEXUAL_ENERGY - DT * (METABOLISM_RATE_BY_STAGE[LifeStage.JUVENILE] + IDLE_PENALTY_RATE)
    )


def test_infertile_partner_prevents_reproduction():
    """BIT-22: sem is_fertile, nao acasala mesmo com action_mate + proximidade + energia elegivel.

    Substitui o antigo test_low_energy_prevents_reproduction (que dependia de MIN_ENERGY_TO_MATE,
    removido). Agora o gate e a fertilidade persistente, nao o nivel de energia instantaneo.
    """
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine, energy=SUB_ASEXUAL_ENERGY)
    c2.is_fertile = False
    # has_eaten=False garante que update() nao volte a torna-la fertil neste step.
    c2.has_eaten = False

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before


def test_survival_floor_prevents_suicidal_mating():
    """Adulto com energia < REPRODUCTION_ENERGY_COST nao acasala (evita parto suicida)."""
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine, energy=SUB_ASEXUAL_ENERGY)
    c2.energy = REPRODUCTION_ENERGY_COST - 1.0

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before


def test_out_of_radius_prevents_reproduction():
    """Mesmas condicoes de fertilidade/action_mate, mas alem de MATING_RADIUS -> sem filho."""
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine, offset=MATING_RADIUS + 50.0, energy=SUB_ASEXUAL_ENERGY)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before


def test_cooldown_prevents_repeated_reproduction_across_consecutive_steps():
    engine = SimulationEngine()
    c1, c2 = _make_adult_pair(engine)
    # think() roda no brain tick (10 FPS) e recalcularia action_mate a partir da
    # rede (saida estocastica no genoma zero) — stub para manter action_mate=True
    # fixo e testar isoladamente a logica de cooldown, nao a rede neural. Idem para
    # is_fertile, que o acasalamento zera e update() so re-seta apos comer.
    for c in (c1, c2):
        c.think = lambda engine: None

    count_before = len(engine.creatures)
    # Mantem o par proximo e fertil por varios steps: so o primeiro deve gerar filho
    # (o cooldown do frame do acasalamento bloqueia os seguintes).
    for _ in range(10):
        c1.body.position = (700, 700)
        c2.body.position = (705, 700)
        c1.body.velocity = (0, 0)
        c2.body.velocity = (0, 0)
        c1.is_fertile = True
        c2.is_fertile = True
        engine.step(DT)

    children_born = len(engine.creatures) - count_before
    assert children_born == 1


def test_smoke_full_simulation_runs_without_exception_with_reproduction_active():
    engine = SimulationEngine()
    for _ in range(10):
        c = Creature(engine, x=700, y=700)
        c.life_stage = LifeStage.ADULT
        c.action_mate = True
        c.energy = 100.0
        c.is_fertile = True
        # Idem: stub de think() para manter action_mate=True fixo, isolando o
        # smoke test da aleatoriedade da rede neural do genoma zero.
        c.think = lambda engine: None
        engine.add_creature(c)

    for _ in range(30):
        engine.step(DT)

    # Cooldown deve impedir crescimento explosivo; a populacao cresce, mas de forma limitada.
    assert len(engine.creatures) < 200
