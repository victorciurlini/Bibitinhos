# Review Report — BIT-23: Parametros Editaveis em Tempo Real

## Veredito
APROVADO — sem bloqueantes.

## Gates (rodados pelo revisor)
- `import main` -> OK import
- `pytest tests/` -> **153 passed, 6 warnings** (warnings = DeprecationWarning pre-existentes do neat-python; nao relacionados a esta task). Bate com o esperado (153).
- `test_params.py` -> 10 cenarios da spec presentes e verdes.

## ERROS (bloqueantes)
Nenhum.

## Auditoria de corretude (conferido, OK)

### Registry (params.py)
- `set_param` (params.py:156-178): clamp em [min,max] via `max(min, min(max, v))`; coercao int
  quando `isinstance(spec["default"], int)` usando `int(round(v))`; retorna `False` para nome
  desconhecido (spec None) e para valor nao-numerico (`TypeError/ValueError` no `float()`) e NaN
  (`v != v`); aplica em TODOS os bindings via `setattr(_module(mod), attr, v)`. Correto.
- `reset_params` (params.py:181-184): restaura via `set_param(engine, name, spec["default"])` —
  usa os defaults LITERAIS da tabela, nao valores capturados no import. Correto.
- Setters especiais: `_set/_get_metabolism_adult|elder` mutam `METABOLISM_RATE_BY_STAGE[stage]`
  (dict lido por chave em runtime); `_set/_get_damping` escrevem `engine.physics.space.damping`
  (Space vivo). Correto.
- `_module` (params.py:136-141): usa `sys.modules.get` com fallback `importlib.import_module`.
  Modulos ja estao carregados na subida do engine. OK.

### Bindings vs codigo real (todos conferidos no fonte pos-BIT-22)
- `idle_penalty_rate`->creature.IDLE_PENALTY_RATE (=1.2), `motor_forward_cost`->MOTOR_FORWARD_COST
  (=0.6), `spin_cost`->SPIN_COST (=1.0), `movement_reference_speed`->MOVEMENT_REFERENCE_SPEED (=35.0). OK.
- `metabolism_adult`/`elder` -> METABOLISM_RATE_BY_STAGE[ADULT=0.8]/[ELDER=2.0]. OK.
- `fertility_energy_threshold`->creature.FERTILITY_ENERGY_THRESHOLD (=60.0). OK.
- `mating_radius`->engine.MATING_RADIUS (=150.0); lido em runtime em engine.step (linhas 165-188). OK.
- `reproduction_energy_cost`->engine.REPRODUCTION_ENERGY_COST (=30.0),
  `reproduction_cooldown`->REPRODUCTION_COOLDOWN (=10.0),
  `min_energy_asexual`->MIN_ENERGY_TO_REPRODUCE_ASEXUALLY (=100.0),
  `asexual_energy_cost`->ASEXUAL_REPRODUCTION_ENERGY_COST (=95.0),
  `asexual_cooldown`->ASEXUAL_REPRODUCTION_COOLDOWN (=45.0). OK.
- Ecossistema: `max_total_food`->engine.MAX_TOTAL_FOOD (=110), `oasis_spawn_chance`->
  engine.OASIS_SPAWN_CHANCE_PER_FRAME (=0.01), `oasis_food_spawn_chance`->engine.OASIS_FOOD_SPAWN_CHANCE
  (=0.18), `max_active_oases`->engine.MAX_ACTIVE_OASES (=6) — todos DEFINIDOS em oasis mas
  importados por valor e LIDOS no namespace do engine (engine.step linhas 245-261). Binding em
  engine correto. OK.
- `food_energy_value`->food.FOOD_ENERGY_VALUE (=32.0). OK.
- `oasis_ttl_min`/`max`->oasis.OASIS_TTL_MIN (=15.0)/OASIS_TTL_MAX (=40.0) — lidos em oasis; binding
  no proprio modulo oasis. OK.
- `water_drag`->damping (default 0.35 em physics.py:11). OK.
- `vision_radius`-> DOIS bindings: sensors.VISION_RADIUS E engine.VISION_RADIUS (=80.0 em ambos).
  sensors le em runtime (sensors.py:39,54); engine copiou por valor no import — binding duplo
  correto e necessario. OK.
