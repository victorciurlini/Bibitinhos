"""BIT-21 — Impeto de busca de comida e acasalamento.

Trava o sintoma reclamado: bibites passam perto de comida e nao viram para comer, e cruzam com
parceiros prontos e nao acasalam. A causa nao e balanceamento de energia (BIT-20) e sim que a
Gen-0 nasce com pesos aleatorios. A solucao sao SEMENTES inatas evolutiveis na Gen-0:
  - food-taxis: pesos visao[i]->Motor_Torque = FOOD_TAXIS_STEER_GAIN*(i-4);
  - impeto reprodutivo: bias de Action_Mate em U(1.5, 2.5);
  - neutralizacao da repulsao: adulto pronto percebe parceiro como sinal positivo.

Convencao do projeto: importar as constantes, nunca hardcodar valores, para que rebalanceamentos
futuros nao quebrem a suite.
"""

import math
import random

import neat
import pytest

from simulation.creature import Creature, LifeStage
from simulation.engine import SimulationEngine
from simulation.food import Food
from simulation.sensors import compute_vision
from simulation.rtneat_wrapper import (
    ACTION_MATE_NODE_KEY,
    ACTION_MATE_SEED_BIAS_MAX,
    ACTION_MATE_SEED_BIAS_MIN,
    FOOD_TAXIS_STEER_GAIN,
    MOTOR_TORQUE_NODE_KEY,
    clone_genome,
    create_zero_genome,
    load_neat_config,
)


def make_engine_with_creature(angle=0.0):
    sim = SimulationEngine()
    creature = Creature(sim, x=1000, y=1000)
    creature.body.angle = angle
    sim.add_creature(creature)
    return sim, creature


def _hungry_adult(sim, creature):
    creature.life_stage = LifeStage.ADULT
    creature.energy = 0.0  # fome maxima -> sinal de comida forte
    creature.reproduction_cooldown = 0.0
    return creature


def _ready_adult(sim, creature):
    creature.life_stage = LifeStage.ADULT
    creature.energy = creature.max_energy  # saciado -> pronto para acasalar
    creature.reproduction_cooldown = 0.0
    return creature


# --- Grupo 1: a semente de food-taxis existe e tem o sinal certo -------------------------------

def test_food_taxis_seed_weights_are_seeded_with_correct_sign():
    config = load_neat_config()
    genome = create_zero_genome(1, config)
    for i in range(9):
        conn_key = (-(i + 1), MOTOR_TORQUE_NODE_KEY)
        assert conn_key in genome.connections
        assert genome.connections[conn_key].weight == pytest.approx(
            FOOD_TAXIS_STEER_GAIN * (i - 4)
        )


def test_food_taxis_center_sector_is_zero_and_weights_are_monotonic():
    config = load_neat_config()
    genome = create_zero_genome(2, config)
    weights = [genome.connections[(-(i + 1), MOTOR_TORQUE_NODE_KEY)].weight for i in range(9)]
    # setor central (i=4) segue reto
    assert weights[4] == pytest.approx(0.0)
    # estritamente crescente de -4*gain (i=0) a +4*gain (i=8)
    assert weights[0] == pytest.approx(-4 * FOOD_TAXIS_STEER_GAIN)
    assert weights[8] == pytest.approx(4 * FOOD_TAXIS_STEER_GAIN)
    for a, b in zip(weights, weights[1:]):
        assert b > a


# --- Grupo 2: Gen-0 vira em direcao a comida (trava a regressao do sintoma) ---------------------

def _place_food_at_angle(sim, creature, degrees, radius=40.0):
    cx, cy = creature.body.position
    theta = math.radians(degrees)
    food = Food(sim, cx + radius * math.cos(theta), cy + radius * math.sin(theta))
    sim.add_food(food)
    return food


def test_gen0_turns_toward_food_on_the_left():
    # Comida a +40 graus (CCW) do eixo frontal -> torque positivo (vira CCW, em direcao a comida).
    sim, creature = make_engine_with_creature(angle=0.0)
    _hungry_adult(sim, creature)
    _place_food_at_angle(sim, creature, +40.0)
    creature.vision = compute_vision(creature, sim)
    creature.think(sim)
    assert creature.motor_torque > 0.0


