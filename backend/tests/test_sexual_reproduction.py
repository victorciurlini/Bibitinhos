"""BIT-22 — Reproducao sexuada emergente por FERTILIDADE PERSISTENTE + PROXIMIDADE.

Convencao do projeto: importar as constantes, nunca hardcodar valores — assim um rebalanceamento
futuro nao quebra a suite.
"""

import pytest

from simulation.creature import Creature, LifeStage, FERTILITY_ENERGY_THRESHOLD
from simulation.engine import (
    SimulationEngine,
    MATING_RADIUS,
    REPRODUCTION_ENERGY_COST,
    REPRODUCTION_COOLDOWN,
    MIN_ENERGY_TO_REPRODUCE_ASEXUALLY,
)

DT = 1 / 30.0


def _adult(engine, x=700, y=700, energy=100.0):
    c = Creature(engine, x=x, y=y)
    c.life_stage = LifeStage.ADULT
    c.energy = energy
    return c


def _fertile_adult(engine, x=700, y=700, energy=100.0, action_mate=True):
    c = _adult(engine, x=x, y=y, energy=energy)
    c.has_eaten = True
    c.is_fertile = True
    c.action_mate = action_mate
    engine.add_creature(c)
    return c


# --- 1. has_eaten gate (o novo "comer antes de acasalar") ---

def test_has_not_eaten_stays_infertile_even_with_full_energy():
    engine = SimulationEngine()
    c = _adult(engine, energy=100.0)  # energia cheia
    c.has_eaten = False

    c.update(DT, engine)

    assert not c.is_fertile


def test_after_eating_and_reaching_threshold_becomes_fertile():
    engine = SimulationEngine()
    c = _adult(engine, energy=100.0)
    c.has_eaten = True

    c.update(DT, engine)

    assert c.is_fertile


# --- 2. Fertilidade persistente ---

def test_fertility_persists_when_energy_drops_below_threshold():
    engine = SimulationEngine()
    c = _adult(engine, energy=100.0)
    c.has_eaten = True
    c.update(DT, engine)
    assert c.is_fertile

    # A energia cai abaixo do limiar no roaming (mas > 0): a fertilidade NAO e revogada.
    c.energy = FERTILITY_ENERGY_THRESHOLD - 10.0
    assert c.energy > 0
    c.update(DT, engine)

    assert c.is_fertile


# --- 3. Acasalamento por proximidade ---

def test_two_fertile_adults_within_radius_produce_one_child():
    engine = SimulationEngine()
    a = _fertile_adult(engine, x=700, y=700)
    b = _fertile_adult(engine, x=700 + int(MATING_RADIUS) - 20, y=700)
    # has_eaten=False para que o update() do proprio step nao re-promova a fertilidade apos o scan
    # zera-la — assim o teste observa o efeito direto do acasalamento (a re-promocao natural, "comeu
    # + energia >= limiar", e coberta pelos testes de fertilidade).
    a.has_eaten = False
    b.has_eaten = False

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before + 1
    assert not a.is_fertile and not b.is_fertile
    assert a.reproduction_cooldown == pytest.approx(REPRODUCTION_COOLDOWN - DT)
    assert b.reproduction_cooldown == pytest.approx(REPRODUCTION_COOLDOWN - DT)


def test_two_fertile_adults_beyond_radius_produce_no_child():
    # Energia abaixo do limiar da clonagem isola a mecanica de PROXIMIDADE: sem via assexuada
    # interferindo, alem de MATING_RADIUS nao nasce ninguem.
    engine = SimulationEngine()
    energy = MIN_ENERGY_TO_REPRODUCE_ASEXUALLY - 5.0
    a = _fertile_adult(engine, x=100, y=700, energy=energy)
    b = _fertile_adult(engine, x=100 + int(MATING_RADIUS) + 50, y=700, energy=energy)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before


# --- 4. Ambos precisam querer ---

def test_both_must_want_to_mate():
    # Energia abaixo do limiar da clonagem para isolar o gate sexual (sem clone mascarando).
    engine = SimulationEngine()
    energy = MIN_ENERGY_TO_REPRODUCE_ASEXUALLY - 5.0
    a = _fertile_adult(engine, x=700, y=700, energy=energy, action_mate=True)
    b = _fertile_adult(engine, x=705, y=700, energy=energy, action_mate=False)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before


# --- 5. Assexuada suprimida na presenca de parceiro viavel ---

def test_asexual_suppressed_when_viable_partner_in_range():
    engine = SimulationEngine()
    a = _fertile_adult(engine, x=700, y=700, energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY)
    b = _fertile_adult(engine, x=705, y=700, energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY)

    count_before = len(engine.creatures)
    engine.step(DT)

    # Exatamente 1 filho (sexuado), nao 2 (clonagem de cada um): a via sexuada suprime a assexuada.
    assert len(engine.creatures) == count_before + 1
    assert a.sought_mate_this_frame and b.sought_mate_this_frame


def test_asexual_fires_when_alone_and_full_energy():
    engine = SimulationEngine()
    # Sozinho (parceiro fora do raio) e com energia cheia -> clona.
    a = _fertile_adult(engine, x=100, y=100, energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before + 1
    assert not a.sought_mate_this_frame


# --- 6. Sobrevivencia: sem parto suicida ---

def test_no_mating_below_survival_energy_floor():
    # 'a' abaixo do piso de sobrevivencia nao acasala; 'b' fica abaixo do limiar da clonagem para
    # nao mascarar o resultado com um filho assexuado.
    engine = SimulationEngine()
    a = _fertile_adult(engine, x=700, y=700, energy=REPRODUCTION_ENERGY_COST - 1.0)
    b = _fertile_adult(engine, x=705, y=700, energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY - 5.0)

    count_before = len(engine.creatures)
    engine.step(DT)

    assert len(engine.creatures) == count_before
