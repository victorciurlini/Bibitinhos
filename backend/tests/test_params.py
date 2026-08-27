"""BIT-23 — Registry de parametros tunaveis em runtime.

Cada teste altera constantes de modulo/estado em memoria; a fixture `params_env` restaura
tudo via reset_params no teardown para nao vazar estado entre testes (os demais testes da suite
importam essas constantes e assumem os defaults do codigo).

Convencao do projeto: importar os objetos dos modulos, nunca hardcodar balanceamento — o registry
so muda VALORES em runtime, entao comparamos contra PARAM_SPECS/defaults, nao contra literais.
"""

import importlib

import pytest

import simulation.creature as creature_mod
import simulation.engine as engine_mod
import simulation.food as food_mod
import simulation.sensors as sensors_mod
from simulation.creature import Creature, LifeStage, METABOLISM_RATE_BY_STAGE
from simulation.engine import SimulationEngine
from simulation.food import Food, FOOD_ENERGY_VALUE
from simulation.params import (
    PARAM_SPECS,
    get_params,
    set_param,
    reset_params,
)

DT = 1 / 30.0


@pytest.fixture
def env():
    """Engine real + restauracao dos defaults no teardown."""
    engine = SimulationEngine()
    yield engine
    reset_params(engine)


def test_binding_simples_atributo_e_efeito_real(env):
    """set_param em binding simples patcheia o atributo do modulo E muda o comportamento real:
    uma ADULT parada passa a drenar na nova taxa de ociosidade via update()."""
    assert set_param(env, "idle_penalty_rate", 3.0) is True
    assert creature_mod.IDLE_PENALTY_RATE == 3.0

    creature = Creature(env)
    creature.life_stage = LifeStage.ADULT
    creature.motor_forward = 0.0
    creature.motor_torque = 0.0
    creature.body.velocity = (0.0, 0.0)
    energia_antes = creature.energy

    # Parada => movement_factor 0 => idle_cost = IDLE_PENALTY_RATE cheio; motor_cost = 0.
    creature.update(DT, env)
    drenado = energia_antes - creature.energy
    esperado = DT * (3.0 + METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])
    assert drenado == pytest.approx(esperado, rel=1e-6)


def test_multi_binding_vision_radius(env):
    """vision_radius tem duas copias (sensors le em runtime; engine copiou por valor no import)."""
    assert set_param(env, "vision_radius", 120.0) is True
    assert sensors_mod.VISION_RADIUS == 120.0
    assert engine_mod.VISION_RADIUS == 120.0


def test_clamp_acima_e_abaixo(env):
    """Valor acima do max aplica o max; abaixo do min aplica o min."""
    spec = PARAM_SPECS["idle_penalty_rate"]
    assert set_param(env, "idle_penalty_rate", 999.0) is True
    assert creature_mod.IDLE_PENALTY_RATE == spec["max"]
    assert set_param(env, "idle_penalty_rate", -50.0) is True
    assert creature_mod.IDLE_PENALTY_RATE == spec["min"]


def test_nome_desconhecido_e_valor_nao_numerico(env):
    """Nome desconhecido => False, nada muda; valor nao-numerico => False."""
    valor_antes = creature_mod.IDLE_PENALTY_RATE
    assert set_param(env, "nao_existe", 1.0) is False
    assert creature_mod.IDLE_PENALTY_RATE == valor_antes

    assert set_param(env, "idle_penalty_rate", "abc") is False
    assert set_param(env, "idle_penalty_rate", None) is False
    assert creature_mod.IDLE_PENALTY_RATE == valor_antes


def test_setters_especiais(env):
    """water_drag mexe no damping do Space vivo; metabolism_adult muta o dict por chave."""
    assert set_param(env, "water_drag", 0.9) is True
    assert env.physics.space.damping == pytest.approx(0.9)

    assert set_param(env, "metabolism_adult", 1.5) is True
    assert METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] == pytest.approx(1.5)


def test_parametro_inteiro(env):
    """Specs com default int coeridos para int (round), nao float."""
    assert set_param(env, "max_total_food", 75.6) is True
    assert engine_mod.MAX_TOTAL_FOOD == 76
    assert isinstance(engine_mod.MAX_TOTAL_FOOD, int)


def test_reset_restaura_todos(env):
    """reset_params volta todos os parametros aos defaults da tabela apos alterar varios."""
    set_param(env, "idle_penalty_rate", 4.0)
    set_param(env, "vision_radius", 200.0)
    set_param(env, "water_drag", 0.8)
    set_param(env, "metabolism_elder", 5.0)
    set_param(env, "max_total_food", 50)

    reset_params(env)

    valores = get_params(env)
    for name, spec in PARAM_SPECS.items():
        assert valores[name] == pytest.approx(spec["default"]), name


def test_get_params_e_state_cobrem_todas_as_chaves(env):
    """get_params e o state expoem exatamente as chaves de PARAM_SPECS."""
    valores = get_params(env)
    assert set(valores.keys()) == set(PARAM_SPECS.keys())

    state = env.get_state()
    assert "params" in state
    assert set(state["params"].keys()) == set(PARAM_SPECS.keys())


def test_food_usa_valor_corrente(env):
    """Food nova usa FOOD_ENERGY_VALUE corrente (patch no modulo muda comida criada depois)."""
    assert set_param(env, "food_energy_value", 50.0) is True
    assert food_mod.FOOD_ENERGY_VALUE == 50.0
    comida = Food(env, 0, 0)
    assert comida.energy_value == 50.0


def test_reproducao_substituiu_min_energy_to_mate(env):
    """Os parametros de reproducao vivos batem nos bindings certos; MIN_ENERGY_TO_MATE nao existe
    mais (BIT-22) e nenhum spec o referencia — trava contra regressao para o binding morto."""
    assert set_param(env, "fertility_energy_threshold", 40.0) is True
    assert creature_mod.FERTILITY_ENERGY_THRESHOLD == 40.0

    assert set_param(env, "mating_radius", 200.0) is True
    assert engine_mod.MATING_RADIUS == 200.0

    assert not hasattr(engine_mod, "MIN_ENERGY_TO_MATE")
    todos_bindings = []
    for spec in PARAM_SPECS.values():
        todos_bindings.extend(attr for _, attr in spec.get("bindings", []))
    assert "MIN_ENERGY_TO_MATE" not in todos_bindings
