# Spec — BIT-23: Parâmetros Editáveis em Tempo Real

**Linear:** N/A
**Risco:** medium
**Camada(s):** Múltiplas — Backend (Simulação) + API/WebSocket + Frontend

**Depende de:** BIT-24 — "Controles Interativos da Simulação" (fundação de comandos
cliente→servidor no `websocket_endpoint` e padrão de overlays no frontend). Não iniciar antes
do BIT-24 estar em `develop`.

> **Nota de numeração:** a fundação de dispatch é a task "Controles Interativos", renumerada de
> BIT-22 para **BIT-24** (o número 22 já foi ocupado pela "Reprodução Sexuada Emergente"
> mergeada). Referências a "BIT-22" neste doc que falam de *dispatch/overlays* são o BIT-24; as
> NOTAs internas que citam BIT-22 referem-se às mudanças de código da reprodução mergeada.

---

## Demanda

O developer quer ajustar as constantes de balanceamento da simulação **em tempo real**, pela
UI, sem editar código nem reiniciar o backend: economia de energia, custos/limiares de
reprodução, ecossistema (oásis/comida) e ambiente (arrasto de água, visão). Ajustes valem só
em memória (reiniciou, voltam os defaults do código) e há botão de reset.

## Abordagem técnica

Um **registry central** (`backend/simulation/params.py`) mapeia cada parâmetro exposto para
seus *bindings* reais (módulo + atributo) ou para um setter especial, com min/max/step/grupo.
O design é ditado por três semânticas do Python **validadas ao vivo** nesta investigação
(ver `research/simulation-core.md`): (1) patch de atributo de módulo funciona para constantes
lidas em runtime; (2) defaults de função são congelados no `def` — por isso `Food.energy_value`
precisa de um refactor de 2 linhas e `OASIS_RADIUS`/`OASIS_FOOD_CAP` ficam **fora**; (3)
`from X import CONST` copia por valor — por isso vários parâmetros têm bindings no
`simulation.engine` (onde a cópia é lida) e `vision_radius` tem **dois** bindings. O transporte
reutiliza o dispatch do BIT-24 (`set_param`/`reset_params`) e o eco vem em `state["params"]`.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/params.py` | criar | Registry `PARAM_SPECS` + `get_params`/`set_param`/`reset_params` |
| `backend/simulation/food.py` | modificar | Extrair `FOOD_ENERGY_VALUE` (default congelado → sentinel `None`) |
| `backend/simulation/engine.py` | modificar | `get_state()` inclui `"params"` |
| `backend/main.py` | modificar | Ações `set_param` e `reset_params` no dispatch do BIT-24 |
| `frontend/src/components/ParamsPanel.jsx` | criar | Painel colapsável com sliders por grupo + reset |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | Compor `ParamsPanel` e alimentá-lo com `params` do state |
| `backend/tests/test_params.py` | criar | Testes do registry (bindings, clamp, reset, setters especiais) |
| `docs/simulacao.md` | modificar | Nota de que os valores são defaults tunáveis em runtime |

## Passos de implementação

### 1. `food.py` — destravar `energy_value` (independente)

```python
FOOD_ENERGY_VALUE = 32.0  # BIT-22: era 40.0 (BIT-20 subira de 20.0) — recompensa por comer
                          # (tunavel em runtime, BIT-23)

class Food:
    def __init__(self, engine, x, y, energy_value=None):
        ...
        self.energy_value = FOOD_ENERGY_VALUE if energy_value is None else energy_value
