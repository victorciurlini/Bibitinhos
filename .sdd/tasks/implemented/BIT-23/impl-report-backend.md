# Impl report — BIT-23 (Backend): Parâmetros Editáveis em Tempo Real

## Status
CONCLUÍDO

## Passos executados
Backend apenas (passos 1, 2, 3, 4, 6 da spec + nota em docs). O passo 5 (frontend) fica fora do escopo.

1. `food.py` — extraída constante `FOOD_ENERGY_VALUE = 32.0` e trocado o default literal por
   sentinel `energy_value=None` no `__init__`, com
   `self.energy_value = FOOD_ENERGY_VALUE if energy_value is None else energy_value`. Comentário
   explica o porquê do sentinel (default de função é congelado no `def`).
2. `params.py` — CRIADO. Registry `PARAM_SPECS` com 22 parâmetros em 4 grupos (Energia,
   Reproducao, Ecossistema, Ambiente), setters/getters especiais
   (`_set/_get_metabolism_adult`, `_set/_get_metabolism_elder`, `_set/_get_damping`) resolvidos
   via `globals()[name]`, e API `get_params`/`set_param`/`reset_params`. Bindings aplicados via
   `setattr(sys.modules[mod], attr, v)`; coerção `float`, clamp em [min,max], `int(round(v))`
   quando `default` é int, `False` para nome desconhecido/valor não-numérico/NaN.
3. `engine.py` — import `from simulation.params import get_params` no topo; `get_state()` agora
   inclui `"params": get_params(self)`.
4. `main.py` — import `from simulation.params import set_param, reset_params`; adicionados os
   ramos `elif action == "set_param"` e `elif action == "reset_params"` ao dispatch do BIT-24.
6. `tests/test_params.py` — CRIADO com os 10 cenários da spec + fixture `env` que reseta via
   `reset_params` no teardown.
- `docs/simulacao.md` — adicionada nota (BIT-23) de que os valores são defaults tunáveis em
  runtime via painel, e que reiniciar o backend restaura os defaults.

## Arquivos modificados/criados
- `backend/simulation/food.py` (modificado) — constante `FOOD_ENERGY_VALUE` + sentinel `None`.
- `backend/simulation/params.py` (criado) — registry + API + setters especiais.
- `backend/simulation/engine.py` (modificado) — import + `"params"` no `get_state()`.
- `backend/main.py` (modificado) — import + 2 ramos no dispatch do websocket.
- `backend/tests/test_params.py` (criado) — 10 testes.
- `docs/simulacao.md` (modificado) — nota BIT-23 no cabeçalho do documento.

## Problemas/decisões
- Todos os defaults da tabela foram reconferidos contra o código atual (pós-BIT-22) e batem:
  `FERTILITY_ENERGY_THRESHOLD=60.0`, `MATING_RADIUS=150.0`, `MAX_TOTAL_FOOD=110`,
  `OASIS_FOOD_SPAWN_CHANCE=0.18`, `MAX_ACTIVE_OASES=6`, `OASIS_SPAWN_CHANCE_PER_FRAME=0.01`,
  `FOOD_ENERGY_VALUE=32.0`, damping default `0.35`, metabolismo ADULT `0.8`/ELDER `2.0`.
  `MIN_ENERGY_TO_MATE` de fato não existe mais; o teste 10 trava contra regressão para esse
  binding morto.
- `set_param` também rejeita NaN (não-numérico útil): `float("nan")` passaria por `float()` mas
  não é clampável, então retorna `False`. Decisão defensiva; não muda o contrato da spec.
- Nenhum default de constante nos módulos foi alterado — o registry só muda valores em runtime,
  e cada teste reseta no teardown, então a suíte existente não sofre interferência.
- Nada tocado em `frontend/`, `rtneat_wrapper.py` ou `neat_config.ini`.

## Resultado dos gates
- `import main` → `OK import`.
- `pytest tests/` → **153 passed, 6 warnings** (warnings são DeprecationWarning pré-existentes do
  neat-python, não relacionados a esta task).
- `pytest tests/test_params.py` → **10 passed** (os 10 cenários do passo 6).
