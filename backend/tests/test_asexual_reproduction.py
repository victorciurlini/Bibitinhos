import pytest

import simulation.engine as engine_module
from simulation.creature import Creature, LifeStage, METABOLISM_RATE_BY_STAGE, IDLE_PENALTY_RATE
from simulation.engine import (
    SimulationEngine,
    ASEXUAL_REPRODUCTION_ENERGY_COST,
    ASEXUAL_REPRODUCTION_COOLDOWN,
    MIN_ENERGY_TO_REPRODUCE_ASEXUALLY,
)

DT = 1 / 30.0


def _make_solo_adult(engine, x=700, y=700, energy=100.0, action_mate=True):
    """Cria uma unica criatura ADULT, longe de qualquer outra (sem parceiro em alcance)."""
    c = Creature(engine, x=x, y=y)
    c.life_stage = LifeStage.ADULT
    c.action_mate = action_mate
    c.energy = energy
    engine.add_creature(c)
    return c


def _make_nearby_adult_pair(engine, x=700, y=700, offset=5, energy=100.0, is_fertile=True):
    """Dois adultos dentro de MATING_RADIUS, ferteis (reproducao sexuada por proximidade — BIT-22)."""
    c1 = Creature(engine, x=x, y=y)
    c2 = Creature(engine, x=x + offset, y=y)
    for c in (c1, c2):
        c.life_stage = LifeStage.ADULT
        c.action_mate = True
        c.energy = energy
        c.is_fertile = is_fertile
    engine.add_creature(c1)
    engine.add_creature(c2)
    return c1, c2


def test_asexual_reproduction_fires_when_alone_with_enough_energy():
    engine = SimulationEngine()
    parent = _make_solo_adult(engine, energy=100.0)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before + 1
    child = [c for c in engine.creatures if c is not parent][0]
    assert child.life_stage == LifeStage.EGG

    # Parada, ela tambem paga o imposto de ociosidade do BIT-20 no frame do update.
    expected_energy = (
        100.0
        - ASEXUAL_REPRODUCTION_ENERGY_COST
        - DT * (METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] + IDLE_PENALTY_RATE)
    )
    assert parent.energy == pytest.approx(expected_energy)

    expected_cooldown = ASEXUAL_REPRODUCTION_COOLDOWN - DT
    assert parent.reproduction_cooldown == pytest.approx(expected_cooldown)


def test_asexual_reproduction_blocked_below_energy_threshold():
    engine = SimulationEngine()
    parent = _make_solo_adult(engine, energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY - 1.0)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before


def test_asexual_reproduction_blocked_when_action_mate_false():
    engine = SimulationEngine()
    parent = _make_solo_adult(engine, energy=100.0, action_mate=False)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before


def test_asexual_reproduction_blocked_for_juvenile():
    engine = SimulationEngine()
    parent = _make_solo_adult(engine, energy=100.0)
    parent.life_stage = LifeStage.JUVENILE

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before


def test_asexual_reproduction_respects_cooldown():
    engine = SimulationEngine()
    parent = _make_solo_adult(engine, energy=100.0)
    parent.reproduction_cooldown = 5.0

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before


def test_no_asexual_when_viable_partner_is_in_range():
    # BIT-22: quando ha um parceiro VIAVEL (fertil, querendo, proximo) em alcance, a via sexuada
    # dispara e seta sought_mate_this_frame, o que bloqueia o fallback assexuado no mesmo step —
    # nasce exatamente 1 filho (sexuado), nao 1 por criatura via clonagem.
    engine = SimulationEngine()
    c1, c2 = _make_nearby_adult_pair(engine, energy=100.0)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before + 1
    assert c1.sought_mate_this_frame and c2.sought_mate_this_frame
    # Ambos consumiram a fertilidade no acasalamento sexuado (nao clonaram).
    assert not c1.is_fertile and not c2.is_fertile


def test_sexual_reproduction_takes_priority_over_asexual_in_same_frame():
    # Dois ADULT ferteis e proximos, ambos com energia de sobra para os dois caminhos:
    # so a via sexuada deve disparar (roda antes e seta sought_mate_this_frame + cooldown,
    # bloqueando o laco assexuado que roda depois, no mesmo step()).
    engine = SimulationEngine()
    c1, c2 = _make_nearby_adult_pair(engine, energy=100.0)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before + 1


def test_child_genome_is_clone_and_mutation_of_single_parent(monkeypatch):
    calls = {}
    original_clone = engine_module.clone_genome
    original_mutate = engine_module.mutate_genome

    def spy_clone(genome, genome_id, config):
        calls["cloned_from"] = genome
        result = original_clone(genome, genome_id, config)
        calls["clone_result"] = result
        return result

    def spy_mutate(genome, config):
        calls["mutated_genome"] = genome
        return original_mutate(genome, config)

    monkeypatch.setattr(engine_module, "clone_genome", spy_clone)
    monkeypatch.setattr(engine_module, "mutate_genome", spy_mutate)

    engine = SimulationEngine()
    parent = _make_solo_adult(engine, energy=100.0)

    engine.step(DT)

    assert calls["cloned_from"] is parent.genome
    assert calls["mutated_genome"] is calls["clone_result"]

    child = [c for c in engine.creatures if c is not parent][0]
    assert child.genome is calls["mutated_genome"]


def test_smoke_full_simulation_runs_without_exception_with_asexual_reproduction_active():
    engine = SimulationEngine()
    for i in range(10):
        c = Creature(engine, x=1000 + i * 200, y=1000 + i * 200)
        c.life_stage = LifeStage.ADULT
        c.action_mate = True
        c.energy = 100.0
        # Isola do output estocastico da rede do genoma zero, mesmo padrao do
        # smoke test da reproducao sexuada (test_reproduction.py).
        c.think = lambda engine: None
        engine.add_creature(c)

    for _ in range(30):
        engine.step(DT)

    # Cooldown deve impedir crescimento explosivo.
    assert len(engine.creatures) < 200