```

Remover o valor hardcoded `32.0` do default (hoje `energy_value=32.0`). Chamadas existentes não
passam `energy_value`, então o comportamento é idêntico.

### 2. `params.py` — registry central (núcleo da task)

Estrutura: dict de specs. Duas formas de aplicação — `bindings` (lista de
`(caminho_do_modulo, atributo)`, todos setados via `setattr(sys.modules[mod], attr, valor)`)
ou `apply`/`read` (callables recebendo `engine`, para alvos que não são atributo de módulo).
`default` é **literal na tabela** (não capturado dinamicamente — é a fonte de verdade do
reset e dos testes).

```python
"""Registry de parametros tunaveis em runtime (BIT-23).

Regras que definem o que pode entrar aqui (validadas ao vivo, ver research):
- So constantes LIDAS EM RUNTIME no modulo dono (patch de modulo funciona).
- Constantes importadas por valor em outro modulo precisam de binding EM CADA COPIA.
- Defaults de funcao sao congelados no `def` — nao adianta patchear o modulo.
Ajustes valem so em memoria: reiniciar o backend restaura os defaults do codigo.
"""
import sys

PARAM_SPECS = {
    # --- Energia ---
    "idle_penalty_rate":        {"group": "Energia", "label": "Imposto de ociosidade (E/s)",
        "default": 1.2, "min": 0.0, "max": 5.0, "step": 0.1,
        "bindings": [("simulation.creature", "IDLE_PENALTY_RATE")]},
    "motor_forward_cost":       {"group": "Energia", "label": "Custo de propulsao (E/s)",
        "default": 0.6, "min": 0.0, "max": 5.0, "step": 0.1,
        "bindings": [("simulation.creature", "MOTOR_FORWARD_COST")]},
    "spin_cost":                {"group": "Energia", "label": "Custo de girar parado (E/s)",
        "default": 1.0, "min": 0.0, "max": 5.0, "step": 0.1,
        "bindings": [("simulation.creature", "SPIN_COST")]},
    "movement_reference_speed": {"group": "Energia", "label": "Velocidade de referencia (px/s)",
        "default": 35.0, "min": 5.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.creature", "MOVEMENT_REFERENCE_SPEED")]},
    "metabolism_adult":         {"group": "Energia", "label": "Metabolismo ADULT (E/s)",
        "default": 0.8, "min": 0.0, "max": 5.0, "step": 0.1,
        "apply": "_set_metabolism_adult", "read": "_get_metabolism_adult"},
    "metabolism_elder":         {"group": "Energia", "label": "Metabolismo ELDER (E/s)",
        "default": 2.0, "min": 0.0, "max": 10.0, "step": 0.1,
        "apply": "_set_metabolism_elder", "read": "_get_metabolism_elder"},

    # --- Reproducao ---
    # NOTA (BIT-22): MIN_ENERGY_TO_MATE foi REMOVIDA — a reproducao sexuada agora usa fertilidade
    # persistente (creature.FERTILITY_ENERGY_THRESHOLD) + proximidade (engine.MATING_RADIUS).
    "fertility_energy_threshold": {"group": "Reproducao", "label": "Energia p/ ficar fertil",
        "default": 60.0, "min": 0.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.creature", "FERTILITY_ENERGY_THRESHOLD")]},
    "mating_radius":            {"group": "Reproducao", "label": "Raio de acasalamento (px)",
        "default": 150.0, "min": 20.0, "max": 400.0, "step": 10.0,
        "bindings": [("simulation.engine", "MATING_RADIUS")]},
    "reproduction_energy_cost": {"group": "Reproducao", "label": "Custo do acasalamento",
        "default": 30.0, "min": 0.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.engine", "REPRODUCTION_ENERGY_COST")]},
    "reproduction_cooldown":    {"group": "Reproducao", "label": "Cooldown sexuado (s)",
        "default": 10.0, "min": 0.0, "max": 120.0, "step": 1.0,
        "bindings": [("simulation.engine", "REPRODUCTION_COOLDOWN")]},
    "min_energy_asexual":       {"group": "Reproducao", "label": "Energia minima p/ clonar",
        "default": 100.0, "min": 0.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.engine", "MIN_ENERGY_TO_REPRODUCE_ASEXUALLY")]},
    "asexual_energy_cost":      {"group": "Reproducao", "label": "Custo da clonagem",
        "default": 95.0, "min": 0.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.engine", "ASEXUAL_REPRODUCTION_ENERGY_COST")]},
    "asexual_cooldown":         {"group": "Reproducao", "label": "Cooldown da clonagem (s)",
        "default": 45.0, "min": 0.0, "max": 180.0, "step": 1.0,
        "bindings": [("simulation.engine", "ASEXUAL_REPRODUCTION_COOLDOWN")]},

    # --- Ecossistema ---
    # NOTA (BIT-22): estas 4 constantes sao DEFINIDAS em simulation.oasis, mas o engine as importa
    # por valor (`from simulation.oasis import ...`) e as LE em engine.step() — logo o binding e
    # simulation.engine (patchear simulation.oasis NAO afeta a copia lida pelo engine).
    "max_total_food":           {"group": "Ecossistema", "label": "Teto global de comida",
        "default": 110, "min": 0, "max": 300, "step": 1,
        "bindings": [("simulation.engine", "MAX_TOTAL_FOOD")]},
    "food_energy_value":        {"group": "Ecossistema", "label": "Energia por comida",
        "default": 32.0, "min": 5.0, "max": 100.0, "step": 1.0,
        "bindings": [("simulation.food", "FOOD_ENERGY_VALUE")]},
    "oasis_spawn_chance":       {"group": "Ecossistema", "label": "Chance de oasis (/frame)",
        "default": 0.01, "min": 0.0, "max": 0.1, "step": 0.005,
        "bindings": [("simulation.engine", "OASIS_SPAWN_CHANCE_PER_FRAME")]},
    "oasis_food_spawn_chance":  {"group": "Ecossistema", "label": "Chance de comida no oasis (/frame)",
        "default": 0.18, "min": 0.0, "max": 0.5, "step": 0.01,
        "bindings": [("simulation.engine", "OASIS_FOOD_SPAWN_CHANCE")]},
    "max_active_oases":         {"group": "Ecossistema", "label": "Maximo de oasis ativos",
        "default": 6, "min": 0, "max": 12, "step": 1,
        "bindings": [("simulation.engine", "MAX_ACTIVE_OASES")]},
    "oasis_ttl_min":            {"group": "Ecossistema", "label": "TTL minimo do oasis (s)",
        "default": 15.0, "min": 5.0, "max": 120.0, "step": 1.0,
        "bindings": [("simulation.oasis", "OASIS_TTL_MIN")]},
    "oasis_ttl_max":            {"group": "Ecossistema", "label": "TTL maximo do oasis (s)",
        "default": 40.0, "min": 10.0, "max": 180.0, "step": 1.0,
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
```

Setters/getters especiais (funções de módulo em `params.py`; nos specs acima referenciadas
por **nome** e resolvidas via `globals()[name]` — mantém a tabela serializável/inspecionável):

```python
def _set_metabolism_adult(engine, value):
    from simulation.creature import METABOLISM_RATE_BY_STAGE, LifeStage
    METABOLISM_RATE_BY_STAGE[LifeStage.ADULT] = value   # mutacao de dict: lida por chave em runtime

def _get_metabolism_adult(engine):
    from simulation.creature import METABOLISM_RATE_BY_STAGE, LifeStage
    return METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]

# _set/_get_metabolism_elder: analogos, com LifeStage.ELDER

def _set_damping(engine, value):
    engine.physics.space.damping = value   # atributo do objeto Space vivo, nao de modulo

def _get_damping(engine):
    return engine.physics.space.damping
```

API pública:

```python
def get_params(engine):
    """{nome: valor corrente} para todos os parametros do registry."""

def set_param(engine, name, value):
    """Aplica com clamp em [min, max]. Retorna False para nome desconhecido ou valor
    nao-numerico; True se aplicou. Aplica em TODOS os bindings (ou no `apply`)."""

def reset_params(engine):
    """Restaura todos os parametros ao `default` da tabela."""
```

Implementação de `set_param`: coerção `float(value)` (int para specs de step 1 — usar
`int(round(v))` quando `isinstance(spec["default"], int)`), clamp, depois
`for mod, attr in bindings: setattr(sys.modules[mod], attr, v)`. Os módulos já estão em
`sys.modules` (importados pelo engine na subida); se não estiverem, `importlib.import_module`.

> **Fora do escopo, não expor** (defaults congelados no `def` — exigiriam refactors além do
> combinado): `OASIS_RADIUS`, `OASIS_FOOD_CAP`, `VISION_FOV_DEGREES` (derivada
> `VISION_FOV_RADIANS` congelada no import), `STARTING_ENERGY`/`max_energy`, `FOOD_TTL`
> (tunável, mas irrelevante para o objetivo — cortado por parcimônia).
> `oasis_ttl_min > oasis_ttl_max` não precisa de validação cruzada: `random.uniform(a, b)`
> aceita `a > b` sem erro (comportamento verificado da stdlib).

### 3. `engine.py` — expor no state

Em `get_state()` (import no topo do módulo: `from simulation.params import get_params`):

```python
"params": get_params(self),
```

### 4. `main.py` — ações no dispatch (depende do BIT-24)

No dispatch do `websocket_endpoint`, adicionar:

```python
            elif action == "set_param":
                set_param(engine, msg.get("name"), msg.get("value"))
            elif action == "reset_params":
                reset_params(engine)
```

(com `from simulation.params import set_param, reset_params` no topo.)

### 5. `ParamsPanel.jsx` (novo) + composição no canvas

- Overlay colapsável em `position: absolute; bottom: 10px; left: 10px` (canto livre — status
  fica no topo-esquerdo, inspetor à direita, tempo embaixo no centro). Colapsado: só um botão
  "⚙ Parâmetros". Expandido: grupos (Energia, Reproducao, Ecossistema, Ambiente) com um
  `<input type="range">` + valor numérico por parâmetro, e botão "Restaurar padrões"
  (envia `{"action":"reset_params"}`).
- Metadados (label/min/max/step/grupo): **hardcodados no componente**, espelhando a tabela do
  `params.py` (o state só transporta `{nome: valor}`). Divergência é pega pelo critério de
  aceite; não vale a pena um endpoint de schema para 22 parâmetros.
- Cada mudança de slider envia `{"action":"set_param","name":...,"value":...}` no evento
  `onChange` (taxa do próprio evento; sem throttle extra — mensagens são minúsculas).
- **Eco vs. slider em uso**: os valores exibidos vêm de `state.params` (via o mesmo interval
  de ~150 ms do BIT-24), **exceto** o slider atualmente sob o cursor (guardar `activeParam`
  em ref durante `onPointerDown→onPointerUp`) — evita o eco "brigar" com a mão do usuário.
- `SimulationCanvas.jsx`: compor `<ParamsPanel params={params} onCommand={sendCommand} />`.

### 6. `backend/tests/test_params.py` (novo)

Importar tudo de `simulation.params` e módulos alvo; **restaurar via `reset_params` no
teardown** de cada teste (fixture) para não vazar estado entre testes. Cobrir:

1. `set_param` em binding simples: `set_param(eng, "idle_penalty_rate", 3.0)` →
   `simulation.creature.IDLE_PENALTY_RATE == 3.0` **e** uma `Creature` ADULT parada passa a
   drenar na taxa nova via `update()` (efeito real, não só o atributo).
2. Multi-binding: `set_param(eng, "vision_radius", 120.0)` → `sensors.VISION_RADIUS == 120.0`
   **e** `engine.VISION_RADIUS == 120.0` (as duas cópias).
3. Clamp: valor acima do `max` aplica o `max`; abaixo do `min` aplica o `min`.
4. Nome desconhecido → `False`, nada muda; valor não-numérico (`"abc"`, `None`) → `False`.
5. Setter especial: `set_param(eng, "water_drag", 0.9)` → `engine.physics.space.damping == 0.9`;
   `metabolism_adult` altera `METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]`.
6. Parâmetro inteiro: `set_param(eng, "max_total_food", 75.6)` →
   `engine.MAX_TOTAL_FOOD == 76` (int, não float).
7. `reset_params` restaura **todos** aos defaults da tabela após alterar vários.
8. `get_params` retorna todas as chaves de `PARAM_SPECS` e `engine.get_state()["params"]`
   idem.
9. `Food(engine, 0, 0)` usa `FOOD_ENERGY_VALUE` corrente (patch no módulo muda comida nova).
10. Parâmetros de reprodução (substituíram o antigo `MIN_ENERGY_TO_MATE`):
    `set_param(eng, "fertility_energy_threshold", 40.0)` →
    `simulation.creature.FERTILITY_ENERGY_THRESHOLD == 40.0`; `set_param(eng, "mating_radius", 200.0)`
    → `simulation.engine.MATING_RADIUS == 200.0`. Nenhuma spec referencia `MIN_ENERGY_TO_MATE`
    (constante removida no BIT-22) — garante que a tabela não regrediu para o binding morto.

## Contratos técnicos

### Backend (Simulação)

- `simulation/params.py`: `PARAM_SPECS` (22 parâmetros, 4 grupos),
  `get_params(engine) -> dict[str, float|int]`, `set_param(engine, name, value) -> bool`,
  `reset_params(engine) -> None`.
- `simulation/food.py`: constante nova `FOOD_ENERGY_VALUE = 40.0`;
  `Food.__init__(..., energy_value=None)` (sentinel).
- Contrato de I/O do NEAT: **inalterado**. Nenhuma constante de `rtneat_wrapper.py`/
  `neat_config.ini` é exposta (mutação genética em runtime fica para task futura, se houver).

### API/WebSocket

```jsonc
// cliente → servidor (aditivo ao dispatch do BIT-24)
{"action": "set_param", "name": "idle_penalty_rate", "value": 2.5}
{"action": "reset_params"}

// servidor → cliente: state_update ganha
"params": {"idle_penalty_rate": 1.2, "fertility_energy_threshold": 60.0, ...}  // 22 chaves
```

### Frontend

- `ParamsPanel.jsx`: props `{ params, onCommand }`; metadados locais espelhando `PARAM_SPECS`.

## Critérios de aceite

- [ ] Arrastar o slider "Imposto de ociosidade" para 5.0 com a simulação rodando muda o
      comportamento **visivelmente** (criaturas paradas morrem rápido) sem reiniciar nada.
- [ ] "Raio de visão" em 200 aumenta o cone desenhado no canvas **e** o alcance real dos
      sensores (o valor ecoado em `vision_radius` do state alimenta o desenho — as duas cópias
      do binding mudam juntas).
- [ ] "Arrasto da água" em 0.9 deixa as criaturas visivelmente mais "deslizantes".
- [ ] "Restaurar padrões" volta todos os sliders e o comportamento aos valores do código.
- [ ] Reiniciar o backend descarta todos os ajustes (nada persistido).
- [ ] Valores fora de [min, max] enviados por cliente adulterado são clampados no servidor.
- [ ] Slider sendo arrastado não "briga" com o eco do servidor.
- [ ] `pytest backend/tests/` 100% verde, incluindo os 10 cenários do passo 6 — e a suíte
      existente permanece verde (os testes atuais importam as constantes dos módulos; como o
      registry só muda valores em runtime e cada teste reseta, não há interferência).
- [ ] `docs/simulacao.md` anotado: valores são defaults, tunáveis em runtime via painel (BIT-23).

## Rollback

Deletar `backend/simulation/params.py`, `frontend/src/components/ParamsPanel.jsx` e
`backend/tests/test_params.py`; reverter `food.py`, `engine.py`, `main.py`,
`SimulationCanvas.jsx` e `docs/simulacao.md`. Sem migração de dados. Se apenas um parâmetro
se mostrar problemático (ex.: oscilação populacional), removê-lo de `PARAM_SPECS` + do painel
resolve sem rollback total.
