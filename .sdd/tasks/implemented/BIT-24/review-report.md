# Review Report — BIT-24: Controles Interativos da Simulação

**Veredito:** APROVADO COM RESSALVAS — 1 bloqueante (correção pequena e localizada no dispatch de `set_time_control`).

## Gates rodados por mim
- `import main` → **OK**
- `pytest tests/ -v` → **142 passed, 6 warnings** (warnings = deprecations pré-existentes do neat-python, não relacionadas)
- `test_interactive_controls.py` → 15 testes, cobrem os 8 cenários da spec, importam `ALLOWED_SPEEDS` (sem hardcode de balanceamento/dimensões)
- `npm run build` → **OK** (34 módulos, sem erros)
- `npm run lint` → 1 erro em `src/App.jsx` (`'React' is defined but never used`), **pré-existente e fora do escopo** (confirmado: App.jsx não foi tocado por esta branch; o import já estava assim em `develop`)

---

## ERROS (bloqueantes)

### [BLOQUEANTE] `backend/main.py:59-60` — `set_time_control` com `speed` não-numérico derruba a conexão WS
O dispatch de `set_time_control` chama `engine.set_time_control(paused=..., speed=msg.get("speed"))`
sem proteger a coerção. Dentro de `engine.set_time_control` (`engine.py:88`) o guard é
`if speed is not None and float(speed) in ALLOWED_SPEEDS`. Um cliente que envie
`{"action":"set_time_control","speed":"abc"}` (ou qualquer valor JSON não-numérico não-nulo:
string, lista, objeto) faz `float(speed)` levantar `ValueError`/`TypeError`. Essa exceção **não**
é capturada — o branch de `drag/move` embrulha o `float()` em try/except (`main.py:66-69`), mas o
branch de `set_time_control` não. A exceção sobe do `while True`; o `try` externo só captura
`WebSocketDisconnect`, então ela propaga, mata a task do endpoint e **derruba a conexão**.

Reproduzido:
```
set_time_control(speed='abc')   -> RAISES ValueError
set_time_control(speed={'a':1}) -> RAISES TypeError
set_time_control(speed=None)    -> ok (no-op)
```

Isto viola diretamente:
- a docstring da própria spec (linha 88): *"Valores invalidos de speed sao ignorados (no-op)"*;
- os critérios de aceite (spec linhas 173-176 e 326): *"campos são validados/coeridos — não
  confiar no cliente"* e *"Mensagem malformada ou ação desconhecida é ignorada (nunca derruba a
  conexão)"*.

Observações:
- O snippet da spec carrega o mesmo bug latente (`float(speed) in ALLOWED_SPEEDS`), mas os
  critérios de aceite pesam mais: não confiar no cliente + nunca derrubar a conexão. A correção
  certa é tornar a coerção segura, não replicar o snippet cru.
- O teste `test_set_time_control_ignores_invalid_speed` só exercita `speed=3.0` (float válido fora
  do conjunto) — nunca um valor não-numérico —, por isso não pega o caso.

**O que fazer (escolher uma):**
1. Em `engine.set_time_control`, embrulhar a coerção: `try: s = float(speed) except (TypeError, ValueError): s = None` e só aplicar se `s in ALLOWED_SPEEDS`. (Preferível: mantém a robustez junto da regra de negócio.)
2. Ou, em `main.py`, embrulhar a chamada de `set_time_control` em try/except como já foi feito no `drag/move`.

**Também adicionar** um caso de teste em `test_interactive_controls.py` para `set_time_control(speed="abc")` (e/ou lista/dict) garantindo que é no-op e não levanta — o cenário que a suíte atual não cobre.

---

## OPORTUNIDADES (não-bloqueantes)

### [MELHORIA] `docs/arquitetura.md` — drift "2000×2000" pré-existente (BIT-22)
Confirmado como pré-existente em `develop` (linhas 17, 29, 73 e 97: mapa "2000×2000", `"width":
2000, "height": 2000`, `scale = min(canvas.w/2000, ...)`), enquanto o mapa real é 1400
(`physics.py:15-16`, BIT-22). O implementer deixou fora de escopo — decisão correta para não
misturar concerns. **Não é bloqueante.** Como o BIT-24 já editou justamente o bloco do
`state_update` (que contém o `"width": 2000` no exemplo), seria uma correção barata e coerente
aprovar de arrastão aqui, mas fica a critério do orquestrador (idealmente uma task de doc-fix
dedicada cobrindo as 4 ocorrências).

### [MELHORIA] Frontend prop-types via `/* eslint-disable react/prop-types */`
`InspectorPanel.jsx:1` e `TimeControls.jsx:1` desabilitam a regra em vez de declarar `propTypes`.
Dado o constraint "sem libs novas" (o pacote `prop-types` não está declarado em `package.json`,
só transitivamente), **é aceitável** — zero runtime, zero dependência, e mantém os arquivos do
escopo limpos no lint. Alternativa futura sem dependência: JSDoc `@param`. Não bloqueia.

