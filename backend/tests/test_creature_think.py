import pytest

from simulation import engine as engine_module
from simulation.creature import Creature, LifeStage, METABOLISM_RATE_BY_STAGE, IDLE_PENALTY_RATE
from simulation.engine import SimulationEngine


def test_think_runs_without_exception_on_fresh_creature():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.think(engine)


def test_think_outputs_motor_within_tanh_range():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.think(engine)
    assert -1.0 <= creature.motor_forward <= 1.0
    assert -1.0 <= creature.motor_torque <= 1.0


def test_think_action_flags_are_bool():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.think(engine)
    assert isinstance(creature.action_grab_drop, bool)
    assert isinstance(creature.action_mate, bool)


def test_update_after_think_never_increases_energy():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.life_stage = creature.life_stage.__class__.ADULT  # sai do estagio EGG p/ mover
    creature.think(engine)
    energy_before = creature.energy
    creature.update(1 / 30.0, engine)
    assert creature.energy <= energy_before


def test_update_energy_cost_proportional_to_motor_magnitude():
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.life_stage = creature.life_stage.__class__.ADULT
    creature.think(engine)

    # Zera os motores manualmente e mede o custo minimo (so vivo, sem torque/impulso)
    quiet = Creature(engine)
    quiet.life_stage = quiet.life_stage.__class__.ADULT
    quiet.motor_forward = 0.0
    quiet.motor_torque = 0.0
    quiet_energy_before = quiet.energy
    quiet.update(1 / 30.0, engine)
    quiet_cost = quiet_energy_before - quiet.energy
    # Parada, ela paga metabolismo + imposto de ociosidade (BIT-20): ficar imovel nao e mais de graca.
    expected_quiet_cost = (1 / 30.0) * (METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] + IDLE_PENALTY_RATE)
    assert quiet_cost == pytest.approx(expected_quiet_cost)

    active = Creature(engine)
    active.life_stage = active.life_stage.__class__.ADULT
    active.motor_forward = 1.0
    active.motor_torque = 1.0
    active_energy_before = active.energy
    active.update(1 / 30.0, engine)
    active_cost = active_energy_before - active.energy
    assert active_cost > quiet_cost


def test_egg_pays_no_motor_cost_even_with_strong_motor_output():
    engine = SimulationEngine()
    egg = Creature(engine)  # life_stage default = EGG
    egg.motor_forward = 1.0
    egg.motor_torque = 1.0
    energy_before = egg.energy
    egg.update(1 / 30.0, engine)
    assert egg.energy == energy_before


def test_think_runs_for_all_alive_creatures_via_engine_step():
    engine = SimulationEngine()
    for _ in range(5):
        c = Creature(engine)
        # BIT-19: envelhece para JUVENILE — ovos nao pensam via engine.step, entao sem isso o smoke
        # test deixaria de exercitar think() para todas as criaturas (seu proposito original).
        c.age = 5.0
        c.life_stage = LifeStage.JUVENILE
        engine.add_creature(c)

    for _ in range(20):
        engine.step(1 / 30.0)


def test_egg_does_not_think_via_engine_step():
    # BIT-19: enquanto EGG, think() nunca roda via engine.step — os motores cacheados ficam em 0.0
    # e a rede nunca e ativada (verificado pelo contador).
    engine = SimulationEngine()
    egg = Creature(engine)  # life_stage default = EGG
    engine.add_creature(egg)

    think_calls = {"n": 0}
    original_activate = egg.net.activate

    def counting_activate(inputs):
        think_calls["n"] += 1
        return original_activate(inputs)

    egg.net.activate = counting_activate

    # 6 frames a 1/30s = 0.2s (2 brain ticks), sem atingir o hatch (age > 2).
    for _ in range(6):
        engine.step(1 / 30.0)

    assert think_calls["n"] == 0
    assert egg.motor_forward == 0.0
    assert egg.motor_torque == 0.0
    assert egg.life_stage == LifeStage.EGG


def test_vision_resumes_after_hatching():
    # BIT-19: apos o hatch (age > 2), o brain tick volta a computar visao/think sem intervencao manual.
    engine = SimulationEngine()
    creature = Creature(engine)
    creature.age = 1.9  # ainda EGG; hatch para JUVENILE acontece durante o teste (age > 2)
    engine.add_creature(creature)

    vision_calls = {"n": 0}
    original_compute = engine_module.compute_vision

    def counting_compute_vision(c, eng):
        vision_calls["n"] += 1
        return original_compute(c, eng)

    engine_module.compute_vision = counting_compute_vision
    try:
        # ~1s: age passa de 1.9 para ~2.9, cruzando o limiar de hatch no meio do percurso.
        for _ in range(30):
            engine.step(1 / 30.0)
    finally:
        engine_module.compute_vision = original_compute

    assert creature.life_stage != LifeStage.EGG
    assert vision_calls["n"] >= 1


def test_to_dict_egg_has_empty_vision():
    # BIT-19: payload de ovo carrega vision vazia; nascido carrega os 9 setores.
    engine = SimulationEngine()
    creature = Creature(engine)  # EGG
    assert creature.to_dict()["vision"] == []

    creature.life_stage = LifeStage.JUVENILE
    vision = creature.to_dict()["vision"]
    assert len(vision) == 9
    assert all(isinstance(v, float) for v in vision)
