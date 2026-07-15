"""BIT-20 — Pressao evolutiva para exploracao.

Trava o comportamento reclamado pelo developer: bibite parado girando no lugar (e ainda assim
procriando). A economia de energia foi invertida para que explorar seja a estrategia dominante
e girar parado seja a PIOR possivel.

Convencao do projeto: importar as constantes, nunca hardcodar valores — assim um rebalanceamento
futuro nao quebra a suite (foi o que permitiu ao BIT-16 mexer em constantes sem tocar nos testes).
"""

import math

import neat
import pytest

from simulation.creature import (
    Creature,
    LifeStage,
    STARTING_ENERGY,
    IDLE_PENALTY_RATE,
    MOVEMENT_REFERENCE_SPEED,
    MOTOR_FORWARD_COST,
    SPIN_COST,
    METABOLISM_RATE_BY_STAGE,
)
from simulation.engine import (
    SimulationEngine,
    MIN_ENERGY_TO_MATE,
    MIN_ENERGY_TO_REPRODUCE_ASEXUALLY,
    REPRODUCTION_ENERGY_COST,
    ASEXUAL_REPRODUCTION_ENERGY_COST,
    REPRODUCTION_COOLDOWN,
    ASEXUAL_REPRODUCTION_COOLDOWN,
)
from simulation.oasis import (
    EDEN_POPULATION_THRESHOLD,
    EDEN_OASIS_MIN_DISTANCE,
    EDEN_OASIS_MAX_DISTANCE,
)
from simulation.rtneat_wrapper import (
    load_neat_config,
    create_zero_genome,
    MOTOR_FORWARD_NODE_KEY,
    MOTOR_FORWARD_SEED_BIAS_MIN,
    MOTOR_FORWARD_SEED_BIAS_MAX,
)

DT = 1 / 30.0


def _adult(engine, motor_forward, motor_torque, speed):
    """Cria uma ADULT com heading 0 e velocidade `speed` para frente (grip lateral nao interfere)."""
    creature = Creature(engine)
    creature.life_stage = LifeStage.ADULT
    creature.motor_forward = motor_forward
    creature.motor_torque = motor_torque
    creature.body.angle = 0.0
    creature.body.velocity = (speed, 0.0)
    return creature


def _energy_cost_per_second(creature, engine):
    energy_before = creature.energy
    creature.update(DT, engine)
    return (energy_before - creature.energy) / DT


# --- O teste que trava a regressao reclamada pelo developer ---

def test_spinning_in_place_costs_more_than_exploring():
    """Girar parado tem que sangrar MAIS energia do que explorar o mapa."""
    engine = SimulationEngine()

    spinner = _adult(engine, motor_forward=0.0, motor_torque=1.0, speed=0.0)
    explorer = _adult(engine, motor_forward=0.8, motor_torque=0.3, speed=MOVEMENT_REFERENCE_SPEED)

    spinner_cost = _energy_cost_per_second(spinner, engine)
    explorer_cost = _energy_cost_per_second(explorer, engine)

    assert spinner_cost > explorer_cost


def test_spinning_in_place_is_the_worst_survival_strategy():
    """Girar parado deve ser a pior estrategia disponivel — pior ate que ficar totalmente imovel."""
    engine = SimulationEngine()

    strategies = {
        "spinning": _adult(engine, 0.0, 1.0, 0.0),
        "idle": _adult(engine, 0.0, 0.0, 0.0),
        "exploring": _adult(engine, 0.8, 0.3, MOVEMENT_REFERENCE_SPEED),
        "full_throttle": _adult(engine, 1.0, 1.0, MOVEMENT_REFERENCE_SPEED),
    }
    costs = {name: _energy_cost_per_second(c, engine) for name, c in strategies.items()}

    assert costs["spinning"] == max(costs.values())          # a pior de todas
    assert costs["exploring"] == min(costs.values())         # a melhor de todas
    assert costs["exploring"] < costs["idle"] < costs["spinning"]


# --- Imposto de ociosidade ---

def test_idle_penalty_is_full_when_stationary():
    engine = SimulationEngine()
    creature = _adult(engine, motor_forward=0.0, motor_torque=0.0, speed=0.0)

    cost = _energy_cost_per_second(creature, engine)

    assert cost == pytest.approx(METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] + IDLE_PENALTY_RATE)


def test_idle_penalty_is_zero_at_reference_speed():
    engine = SimulationEngine()
    creature = _adult(engine, motor_forward=0.0, motor_torque=0.0, speed=MOVEMENT_REFERENCE_SPEED)

    cost = _energy_cost_per_second(creature, engine)

    assert cost == pytest.approx(METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])


def test_idle_penalty_scales_with_speed():
    """Metade da velocidade de referencia => metade do imposto."""
    engine = SimulationEngine()
    creature = _adult(engine, motor_forward=0.0, motor_torque=0.0, speed=MOVEMENT_REFERENCE_SPEED / 2)

    cost = _energy_cost_per_second(creature, engine)

    expected = METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] + IDLE_PENALTY_RATE * 0.5
    assert cost == pytest.approx(expected)