### [MELHORIA] `SimulationCanvas.jsx:118-119` — fallback `data.width || 2000`
Fallback inofensivo (o state real sempre envia `width`/`height`), mas ecoa o mesmo número
mágico "2000" do drift acima. Se/quando o doc-fix for feito, alinhar o fallback (ou remover, já
que o backend sempre serializa as dimensões).

### [MELHORIA] `App.jsx:1` — lint vermelho pré-existente
`'React' is defined but never used`. Confirmado pré-existente e fora do escopo (App.jsx intocado).
Correção trivial (remover o import não usado — o projeto usa jsx-runtime) que poderia ser feita
oportunisticamente para deixar o gate de lint 100% verde, mas não é regressão da BIT-24.

---

## Confirmações de corretude (verificado, OK)
- **Acumulador de velocidade** (`main.py:82-89`): substeps de `dt` FIXO 1/30; 0.5x = 1 step/2 iter,
  2x/4x = 2/4 steps/iter; pausado não roda step mas o broadcast continua. `dt` nunca aumenta — OK.
- **Re-pin do drag** (`engine.py:136-144`): aplicado imediatamente antes de `physics.step`; solta
  criatura morta; teste 6 confirma que o re-pin vence `motor_forward=1.0`. OK.
- **Clamp de `drag_to`** aos limites `[0,width]×[0,height]` via `engine.width/height` (= map 1400),
  sem literais no teste — segue a convenção. OK.
- **Soltar no disconnect** (`main.py:74`) e **soltar no meio do step se morreu** — ambos cobertos
  (testes 7 e o handler). OK.
- **`id` único e monotônico**: todas as vias de criação de genoma (zero, `organic_crossover`,
  `clone_genome`) passam por `next_genome_id()` (`engine.py:130, 184, 216`), então `id == genome.key`
  nunca colide — `get_creature_by_id` é sólido. OK.
- **`start_drag` robusto**: `creature_id` estranho (None/str/dict) retorna `False` sem levantar. OK.
- **Contrato NEAT inalterado**: `rtneat_wrapper.py`/`neat_config.ini` não tocados; 16 in / 4 out
  intactos. OK.
- **Protocolo WS aditivo/retrocompatível**: cliente antigo que nada envia segue funcionando; campos
  novos são adições ao `state_update`. OK.
- **`to_dict()`/`get_state()`**: mantêm todos os campos antigos + adicionam os novos; suíte inteira
  (142 testes, incl. `test_oasis` que consome `get_state`) passa — sem regressão. OK.
- **Overlays no padrão existente** (badge `rgba(0,0,0,0.6)`, `position:absolute`, `zIndex:10`,
  monospace); state quente em refs + interval de 150 ms (evita re-render a 30 FPS). OK.

## Resumo
Implementação sólida e fiel à spec nos 9 passos, backend e frontend. Um único bloqueante real: o
branch de `set_time_control` no dispatch WS não coage `speed` com segurança, então um valor
não-numérico enviado pelo cliente levanta exceção e derruba a conexão — exatamente o que o critério
de aceite "não confiar no cliente / nunca derrubar a conexão" proíbe. Corrigir a coerção (no engine
ou no dispatch) + adicionar o teste do speed não-numérico e a task pode ir para implemented/. As
demais observações são não-bloqueantes.

---

## Resolução do bloqueante (orquestrador, 2026-07-16)

**Corrigido.** A coerção de `speed` foi protegida na fonte, em `engine.set_time_control`
(`backend/simulation/engine.py`): `float(speed)` agora está dentro de `try/except
(TypeError, ValueError)` com `return` (no-op) para valores não-numéricos — protege todos os
chamadores (dispatch, testes, usos futuros), não só o branch do `main.py`.

Teste adicionado: `test_set_time_control_ignores_non_numeric_speed` em
`backend/tests/test_interactive_controls.py` — cobre `"abc"`, lista e dict; confirma no-op sem
exceção.

Verificação:
- `pytest tests/` = **143 passed** (142 + o teste novo).
- Smoke test funcional end-to-end (WS real via uvicorn): `speed:"abc"` e `speed:[1,2]`
  ignorados, conexão viva, `speed` mantém o valor anterior. Também validados ao vivo: eco de
  `paused`/`speed`, `id` + campos de inspeção nas criaturas, drag completo (criatura fixada em
  ~(123,456)), e ação desconhecida / JSON malformado como no-op sem derrubar a conexão.

Veredito final: **APROVADO** — bloqueante resolvido, sem pendências.
