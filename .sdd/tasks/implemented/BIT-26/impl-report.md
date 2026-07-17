# Relatorio de implementacao — BIT-26: Paineis de Metricas Populacionais

## Status
CONCLUIDO

## Passos executados

Segui os 11 passos da spec na ordem, sem expansao de escopo.

## Arquivos modificados

| Arquivo | Alteracao |
|---|---|
| `backend/simulation/metrics.py` | **criado** — `compute_metrics(engine)` (funcao pura, JSON-safe) + `METRICS_SAMPLE_INTERVAL = 1.0` e `METRICS_HISTORY_MAX = 600`, exatamente como na spec. |
| `backend/simulation/engine.py` | imports (`deque`, modulo metrics); `__init__` ganha `births_total`, `deaths_total`, `metrics_history` (deque com `maxlen=METRICS_HISTORY_MAX`) e `_metrics_accumulator`; `step()` soma `births_total` apos as duas vias de reproducao (sexuada e assexuada), incrementa `deaths_total` no laco de remocao de mortos e faz a amostragem do historico ao final do step (while sobre o acumulador, 1 amostra por cruzamento de intervalo); `get_state()` ganha o campo `"metrics"`. |
| `backend/main.py` | novo endpoint REST `GET /metrics/history` retornando `{"history": list(engine.metrics_history)}`. |
| `backend/tests/test_metrics.py` | **criado** — 9 testes: agregados zerados em engine vazio (sem ZeroDivisionError), contagem de populacao/fases, `deaths_total` apos morte por inanicao, `births_total` nas vias assexuada E sexuada, amostragem de 3 s -> 3 amostras com `time` estritamente crescente, cap do deque (`maxlen == METRICS_HISTORY_MAX`), `get_state()["metrics"]` presente e `json.dumps`-avel, payload do handler do endpoint. Constantes importadas, nunca hardcodadas (padrao do projeto). |
| `frontend/src/components/Sparkline.jsx` | **criado** — SVG puro: props `data`, `width=210`, `height=36`, `color=HUD.accent`; polyline normalizada ao min/max da janela; `data.length < 2` renderiza so a linha de base em `HUD.track`; serie constante nao divide por zero. |
| `frontend/src/components/MetricsPanel.jsx` | **criado** — linha de numeros (Populacao/Comida/Oasis), 4 chips EGG/JUV/ADU/ELD, 4 sparklines com valor corrente ao lado (Populacao, Energia media, Nascimentos em accent, Mortes em warm); `metrics == null` -> hint no estilo do InspectorPanel ("Aguardando dados da simulacao."). Tokens do hudTheme.js em tudo. |
| `frontend/src/components/SimulationCanvas.jsx` | estados `metrics`/`metricsSeries` + `metricsSeriesRef`; fetch de bootstrap em `GET /metrics/history` no mount (erro de rede silencioso); no `inspectInterval` (150 ms) existente: `setMetrics` + append de 1 amostra por segundo simulado (comparacao de `Math.floor(time)`) com cap 600 (`METRICS_SERIES_MAX`, espelho da constante do backend); props novas passadas ao ControlMenu. |
| `frontend/src/components/ControlMenu.jsx` | secao `Metricas` entre Inspetor e Parametros, renderizando `<MetricsPanel metrics={metrics} series={metricsSeries} />`; comentario de topo atualizado. |
| `docs/arquitetura.md` | campo `metrics` documentado no payload do `state_update`; nova subsecao `GET /metrics/history`; linha de limitacoes conhecidas atualizada (paineis de metricas existem desde o BIT-26). |

## Problemas encontrados / decisoes

1. **Teste do endpoint sem TestClient**: o venv tem `starlette 0.27.0` + `httpx 0.28.1`, combinacao em que o `TestClient` do Starlette quebra (remocao do kwarg `app=` no httpx 0.28). Como a lista de testes da spec nao exige teste HTTP-level, o teste chama o handler `main.metrics_history()` diretamente (o que tambem cobre o import de `main` dentro da suite). O criterio "responde 200" fica coberto pela logica trivial do handler + verificacao manual.
2. **dt do teste de amostragem**: usei `dt = 0.5` (exato em binario) em vez de `1/30` para "3 s simulados -> 3 amostras" — com `dt = 1/30`, 90 somas de float podem fechar em 2.999... e deixar o teste flaky. A semantica testada e a mesma (1 amostra por segundo simulado, `time` crescente).
3. **Eden nao conta como nascimento**: `births_total` soma apenas as duas vias de reproducao, como a spec pede (passo 3). O respawn anti-extincao do Jardim do Eden usa `add_creature` direto e nao incrementa o contador — documentado em comentario no `__init__` e no arquitetura.md.
4. **Rotulo da secao**: usei `Metricas` (sem acento), coerente com os rotulos existentes do ControlMenu ("Parametros"); o `sectionLabelStyle` ja aplica uppercase visual.
5. **Amostragem no fim do step, pos-limpeza de mortos**: o snapshot amostrado reflete o mesmo estado que o `get_state()` do frame veria (nunca inclui criatura morta pendente de remocao).

## Resultado dos gates

- `venv\Scripts\python.exe -c "import main"` -> `OK - app importa`
- `pytest tests/ -q` -> **166 passed** (157 baseline + 9 novos), 0 failed, 8 warnings pre-existentes (neat-python/pydantic)
- `npm run test` -> 1 passed (suite existente)
- `npm run build` -> vite build ok (40 modulos, sem erros)

## Pontos de atencao para o revisor

- O buffer local do frontend (`metricsSeriesRef`) apende pelo criterio `Math.floor(m.time)` maior que o da ultima amostra — igual ao backend em regime normal, mas as amostras do WS e as do deque do backend podem divergir em sub-segundo (fase do acumulador vs. floor do time). Irrelevante para sparklines de 10 min.
- Sob `speed = 4x`, o backend pode gerar ate 4 amostras/s de historico enquanto o frontend (150 ms de interval) acompanha; sob pausa, nada e apendado (time nao avanca). Comportamento esperado.
- `compute_metrics` roda 2x por frame de broadcast quando ha cruzamento de amostra (uma no step, uma no get_state) — O(n) sobre a populacao, custo desprezivel.
