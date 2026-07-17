# Review — BIT-26: Paineis de Metricas Populacionais

## Veredito
**APROVADO**

## Resultado dos gates (rodados pelo revisor)
- `venv\Scripts\python.exe -c "import main"` → OK
- `pytest tests/ -q` → **166 passed** (157 baseline + 9 novos), 0 failed, 8 warnings pre-existentes
- `npm run build` → OK (vite, sem erros)
- `npm test -- --run` → 1 passed

## Erros bloqueantes
Nenhum.

## Aderencia a spec (criterios de aceite, um a um)

| Criterio | Status | Evidencia |
|---|---|---|
| `state_update` com campo `metrics` aditivo, contrato completo | OK | `engine.py:354` + `metrics.py:17-27` — os 9 campos batem com o contrato; cliente antigo ignora o campo |
| `births_total`/`deaths_total` incrementam com teste das duas vias | OK | `engine.py:210` (sexuada), `engine.py:243` (assexuada), `engine.py:298` (morte, contada dentro do UNICO laco de remocao, antes de descartar a referencia); testes `test_metrics.py:70-97` cobrem morte + as duas vias |
| 1 amostra/s simulado, cap 600 | OK | `engine.py:334-337` (while com subtracao do intervalo — sem drift), deque com `maxlen=METRICS_HISTORY_MAX`; testes `test_metrics.py:100-119` |
| `GET /metrics/history` responde a lista | OK | `main.py:49-56`; teste no nivel do handler (ver desvio 1) |
| HUD com secao Metricas (numeros, chips, 4 sparklines) | OK | `MetricsPanel.jsx` + `Sparkline.jsx` (SVG puro, sem lib nova) + `ControlMenu.jsx:144-146` (entre Inspetor e Parametros); tokens do `hudTheme.js` em tudo (`accent`, `warm`, `track`, `accentSoft` existem) |
| Hint sem dados | OK | `MetricsPanel.jsx:60-62`, mesmo padrao do InspectorPanel |
| Gates verdes | OK | rodados pelo revisor (acima) |

## Avaliacao dos desvios declarados
1. **Teste do endpoint chama `main.metrics_history()` direto** — ACEITAVEL. A incompatibilidade starlette 0.27 + httpx 0.28 (remocao do kwarg `app=`) e real; a lista de testes da spec (passo 6) nao exigia teste HTTP-level; o handler e trivial (`return {"history": list(...)}`) e o teste ainda cobre payload + `json.dumps`. Ver melhoria 1.
2. **`dt = 0.5` no teste de amostragem** — ACEITAVEL. 0.5 e exato em binario; a semantica testada ("1 amostra por segundo simulado, `time` estritamente crescente") e a mesma da spec, sem flakiness de acumulo de float.
3. **Respawn do Eden nao conta em `births_total`** — CONFORME A SPEC (nao e desvio): o passo 3 manda instrumentar apenas as duas vias de reproducao. `engine.py:306-308` usa `add_creature` direto e o comportamento esta documentado em `engine.py:82-84` e no `arquitetura.md`.

## Corretude — pontos verificados alem da spec
- Hot-path de render intacto: `data.metrics` e processado no `inspectInterval` de 150 ms (`SimulationCanvas.jsx:361-372`), NAO no `ws.onmessage` — nenhum re-render novo a 30 FPS.
- Append do buffer local por cruzamento de `Math.floor(time)` funciona em 0.5x/1x/2x/4x (a 4x o poll de 150 ms avanca ~0.6 s simulado por tick, nunca pula um segundo inteiro); pausado nada apende.
- `compute_metrics` de engine vazio nao divide por zero; snapshot amostrado pos-limpeza de mortos (consistente com o `get_state()` do frame).
- Sparkline: serie constante nao divide por zero (`range = max - min || 1`); `data.length < 2` renderiza so a trilha.
- Regressoes: `git diff 08516b5` nao toca nenhuma constante de balanceamento, nenhum teste antigo, nenhum campo existente do protocolo WS. Balanceamento e retrocompatibilidade preservados.

## Oportunidades de melhoria (nao bloqueantes)
1. `backend/tests/test_metrics.py:14,83` — o teste da via assexuada usa `energy=100.0` hardcodado, que coincide com `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 100.0`. Se o limiar subir, o teste passa a nao exercitar a via silenciosamente... na verdade falharia (births == 0), o que e detectavel — mas importar a constante de `engine.py` (padrao do projeto) tornaria a intencao explicita: `energy=MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`.
2. `frontend/src/components/SimulationCanvas.jsx:91-99` — corrida benigna: se o fetch de bootstrap resolver depois de o `inspectInterval` ja ter apendado amostras, `metricsSeriesRef.current = data.history...` descarta essas amostras locais (o historico do servidor normalmente as contem, entao o impacto e nulo na pratica). Se quiser blindar: fazer merge por `time` em vez de substituir.
3. Quando o pin do venv permitir (httpx <0.28 ou starlette >=0.37), promover `test_metrics_history_endpoint_payload` a teste HTTP-level com `TestClient` para cobrir status 200 de verdade.

## Observacao operacional
Os arquivos novos (`metrics.py`, `test_metrics.py`, `Sparkline.jsx`, `MetricsPanel.jsx`, `impl-report.md`) estao **untracked** e as modificacoes **nao commitadas** na branch BIT-26 — falta o commit da task (fluxo do orquestrador).

## Resumo
Implementacao fiel a spec, contadores e amostragem corretos, HUD integrado sem tocar o hot-path de render, zero regressao (166 testes verdes, build do frontend ok). Pode fechar a task; melhorias listadas sao opcionais.
