"""Testes dos controles interativos da simulacao (BIT-24): controle de tempo, arrasto
e serializacao de campos de inspeccao. Importa as constantes dos modulos — nunca hardcoda
valores de balanceamento/dimensoes (padrao do projeto)."""
import pytest

from simulation.engine import SimulationEngine, ALLOWED_SPEEDS
from simulation.creature import Creature


@pytest.fixture
def engine():
    return SimulationEngine()


# --- 1. Controle de tempo -------------------------------------------------

def test_allowed_speeds_contract():
    assert ALLOWED_SPEEDS == (0.5, 1.0, 2.0, 4.0)


def test_set_time_control_sets_paused(engine):
    assert engine.paused is False
    engine.set_time_control(paused=True)
    assert engine.paused is True
    engine.set_time_control(paused=False)
    assert engine.paused is False


def test_set_time_control_sets_valid_speed(engine):
    engine.set_time_control(speed=2.0)
    assert engine.speed == 2.0


def test_set_time_control_ignores_invalid_speed(engine):
    engine.set_time_control(speed=2.0)
    engine.set_time_control(speed=3.0)  # invalida: fora de ALLOWED_SPEEDS
    assert engine.speed == 2.0  # mantem a anterior


def test_set_time_control_ignores_non_numeric_speed(engine):
    # Cliente adulterado: speed nao-numerico nao pode levantar excecao (derrubaria a conexao WS).
    engine.set_time_control(speed=2.0)
    for bad in ("abc", [1, 2], {"a": 1}):
        engine.set_time_control(speed=bad)  # no-op silencioso
        assert engine.speed == 2.0  # mantem a anterior, sem excecao


def test_set_time_control_independent_fields(engine):
    # Apenas speed: paused nao muda.
    engine.set_time_control(paused=True)
    engine.set_time_control(speed=0.5)
    assert engine.paused is True
    assert engine.speed == 0.5


# --- 2. get_state expoe tempo --------------------------------------------

def test_get_state_contains_paused_and_speed(engine):
    engine.set_time_control(paused=True, speed=4.0)
    state = engine.get_state()
    assert state["paused"] is True
    assert state["speed"] == 4.0


# --- 3. Serializacao de inspeccao ----------------------------------------

def test_to_dict_contains_id_equal_to_genome_key(engine):
    creature = Creature(engine)
    engine.add_creature(creature)
    d = creature.to_dict()
    assert d["id"] == creature.genome.key
    assert creature.id == creature.genome.key


def test_to_dict_contains_new_inspection_fields(engine):
    creature = Creature(engine)
    d = creature.to_dict()
    for field in (
        "id", "age", "max_energy", "reproduction_cooldown",
        "motor_forward", "motor_torque", "action_mate", "action_grab_drop",
    ):
        assert field in d, f"campo {field} ausente em to_dict()"


# --- 4. start_drag --------------------------------------------------------

def test_start_drag_valid_id_returns_true(engine):
    creature = Creature(engine)
    engine.add_creature(creature)
    assert engine.start_drag(creature.id) is True


def test_start_drag_missing_id_returns_false(engine):
    creature = Creature(engine)
    engine.add_creature(creature)
    assert engine.start_drag(creature.id + 999999) is False


def test_start_drag_dead_creature_returns_false(engine):
    creature = Creature(engine)
    engine.add_creature(creature)
    creature.is_alive = False
    assert engine.start_drag(creature.id) is False


# --- 5. drag_to clampa dentro do mundo -----------------------------------

def test_drag_to_clamps_target_to_world_bounds(engine):
    creature = Creature(engine)
    engine.add_creature(creature)
    engine.start_drag(creature.id)
    # Alvo fora do mundo (abaixo e acima dos limites) deve ser clampado para [0, width]x[0, height].
    engine.drag_to(-50.0, engine.height + 1000.0)
    tx, ty = engine._drag_target
    assert tx == 0.0
    assert ty == engine.height
    assert creature.body.position.x == 0.0
    assert creature.body.position.y == engine.height


# --- 6. re-pin vence o motor ---------------------------------------------

def test_held_creature_stays_at_target_after_step_despite_motor(engine):
    creature = Creature(engine)
    engine.add_creature(creature)
    engine.start_drag(creature.id)
    target = (300.0, 400.0)
    engine.drag_to(*target)
    creature.motor_forward = 1.0
    creature.life_stage = creature.life_stage  # sem efeito, so explicitude
    engine.step(1 / 30.0)
    assert creature.body.position.x == pytest.approx(target[0])
    assert creature.body.position.y == pytest.approx(target[1])


# --- 7. morte durante o drag solta automaticamente ------------------------

def test_creature_dying_during_drag_is_released(engine):
    creature = Creature(engine)
    engine.add_creature(creature)
    engine.start_drag(creature.id)
    creature.is_alive = False
    engine.step(1 / 30.0)
    assert engine._held_creature is None
    assert engine._drag_target is None


# --- 8. end_drag solta e para de re-fixar ---------------------------------

def test_end_drag_releases_and_stops_repinning(engine):
    creature = Creature(engine)
    engine.add_creature(creature)
    engine.start_drag(creature.id)
    engine.drag_to(300.0, 400.0)
    engine.end_drag()
    assert engine._held_creature is None
    assert engine._drag_target is None
    # Apos soltar, o step nao re-fixa mais: a criatura pode se mover livremente.
    before = (creature.body.position.x, creature.body.position.y)
    creature.motor_forward = 1.0
    creature.age = 20.0  # ADULT: o motor e de fato aplicado (EGG nao move)
    for _ in range(10):
        engine.step(1 / 30.0)
    after = (creature.body.position.x, creature.body.position.y)
    assert (after[0], after[1]) != (before[0], before[1])