- MIN_ENERGY_TO_MATE: NAO existe binding para a constante removida. `test_reproducao_...` trava
  contra regressao (assert `MIN_ENERGY_TO_MATE` fora de todos os bindings). OK.

### Consistencia BACKEND <-> FRONTEND (22 chaves)
Conferido 1-a-1 o array `PARAM_SPECS` de ParamsPanel.jsx (linhas 11-41) contra o dict de
params.py: os 22 nomes, os 4 grupos, e todos os min/max/step batem EXATAMENTE. Ordem preservada.
Nenhuma chave faltando/sobrando, nenhum min/max fora de sincronia. OK.

### Frontend
- Eco vs. slider em uso: `activeParamRef` setado em `onPointerDown`, limpo em `onPointerUp`;
  `localValues` guarda o valor do slider sob o cursor; `displayValue`/`sliderValue` usam o local
  enquanto arrastando, senao o eco de `params`. Correto (ParamsPanel.jsx:116-141,163-165).
- `handleChange` (linha 126-133) envia `{action:'set_param', name, value:Number(...)}` — value
  numerico. `onChange` no input range dispara. OK.
- "Restaurar padroes" (linha 193-199) envia `{action:'reset_params'}`. OK.
- SimulationCanvas: `params` em useState alimentado no mesmo interval de 150ms
  (`if (data.params && typeof data.params === 'object') setParams(...)`), passado ao ControlMenu.
  ControlMenu renderiza `<ParamsPanel>` como 3a secao (desvio de layout APROVADO). OK.
- Sem libs novas; build OK, lint limpo (unico erro e pre-existente em App.jsx). OK.

### Regressoes / contratos
- `get_state` ganhou `"params": get_params(self)` de forma aditiva; resto do payload intacto
  (engine.py:326-331). OK.
- Dispatch em main.py aditivo (2 `elif` novos); nada removido. OK.
- Contrato NEAT (rtneat_wrapper.py / neat_config.ini) intocado. OK.
- Nenhum default de constante dos modulos foi alterado — o registry so muda em runtime; cada
  teste reseta no teardown (fixture `env`). Suite existente permanece verde. OK.
- food.py: sentinel `energy_value=None` -> `FOOD_ENERGY_VALUE if energy_value is None else ...`.
  Chamadas existentes nao passam `energy_value`, comportamento identico. OK.

## OPORTUNIDADES (nao-bloqueantes)
1. `ParamsPanel.jsx:126-133` `handleChange`: quando o slider NAO esta sob o cursor (ex.: mudanca
   via teclado com foco mas sem pointerdown, ou clique direto na trilha), `activeParamRef.current`
   pode nao bater com `spec.name`, entao o `localValues` nao e atualizado e o valor exibido so se
   corrige no proximo eco (~150ms). Efeito e um flicker minimo e transitorio; nao afeta o backend
   (o comando e sempre enviado). Baixa prioridade.
2. `ParamsPanel.jsx:120-124` `handlePointerUp` limpa `localValues` inteiro (`setLocalValues({})`).
   Como so ha um slider ativo por vez, funciona; poderia limpar so a chave ativa por clareza.
   Cosmetico.
3. `test_params.py` cobre efeito real via `update()` apenas para `idle_penalty_rate` (cenario 1).
   Os demais bindings sao testados no nivel de atributo/estado (suficiente para a spec, que pedia
   efeito real so no cenario 1). Poderia haver 1 teste de efeito para `water_drag`/`vision_radius`
   no loop, mas nao e exigido pela spec.
4. Duplicacao inevitavel dos metadados (PARAM_SPECS no backend e no frontend). A spec decidiu
   conscientemente contra um endpoint de schema para 22 params; a divergencia e pega por review.
   Se a tabela crescer, considerar um teste de contrato que compare as duas listas. Fora do escopo.

## Resumo
Pode fechar a task. Implementacao backend e frontend aderentes a spec, 22 bindings corretos contra
o codigo pos-BIT-22, consistencia backend<->frontend exata, 153 testes verdes, contratos NEAT e
payload preservados. Desvio de layout (painel como 3a secao do ControlMenu) tratado como aprovado.
Nenhum bloqueante.
