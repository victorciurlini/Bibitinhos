# Spec — BIT-26: Painéis de Métricas Populacionais

**Linear:** N/A
**Risco:** medium
**Camada(s):** Múltiplas — Backend (Simulação) + API/WebSocket + Frontend

---

## Demanda

Dar visibilidade à dinâmica populacional da simulação: um painel no HUD com os agregados correntes (população, distribuição por fase de vida, energia/idade médias, nascimentos/mortes acumulados, comida e oásis) e mini-gráficos (sparklines) da evolução dessas métricas ao longo do tempo.

## Abordagem técnica

O backend passa a ser a fonte canônica das métricas: o engine ganha contadores incrementais de nascimentos/mortes e um histórico amostrado a cada 1 s simulado (deque com cap), calculados por um novo módulo `metrics.py`. Os agregados correntes entram como campo `metrics` no `state_update` existente (aditivo, retrocompatível) e o histórico é exposto via REST `GET /metrics/history` só para bootstrap do painel — o broadcast a 30 FPS não é inflado com séries. No frontend, um `MetricsPanel` com sparklines em **SVG puro** (sem lib de gráficos — o HUD é todo custom e os gráficos são pequenos) acumula os pontos localmente a partir do `metrics` de cada frame.

Fonte no servidor (e não no cliente) porque: sobrevive a reconexões do frontend, e é reutilizada pelo modo headless (BIT-28).

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/simulation/metrics.py` | criar | `compute_metrics(engine)` + constantes de amostragem |
| `backend/simulation/engine.py` | modificar | contadores births/deaths, histórico amostrado, campo `metrics` no `get_state()` |
| `backend/main.py` | modificar | endpoint `GET /metrics/history` |
| `backend/tests/test_metrics.py` | criar | testes dos contadores, amostragem e payload |
| `frontend/src/components/Sparkline.jsx` | criar | mini-gráfico de linha SVG reutilizável |
| `frontend/src/components/MetricsPanel.jsx` | criar | painel de métricas (números correntes + sparklines) |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | estado `metrics` + buffer local de série temporal |
| `frontend/src/components/ControlMenu.jsx` | modificar | nova seção "Métricas" |
| `docs/arquitetura.md` | modificar | documentar campo `metrics` e endpoint novo |

## Passos de implementação

1. **Criar `backend/simulation/metrics.py`:**
   ```python
   METRICS_SAMPLE_INTERVAL = 1.0   # segundos simulados entre amostras do histórico
   METRICS_HISTORY_MAX = 600       # ~10 min de história

   def compute_metrics(engine):
       """Agregados populacionais do estado corrente do engine (JSON-safe)."""
       creatures = engine.creatures
       n = len(creatures)
       stage_counts = {"EGG": 0, "JUVENILE": 0, "ADULT": 0, "ELDER": 0}
       for c in creatures:
           stage_counts[c.life_stage.name] += 1
       return {
           "time": engine.time_elapsed,
           "population": n,
           "stage_counts": stage_counts,
           "avg_energy": (sum(c.energy for c in creatures) / n) if n else 0.0,
           "avg_age": (sum(c.age for c in creatures) / n) if n else 0.0,
           "births_total": engine.births_total,
           "deaths_total": engine.deaths_total,
           "food_count": len(engine.foods),
           "oases_count": len(engine.oases),
       }
   ```
2. **Estender `SimulationEngine.__init__`** (engine.py): `self.births_total = 0`, `self.deaths_total = 0`, `self.metrics_history = deque(maxlen=METRICS_HISTORY_MAX)`, `self._metrics_accumulator = 0.0` (importar `deque` e o módulo metrics).
3. **Instrumentar `engine.step()`:**
   - Onde filhos sexuados/assexuados são criados (linhas ~162-231): `self.births_total += len(<filhos criados>)` — somar ambas as vias.
   - Onde criaturas mortas são removidas (linhas ~279-286): contar removidas e `self.deaths_total += <contagem>`.
   - Ao final do step: `self._metrics_accumulator += dt`; enquanto `>= METRICS_SAMPLE_INTERVAL`, fazer `self.metrics_history.append(compute_metrics(self))` e subtrair o intervalo (uma amostra por cruzamento; com dt=1/30 nunca acumula 2 intervalos).
4. **`get_state()`** ganha `"metrics": compute_metrics(self)`.
5. **`backend/main.py`:** novo endpoint REST:
   ```python
   @app.get("/metrics/history")
   def metrics_history():
       return {"history": list(engine.metrics_history)}
   ```
6. **Testes (`test_metrics.py`):**
   - `compute_metrics` de engine vazio retorna zeros (sem ZeroDivisionError).
   - Após forçar uma morte (energia 0 + steps), `deaths_total` incrementa.
   - Após reprodução forçada (cenário dos testes de reprodução existentes), `births_total` incrementa.
   - Rodar `step()` por 3 s simulados → `len(metrics_history) == 3` e amostras com `time` crescente.
   - `get_state()["metrics"]` presente e JSON-serializável (`json.dumps`).
7. **`Sparkline.jsx`:** componente SVG puro: props `data` (array de números), `width` (default 210), `height` (default 36), `color` (default `HUD.accent`). Desenha `<polyline>` normalizada ao min/max da janela (escala relativa ao máximo observado); com `data.length < 2` renderiza a trilha vazia. Fundo `HUD.track` como linha de base.
8. **`MetricsPanel.jsx`:** recebe `metrics` (agregados correntes) e `series` (array de amostras). Layout no padrão dos painéis atuais (fonte mono, `HUD.textDim` para labels):
   - Linha de números: População, Comida, Oásis.
   - Distribuição por fase: 4 chips `EGG/JUV/ADU/ELD` com contagens.
   - Sparklines com valor corrente ao lado: "População", "Energia média", "Nascimentos" (`births_total`), "Mortes" (`deaths_total`).
   - Sem dados (`metrics == null`): hint como o InspectorPanel faz.
9. **`SimulationCanvas.jsx`:**
   - `const [metrics, setMetrics] = useState(null)` e `const metricsSeriesRef = useRef([])` + `const [metricsSeries, setMetricsSeries] = useState([])`.
   - No mount (junto da abertura do WS): `fetch('http://localhost:8001/metrics/history')` → semear `metricsSeriesRef.current` com `data.history` (ignorar erro de rede silenciosamente).
   - No `inspectInterval` (150 ms) existente: ler `latestWorldState.current.metrics`; `setMetrics(m)`; se `Math.floor(m.time)` > último `Math.floor(time)` da série, apendar amostra e capar em 600 (`shift`), então `setMetricsSeries([...ref])`.
   - Passar `metrics` e `metricsSeries` ao `ControlMenu`.
10. **`ControlMenu.jsx`:** nova seção `MÉTRICAS` entre INSPETOR e PARÂMETROS, renderizando `<MetricsPanel metrics={metrics} series={metricsSeries} />`.
11. **`docs/arquitetura.md`:** adicionar campo `metrics` ao payload documentado e o endpoint `GET /metrics/history`.

## Contratos técnicos

### Backend (Simulação)
- `compute_metrics(engine) -> dict` (metrics.py) — formato acima.
- `SimulationEngine`: atributos novos `births_total: int`, `deaths_total: int`, `metrics_history: deque[dict]`, `_metrics_accumulator: float`.
- Constantes: `METRICS_SAMPLE_INTERVAL = 1.0`, `METRICS_HISTORY_MAX = 600`.

### API/WebSocket
- `state_update` ganha campo top-level `"metrics"`:
  ```json
  "metrics": {"time": 123.4, "population": 14, "stage_counts": {"EGG": 2, "JUVENILE": 3, "ADULT": 8, "ELDER": 1}, "avg_energy": 61.2, "avg_age": 40.7, "births_total": 12, "deaths_total": 8, "food_count": 87, "oases_count": 3}
  ```
- `GET /metrics/history` → `{"history": [<amostras no mesmo formato>]}` (até 600 itens, ordem cronológica).

### Frontend
- `MetricsPanel({ metrics, series })`, `Sparkline({ data, width, height, color })`.
- Consome `metrics` do `state_update` e semeia a série via `GET /metrics/history`.

## Critérios de aceite

- [ ] `state_update` inclui `metrics` com todos os campos do contrato; cliente antigo não quebra (campo aditivo).
- [ ] `births_total`/`deaths_total` incrementam quando há reprodução/morte (testes cobrem os dois).
- [ ] `metrics_history` acumula 1 amostra por segundo simulado, com cap de 600.
- [ ] `GET /metrics/history` responde 200 com a lista de amostras.
- [ ] HUD mostra a seção Métricas com números correntes, chips por fase e 4 sparklines que evoluem com a simulação.
- [ ] Painel some/mostra hint quando não há dados (antes da conexão).
- [ ] `python -c "import main"` ok e `pytest backend/tests/` verde (157 + novos).

## Rollback

Reverter os commits da branch BIT-26: deletar `metrics.py`, `test_metrics.py`, `MetricsPanel.jsx`, `Sparkline.jsx`; restaurar `engine.py`, `main.py`, `SimulationCanvas.jsx`, `ControlMenu.jsx`, `docs/arquitetura.md`.
