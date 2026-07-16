# Research — BIT-23 / simulation-core (parâmetros editáveis em runtime)

> Validações executadas ao vivo no venv do projeto (as três abaixo têm output medido).
>
> **Reverificação (2026-07-16, pós-BIT-22 mergeado):** o código derivou desde o rascunho
> inicial. Ajustes aplicados na tabela do registry: `MIN_ENERGY_TO_MATE` **foi removida**
> (reprodução sexuada virou fertilidade persistente + proximidade → expor
> `FERTILITY_ENERGY_THRESHOLD` em `simulation.creature` e `MATING_RADIUS` em `simulation.engine`);
> as 4 constantes de ecossistema agora são **definidas em `simulation.oasis`** (binding continua
> `simulation.engine`, pois é lá que são lidas por cópia); defaults atualizados para os valores
> correntes do código — `MAX_TOTAL_FOOD=110`, `OASIS_FOOD_SPAWN_CHANCE=0.18`, `MAX_ACTIVE_OASES=6`,
> `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY=100`, `ASEXUAL_REPRODUCTION_ENERGY_COST=95`.

## Arquivos relevantes

- `backend/simulation/creature.py`, `engine.py`, `oasis.py`, `food.py`, `sensors.py`, `physics.py`
- `backend/main.py` (transporte dos comandos — reutiliza a fundação do BIT-24 "Controles Interativos")

## Validações ao vivo (decidem o design)

1. **Patch de módulo funciona** para constantes lidas em runtime no próprio módulo:
   `simulation.creature.IDLE_PENALTY_RATE = 99.0` → `update()` passou a drenar ~99.8/s. ✅
2. **Defaults de função são congelados no `def`**: `oasis.OASIS_RADIUS = 999` e
   `Oasis(0,0)` continuou com `radius=150` (default avaliado na definição). ⚠️
3. **`from X import CONST` copia por valor**: `sensors.VISION_RADIUS = 200` não altera
   `engine.VISION_RADIUS` (fica 80). Parâmetros importados em mais de um módulo precisam
   de **múltiplos bindings**. ⚠️

## Mapa de tunabilidade (constante → onde é lida em runtime → binding necessário)

| Parâmetro | Leitura em runtime | Binding(s) |
|---|---|---|
| `IDLE_PENALTY_RATE`, `MOTOR_FORWARD_COST`, `SPIN_COST`, `MOVEMENT_REFERENCE_SPEED` | `creature.update()` (global do módulo) | `simulation.creature` |
| `METABOLISM_RATE_BY_STAGE` (dict) | `creature.update()` por chave | mutação de valores do dict (não rebind) |
| `REPRODUCTION_ENERGY_COST`, `REPRODUCTION_COOLDOWN`, `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`, `ASEXUAL_REPRODUCTION_ENERGY_COST`, `ASEXUAL_REPRODUCTION_COOLDOWN`, `MATING_RADIUS` | `engine` (handler + laço assexuado + laço de proximidade) | `simulation.engine` |
| `FERTILITY_ENERGY_THRESHOLD` | `creature.update()` (fertilidade persistente, BIT-22) | `simulation.creature` |
| ~~`MIN_ENERGY_TO_MATE`~~ | **REMOVIDA no BIT-22** — substituída por `FERTILITY_ENERGY_THRESHOLD` + `MATING_RADIUS` | — (não existe mais) |
| `OASIS_SPAWN_CHANCE_PER_FRAME`, `MAX_ACTIVE_OASES`, `OASIS_FOOD_SPAWN_CHANCE`, `MAX_TOTAL_FOOD` | **definidas em `simulation.oasis`**, mas o `engine` as importa por valor e as lê em `engine.step()` | `simulation.engine` (patchear `simulation.oasis` NÃO afeta a cópia lida pelo engine!) |
| `OASIS_TTL_MIN`, `OASIS_TTL_MAX` | `Oasis.__init__` lê globals do módulo em runtime | `simulation.oasis` |
| `OASIS_RADIUS`, `OASIS_FOOD_CAP` | ❌ default congelado no `def __init__` | requer mudança de código (`radius=None` → global) — **fora do escopo**, não expor |
| `Food.energy_value` | ❌ default congelado (`energy_value=32.0`, BIT-22 baixou de 40.0) | mudança pequena de código: extrair `FOOD_ENERGY_VALUE = 32.0` e usar `None`-sentinel — **incluir** (1 linha + constante) |
| `VISION_RADIUS` | `sensors.compute_vision` + `engine.get_state` (cópia) | **dois** bindings: `simulation.sensors` + `simulation.engine` |
| `space.damping` | atributo do objeto `Space` vivo | setter especial: `engine.physics.space.damping = v` |
| `VISION_FOV_DEGREES` | ❌ `VISION_FOV_RADIANS` é derivada no import | não expor (exigiria recomputar derivada; ganho baixo) |

## O que precisa ser feito

- **`backend/simulation/params.py` (novo)** — registry central:
  - `PARAM_SPECS: dict[str, ParamSpec]` com `label`, `group`, `min`, `max`, `step`,
    `bindings: list[(module_path, attr)]` **ou** `apply: Callable[[engine, float], None]`
    (caso damping/metabolismo-dict), e `default` **literal na tabela** (NÃO capturado no import —
    se capturasse o valor do módulo no import, um patch anterior contaminaria o reset).
  - `get_params(engine) -> dict[str, float]` (valores correntes),
    `set_param(engine, name, value) -> bool` (clamp em [min, max]; nome desconhecido → False),
    `reset_params(engine)`.
- **`food.py`**: `FOOD_ENERGY_VALUE = 40.0` + `def __init__(..., energy_value=None)` →
  `self.energy_value = FOOD_ENERGY_VALUE if energy_value is None else energy_value`.
- **`engine.get_state()`**: incluir `"params": get_params(self)` (≈15 floats; custo desprezível
  frente às criaturas com visão).
- **`main.py`**: ações novas no dispatch do BIT-24: `set_param` e `reset_params`.

## Perguntas em aberto

- Nenhuma bloqueante. Grupos de UI decididos: Energia, Reprodução, Ecossistema, Ambiente.
