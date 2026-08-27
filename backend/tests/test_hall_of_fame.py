from simulation.creature import Creature, LifeStage
from simulation.engine import (
    SimulationEngine,
    HALL_OF_FAME_SIZE,
    HALL_OF_FAME_CHILDREN_WEIGHT,
)

DT = 1 / 30.0


def _make_dead_creature(engine, age=20.0, children_count=0, generation=0):
    """Cria criatura morta pronta para ser registrada no hall."""
    c = Creature(engine, x=700, y=700)
    c.life_stage = LifeStage.ADULT
    c.age = age
    c.children_count = children_count
    c.generation = generation
    c.is_alive = False
    return c


# ---------------------------------------------------------------------------
# _record_in_hall_of_fame
# ---------------------------------------------------------------------------

def test_record_inserts_entry_with_correct_score():
    engine = SimulationEngine()
    c = _make_dead_creature(engine, age=30.0, children_count=2)
    engine._record_in_hall_of_fame(c)

    assert len(engine.hall_of_fame) == 1
    expected_score = 30.0 + HALL_OF_FAME_CHILDREN_WEIGHT * 2
    assert engine.hall_of_fame[0]["score"] == expected_score


def test_record_preserves_generation():
    engine = SimulationEngine()
    c = _make_dead_creature(engine, age=20.0, generation=7)
    engine._record_in_hall_of_fame(c)
    assert engine.hall_of_fame[0]["generation"] == 7


def test_record_sorted_desc_by_score():
    engine = SimulationEngine()
    for age in [10.0, 50.0, 30.0]:
        engine._record_in_hall_of_fame(_make_dead_creature(engine, age=age))

    scores = [e["score"] for e in engine.hall_of_fame]
    assert scores == sorted(scores, reverse=True)


def test_record_respects_cap():
    engine = SimulationEngine()
    # Inserir HALL_OF_FAME_SIZE + 3 entradas com scores crescentes
    for i in range(HALL_OF_FAME_SIZE + 3):
        engine._record_in_hall_of_fame(_make_dead_creature(engine, age=float(i)))

    assert len(engine.hall_of_fame) == HALL_OF_FAME_SIZE
    # As N maiores devem ter sobrado (maiores ages = maiores scores sem filhos)
    min_score_kept = engine.hall_of_fame[-1]["score"]
    assert min_score_kept >= float(3)  # as 3 menores (0,1,2) foram expulsas


def test_record_low_score_does_not_enter_full_hall():
    engine = SimulationEngine()
    # Preenche o hall com scores altos
    for i in range(HALL_OF_FAME_SIZE):
        engine._record_in_hall_of_fame(_make_dead_creature(engine, age=100.0 + i))

    score_floor = engine.hall_of_fame[-1]["score"]
    # Tenta inserir criatura com score menor que o pior do hall
    engine._record_in_hall_of_fame(_make_dead_creature(engine, age=0.1))
    assert len(engine.hall_of_fame) == HALL_OF_FAME_SIZE
    assert engine.hall_of_fame[-1]["score"] >= score_floor


def test_children_weight_beats_equivalent_longevity():
    engine = SimulationEngine()
    # Criatura longeva sem filhos
    c_longeva = _make_dead_creature(engine, age=100.0, children_count=0)
    # Criatura com filhos suficientes para superar
    filhos_necessarios = int(100.0 / HALL_OF_FAME_CHILDREN_WEIGHT) + 1
    c_prolifera = _make_dead_creature(engine, age=0.0, children_count=filhos_necessarios)

    engine._record_in_hall_of_fame(c_longeva)
    engine._record_in_hall_of_fame(c_prolifera)

    assert engine.hall_of_fame[0]["score"] > engine.hall_of_fame[1]["score"]
    assert engine.hall_of_fame[0]["genome"].key == c_prolifera.genome.key


def test_genome_in_hall_is_independent_copy():
    """Mutar o genoma vivo após registrar não deve alterar a entrada no hall (deepcopy)."""
    from simulation.rtneat_wrapper import mutate_genome
    engine = SimulationEngine()
    c = _make_dead_creature(engine, age=30.0)
    engine._record_in_hall_of_fame(c)

    connections_before = len(engine.hall_of_fame[0]["genome"].connections)
    # Forçar mutação no genoma original da criatura
    for _ in range(20):
        mutate_genome(c.genome, c.config)
    connections_after = len(engine.hall_of_fame[0]["genome"].connections)

    # A cópia no hall não deve ter sido alterada
    assert connections_before == connections_after


# ---------------------------------------------------------------------------
# Extinção com hall populado
# ---------------------------------------------------------------------------

def test_extinction_with_hall_preserves_generation():
    engine = SimulationEngine()
    # Popular o hall com entrada de generation=5
    c = _make_dead_creature(engine, age=50.0, generation=5)
    engine._record_in_hall_of_fame(c)

    # Forçar extinção (sem criaturas)
    assert len(engine.creatures) == 0
    engine.step(DT)

    assert len(engine.creatures) == 15  # BIT-35: respawn é 15 (era 10)
    for creature in engine.creatures:
        assert creature.generation == 5
        assert creature.is_alive


def test_extinction_with_hall_does_not_produce_gen_zero():
    engine = SimulationEngine()
    c = _make_dead_creature(engine, age=50.0, generation=3)
    engine._record_in_hall_of_fame(c)

    engine.step(DT)

    for creature in engine.creatures:
        assert creature.generation != 0


def test_extinction_with_hall_round_robins_entries():
    """Com múltiplas entradas, cada re-semeada usa uma entrada diferente (round-robin)."""
    engine = SimulationEngine()
    for gen in [2, 4, 6]:
        c = _make_dead_creature(engine, age=float(gen * 10), generation=gen)
        engine._record_in_hall_of_fame(c)

    engine.step(DT)

    # Deve haver criaturas com as gerações do hall (não todas iguais)
    generations = {cr.generation for cr in engine.creatures}
    assert len(generations) > 1  # round-robin distribui entre as entradas


# ---------------------------------------------------------------------------
# Extinção sem hall (fallback)
# ---------------------------------------------------------------------------

def test_extinction_without_hall_fallback_gen_zero():
    engine = SimulationEngine()
    assert len(engine.hall_of_fame) == 0

    engine.step(DT)

    assert len(engine.creatures) == 15  # BIT-35: respawn é 15 (era 10)
    for creature in engine.creatures:
        assert creature.generation == 0


# ---------------------------------------------------------------------------
# Integração: criaturas morrem e entram no hall via step()
# ---------------------------------------------------------------------------

def test_dead_creatures_enter_hall_via_step():
    engine = SimulationEngine()
    c = Creature(engine, x=700, y=700)
    c.life_stage = LifeStage.ADULT
    c.age = 25.0
    c.energy = 0.001  # morre no próximo step
    engine.add_creature(c)

    assert len(engine.hall_of_fame) == 0
    engine.step(DT)
    # Criatura morreu → deve ter sido registrada (e o Eden re-semeou porque ficou vazio)
    assert len(engine.hall_of_fame) >= 1