def test_idle_penalty_is_not_gameable_by_motor_output():
    """Travada contra a parede (thrust cheio, velocidade ~0) paga o imposto CHEIO.

    A multa e medida pela velocidade real do corpo, nao pelo output do motor — se fosse pelo output,
    bastaria empurrar contra a parede para fingir movimento e escapar da punicao.
    """
    engine = SimulationEngine()
    stuck = _adult(engine, motor_forward=1.0, motor_torque=0.0, speed=0.0)

    cost = _energy_cost_per_second(stuck, engine)

    expected = (
        METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]
        + IDLE_PENALTY_RATE                 # imposto cheio: nao esta indo a lugar nenhum
        + MOTOR_FORWARD_COST * 1.0          # e ainda paga o motor que esta queimando
    )
    assert cost == pytest.approx(expected)


def test_egg_pays_no_idle_penalty():
    """EGG nao se move por design — multa-lo por estar parado seria puni-lo por existir."""
    engine = SimulationEngine()
    egg = Creature(engine)  # life_stage default = EGG
    egg.motor_forward = 0.0
    egg.motor_torque = 0.0
    egg.body.velocity = (0.0, 0.0)

    energy_before = egg.energy
    egg.update(DT, engine)

    assert egg.energy == energy_before


def test_turning_while_moving_is_free():
    """Curvar em movimento nao pode custar nada: a criatura precisa virar para perseguir comida."""
    engine = SimulationEngine()

    straight = _adult(engine, motor_forward=0.8, motor_torque=0.0, speed=MOVEMENT_REFERENCE_SPEED)
    turning = _adult(engine, motor_forward=0.8, motor_torque=1.0, speed=MOVEMENT_REFERENCE_SPEED)

    assert _energy_cost_per_second(turning, engine) == pytest.approx(
        _energy_cost_per_second(straight, engine)
    )


def test_spinning_while_stationary_is_not_free():
    """O mesmo torque, porem parada, custa SPIN_COST cheio."""
    engine = SimulationEngine()

    still = _adult(engine, motor_forward=0.0, motor_torque=0.0, speed=0.0)
    spinning = _adult(engine, motor_forward=0.0, motor_torque=1.0, speed=0.0)

    delta = _energy_cost_per_second(spinning, engine) - _energy_cost_per_second(still, engine)

    assert delta == pytest.approx(SPIN_COST)


# --- Seed genetico: a Gen 0 nasce andando ---

def test_gen0_genomes_are_all_seeded_to_move_forward():
    """100% da Gen 0 tem que nascer capaz de andar.

    Sem o seed, ~48% nascia com Motor_Forward <= 0 e, como forward_thrust = max(0.0, motor_forward),
    era fisicamente incapaz de se mover para sempre.
    """
    config = load_neat_config()

    for i in range(200):
        genome = create_zero_genome(90000 + i, config)

        bias = genome.nodes[MOTOR_FORWARD_NODE_KEY].bias
        assert MOTOR_FORWARD_SEED_BIAS_MIN <= bias <= MOTOR_FORWARD_SEED_BIAS_MAX

        net = neat.nn.FeedForwardNetwork.create(genome, config)
        outputs = net.activate([0.0] * 16)  # sem nada no cone de visao, sensores zerados
        assert outputs[0] > 0.0, "genoma da Gen 0 nasceu incapaz de andar"


def test_seed_preserves_genetic_variety():
    """O seed enviesa, nao clona: os thrusts iniciais precisam variar entre individuos."""
    config = load_neat_config()

    biases = {create_zero_genome(91000 + i, config).nodes[MOTOR_FORWARD_NODE_KEY].bias for i in range(50)}

    assert len(biases) > 1


# --- Reproducao: acasalar tem que dominar sobre clonar ---

def test_mating_is_more_accessible_than_cloning():
    assert MIN_ENERGY_TO_MATE < MIN_ENERGY_TO_REPRODUCE_ASEXUALLY
    assert REPRODUCTION_ENERGY_COST < ASEXUAL_REPRODUCTION_ENERGY_COST
    assert REPRODUCTION_COOLDOWN < ASEXUAL_REPRODUCTION_COOLDOWN


def test_mating_threshold_is_below_max_energy():
    """O limiar nao pode voltar a colar no teto de max_energy.

    Com MIN_ENERGY_TO_MATE == max_energy (o que o BIT-16 introduziu), acasalar exigia DUAS criaturas
    com energia perfeitamente cheia no mesmo frame — janela quase nula —, enquanto clonar exigia so
    uma. Era essa assimetria que fazia o bibite parado clonar em vez de acasalar.
    """
    engine = SimulationEngine()
    max_energy = Creature(engine).max_energy

    assert MIN_ENERGY_TO_MATE < max_energy


def test_newborn_still_has_to_eat_before_mating():
    """Intencao do BIT-16 preservada: ninguem acasala sem antes ter comido."""
    assert MIN_ENERGY_TO_MATE > STARTING_ENERGY


# --- Jardim do Eden nao subsidia mais quem esta parado ---

def test_eden_oasis_spawns_away_from_the_survivor():
    """O oasis do Eden nascia EM CIMA do sobrevivente, fazendo chover comida sobre quem ficou parado."""
    engine = SimulationEngine()

    survivor = Creature(engine, x=1000, y=1000)  # centro do mapa: sem clamp de borda interferindo
    engine.creatures = [survivor]
    engine.oases = []
    assert len(engine.creatures) < EDEN_POPULATION_THRESHOLD

    engine.step(DT)

    assert engine.oases, "o Eden deveria ter criado um oasis"
    for oasis in engine.oases:
        dist = math.hypot(oasis.x - survivor.body.position.x, oasis.y - survivor.body.position.y)
        assert dist >= EDEN_OASIS_MIN_DISTANCE - 1.0
        assert dist <= EDEN_OASIS_MAX_DISTANCE + 1.0
