"""Registry de parametros tunaveis em runtime (BIT-23).

Regras que definem o que pode entrar aqui (validadas ao vivo, ver research):
- So constantes LIDAS EM RUNTIME no modulo dono (patch de modulo funciona).
- Constantes importadas por valor em outro modulo precisam de binding EM CADA COPIA.
- Defaults de funcao sao congelados no `def` — nao adianta patchear o modulo.
Ajustes valem so em memoria: reiniciar o backend restaura os defaults do codigo.

Duas formas de aplicacao por spec:
- `bindings`: lista de (caminho_do_modulo, atributo); todos setados via
  setattr(sys.modules[mod], attr, valor).
- `apply`/`read`: nomes de callables (resolvidos via globals()) que recebem o `engine`,
  para alvos que nao sao atributo de modulo (dict de metabolismo, damping do Space vivo).

`default` e literal na tabela (fonte de verdade do reset e dos testes), nao capturado
dinamicamente.
"""
import importlib
import sys

PARAM_SPECS = {
    # --- Energia ---
    "idle_penalty_rate":        {"group": "Energia", "label": "Imposto de ociosidade (E/s)",
        "default": 0.1, "min": 0.0, "max": 5.0, "step": 0.1,
        "bindings": [("simulation.creature", "IDLE_PENALTY_RATE")]},
    "motor_forward_cost":       {"group": "Energia", "label": "Custo de propulsao (E/s)",
        "default": 0.05, "min": 0.0, "max": 5.0, "step": 0.01,
        "bindings": [("simulation.creature", "MOTOR_FORWARD_COST")]},
    "spin_cost":                {"group": "Energia", "label": "Custo de girar parado (E/s)",
        "default": 0.3, "min": 0.0, "max": 5.0, "step": 0.1,
        "bindings": [("simulation.creature", "SPIN_COST")]},
    "movement_reference_speed": {"group": "Energia", "label": "Velocidade de referencia (px/s)",
        "default": 35.0, "min": 5.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.creature", "MOVEMENT_REFERENCE_SPEED")]},
    "metabolism_adult":         {"group": "Energia", "label": "Metabolismo ADULT (E/s)",
        "default": 0.2, "min": 0.0, "max": 5.0, "step": 0.1,
        "apply": "_set_metabolism_adult", "read": "_get_metabolism_adult"},
    "metabolism_elder":         {"group": "Energia", "label": "Metabolismo ELDER (E/s)",
        "default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1,
        "apply": "_set_metabolism_elder", "read": "_get_metabolism_elder"},

    # --- Reproducao ---
    # NOTA (BIT-22): MIN_ENERGY_TO_MATE foi REMOVIDA — a reproducao sexuada agora usa fertilidade
    # persistente (creature.FERTILITY_ENERGY_THRESHOLD) + proximidade (engine.MATING_RADIUS).
    "fertility_energy_threshold": {"group": "Reproducao", "label": "Energia p/ ficar fertil",
        "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.creature", "FERTILITY_ENERGY_THRESHOLD")]},
    "mating_radius":            {"group": "Reproducao", "label": "Raio de acasalamento (px)",
        "default": 200.0, "min": 20.0, "max": 400.0, "step": 10.0,
        "bindings": [("simulation.engine", "MATING_RADIUS")]},
    "reproduction_energy_cost": {"group": "Reproducao", "label": "Custo do acasalamento",
        "default": 20.0, "min": 0.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.engine", "REPRODUCTION_ENERGY_COST")]},
    "reproduction_cooldown":    {"group": "Reproducao", "label": "Cooldown sexuado (s)",
        "default": 6.0, "min": 0.0, "max": 120.0, "step": 1.0,
        "bindings": [("simulation.engine", "REPRODUCTION_COOLDOWN")]},
    "min_energy_asexual":       {"group": "Reproducao", "label": "Energia minima p/ clonar",
        "default": 100.0, "min": 0.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.engine", "MIN_ENERGY_TO_REPRODUCE_ASEXUALLY")]},
    "asexual_energy_cost":      {"group": "Reproducao", "label": "Custo da clonagem",
        "default": 80.0, "min": 0.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.engine", "ASEXUAL_REPRODUCTION_ENERGY_COST")]},
    "asexual_cooldown":         {"group": "Reproducao", "label": "Cooldown da clonagem (s)",
        "default": 45.0, "min": 0.0, "max": 180.0, "step": 1.0,
        "bindings": [("simulation.engine", "ASEXUAL_REPRODUCTION_COOLDOWN")]},

    # --- Ecossistema ---
    # NOTA (BIT-22): estas 4 constantes sao DEFINIDAS em simulation.oasis, mas o engine as importa
    # por valor (`from simulation.oasis import ...`) e as LE em engine.step() — logo o binding e
    # simulation.engine (patchear simulation.oasis NAO afeta a copia lida pelo engine).
    "max_total_food":           {"group": "Ecossistema", "label": "Teto global de comida",
        "default": 150, "min": 0, "max": 300, "step": 1,
        "bindings": [("simulation.engine", "MAX_TOTAL_FOOD")]},
    "food_energy_value":        {"group": "Ecossistema", "label": "Energia por comida",
        "default": 50.0, "min": 5.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.food", "FOOD_ENERGY_VALUE")]},
    "oasis_spawn_chance":       {"group": "Ecossistema", "label": "Chance de oasis (/frame)",
        "default": 0.035, "min": 0.0, "max": 0.1, "step": 0.005,
        "bindings": [("simulation.engine", "OASIS_SPAWN_CHANCE_PER_FRAME")]},
    "oasis_food_spawn_chance":  {"group": "Ecossistema", "label": "Chance de comida no oasis (/frame)",
        "default": 0.22, "min": 0.0, "max": 0.5, "step": 0.01,
        "bindings": [("simulation.engine", "OASIS_FOOD_SPAWN_CHANCE")]},
    "max_active_oases":         {"group": "Ecossistema", "label": "Maximo de oasis ativos",
        "default": 6, "min": 0, "max": 12, "step": 1,
        "bindings": [("simulation.engine", "MAX_ACTIVE_OASES")]},
    "oasis_ttl_min":            {"group": "Ecossistema", "label": "TTL minimo do oasis (s)",
        "default": 25.0, "min": 5.0, "max": 120.0, "step": 1.0,
        "bindings": [("simulation.oasis", "OASIS_TTL_MIN")]},
    "oasis_ttl_max":            {"group": "Ecossistema", "label": "TTL maximo do oasis (s)",
        "default": 60.0, "min": 10.0, "max": 180.0, "step": 1.0,
        "bindings": [("simulation.oasis", "OASIS_TTL_MAX")]},

    # --- Ambiente ---
    "water_drag":               {"group": "Ambiente", "label": "Arrasto da agua (damping)",
        "default": 0.35, "min": 0.05, "max": 1.0, "step": 0.05,
        "apply": "_set_damping", "read": "_get_damping"},
    "vision_radius":            {"group": "Ambiente", "label": "Raio de visao (px)",
        "default": 80.0, "min": 20.0, "max": 200.0, "step": 5.0,
        "bindings": [("simulation.sensors", "VISION_RADIUS"),
                     ("simulation.engine", "VISION_RADIUS")]},  # copia por valor no engine!
}


# --- Setters/getters especiais (referenciados por nome nos specs; resolvidos via globals()) ---

def _set_metabolism_adult(engine, value):
    from simulation.creature import METABOLISM_RATE_BY_STAGE, LifeStage
    METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] = value   # mutacao de dict: lida por chave em runtime


def _get_metabolism_adult(engine):
    from simulation.creature import METABOLISM_RATE_BY_STAGE, LifeStage
    return METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]


def _set_metabolism_elder(engine, value):
    from simulation.creature import METABOLISM_RATE_BY_STAGE, LifeStage
    METABOLISM_RATE_BY_STAGE[LifeStage.ELDER] = value


def _get_metabolism_elder(engine):
    from simulation.creature import METABOLISM_RATE_BY_STAGE, LifeStage
    return METABOLISM_RATE_BY_STAGE[LifeStage.ELDER]


def _set_damping(engine, value):
    engine.physics.space.damping = value   # atributo do objeto Space vivo, nao de modulo


def _get_damping(engine):
    return engine.physics.space.damping


# --- API publica ---

def _module(mod):
    """Retorna o modulo (ja em sys.modules na subida do engine; importa se necessario)."""
    m = sys.modules.get(mod)
    if m is None:
        m = importlib.import_module(mod)
    return m


def get_params(engine):
    """{nome: valor corrente} para todos os parametros do registry."""
    result = {}
    for name, spec in PARAM_SPECS.items():
        if "read" in spec:
            result[name] = globals()[spec["read"]](engine)
        else:
            mod, attr = spec["bindings"][0]
            result[name] = getattr(_module(mod), attr)
    return result


def set_param(engine, name, value):
    """Aplica com clamp em [min, max]. Retorna False para nome desconhecido ou valor
    nao-numerico; True se aplicou. Aplica em TODOS os bindings (ou no `apply`)."""
    spec = PARAM_SPECS.get(name)
    if spec is None:
        return False
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    if v != v:  # NaN nunca passa no clamp de forma util
        return False

    v = max(spec["min"], min(spec["max"], v))
    if isinstance(spec["default"], int):
        v = int(round(v))

    if "apply" in spec:
        globals()[spec["apply"]](engine, v)
    else:
        for mod, attr in spec["bindings"]:
            setattr(_module(mod), attr, v)
    return True


def reset_params(engine):
    """Restaura todos os parametros ao `default` da tabela."""
    for name, spec in PARAM_SPECS.items():
        set_param(engine, name, spec["default"])