def test_gen0_turns_toward_food_on_the_right():
    # Comida a -40 graus (CW) do eixo frontal -> torque negativo (vira CW, em direcao a comida).
    sim, creature = make_engine_with_creature(angle=0.0)
    _hungry_adult(sim, creature)
    _place_food_at_angle(sim, creature, -40.0)
    creature.vision = compute_vision(creature, sim)
    creature.think(sim)
    assert creature.motor_torque < 0.0


# --- Grupo 3: semente de Action_Mate ------------------------------------------------------------

def test_action_mate_bias_seeded_within_range():
    config = load_neat_config()
    for i in range(30):
        genome = create_zero_genome(1000 + i, config)
        bias = genome.nodes[ACTION_MATE_NODE_KEY].bias
        assert ACTION_MATE_SEED_BIAS_MIN <= bias <= ACTION_MATE_SEED_BIAS_MAX


# A semente de Action_Mate e PROBABILISTICA (bias sorteado em U(min, max)), entao a decisao de
# acasalar da Gen-0 nao e deterministica sobre 1 genoma. Fixamos a semente do RNG global e
# afirmamos estatisticamente sobre N amostras contra um limiar conservador.
# BIT-37: com U(0.8,1.5) a taxa real cai para ~65-75%, entao 0.75 e conservador sem ser flaky.
SAMPLE_SIZE = 200
MIN_SUCCESS_FRACTION = 0.75


def test_sated_adult_wants_to_mate_with_nothing_in_sight():
    random.seed(42)
    successes = 0
    for _ in range(SAMPLE_SIZE):
        sim, creature = make_engine_with_creature(angle=0.0)
        _ready_adult(sim, creature)
        creature.vision = compute_vision(creature, sim)  # nada em vista -> tudo zero
        assert creature.vision == [0.0] * 9
        creature.think(sim)
        if creature.action_mate is True:
            successes += 1
    fraction = successes / SAMPLE_SIZE
    assert fraction >= MIN_SUCCESS_FRACTION


# --- Grupo 4: neutralizacao puxa parceiros ------------------------------------------------------

def test_ready_adult_turns_toward_partner():
    # Parceiro a +40 graus: observador pronto vira em direcao a ele (torque positivo), nao para longe.
    # A semente de food-taxis puxa o torque, mas o resto do genoma da Gen-0 e aleatorio, entao a
    # decisao nao e deterministica: fixamos o RNG global e afirmamos estatisticamente sobre N amostras
    # contra um limiar conservador (ver SAMPLE_SIZE / MIN_SUCCESS_FRACTION acima).
    random.seed(42)
    successes = 0
    for _ in range(SAMPLE_SIZE):
        sim, creature = make_engine_with_creature(angle=0.0)
        _ready_adult(sim, creature)
        cx, cy = creature.body.position
        theta = math.radians(40.0)
        partner = Creature(sim, x=cx + 40 * math.cos(theta), y=cy + 40 * math.sin(theta))
        partner.life_stage = LifeStage.ADULT
        partner.energy = partner.max_energy
        sim.add_creature(partner)
        creature.vision = compute_vision(creature, sim)
        # parceiro a +40 graus cai num setor a esquerda do centro, com sinal POSITIVO (atrativo)
        assert any(v > 0.0 for v in creature.vision[5:])
        assert all(v >= 0.0 for v in creature.vision)  # nenhum sinal repulsivo (negativo)
        creature.think(sim)
        if creature.motor_torque > 0.0:
            successes += 1
    fraction = successes / SAMPLE_SIZE
    assert fraction >= MIN_SUCCESS_FRACTION


# --- Grupo 5: a semente e evolutivel, nao global ------------------------------------------------

def test_clone_preserves_parent_weights_without_reseeding():
    config = load_neat_config()
    parent = create_zero_genome(5, config)
    # muta os pesos semeados do pai para valores atipicos, que a semente reescreveria se re-aplicada
    for i in range(9):
        parent.connections[(-(i + 1), MOTOR_TORQUE_NODE_KEY)].weight = 42.0
    parent.nodes[ACTION_MATE_NODE_KEY].bias = -10.0

    child = clone_genome(parent, 6, config)

    for i in range(9):
        assert child.connections[(-(i + 1), MOTOR_TORQUE_NODE_KEY)].weight == pytest.approx(42.0)
    assert child.nodes[ACTION_MATE_NODE_KEY].bias == pytest.approx(-10.0)
