# Research — frontend (BIT-26: Painéis de métricas populacionais)

> Relatório do sub-agente Explore sobre `frontend/src/` para a demanda de métricas populacionais.

## Visão geral
- React 18.3.1 + Vite 5.4.10 (porta 5173); backend FastAPI WebSocket (porta 8001, 30 FPS)
- Dependências: apenas `react` e `react-dom`; **nenhuma lib de gráficos instalada**
- devDependencies incluem `vitest ^2.1.0` e eslint

## Arquivos relevantes

| Arquivo | Responsabilidade |
|---------|-----------------|
| `frontend/src/App.jsx` | Raiz — renderiza `SimulationCanvas` |
| `frontend/src/components/SimulationCanvas.jsx` | Componente principal: canvas, WebSocket, refs hot-path, estado espelhado |
| `frontend/src/components/ControlMenu.jsx` | Painel HUD recolhível (top-left) — estrutura-mãe dos sub-painéis Tempo, Inspetor, Parâmetros |
| `frontend/src/components/TimeControls.jsx` | Sub-painel: pausar/velocidades (0.5x–4x) |
| `frontend/src/components/InspectorPanel.jsx` | Sub-painel: criatura selecionada |
| `frontend/src/components/ParamsPanel.jsx` | Sub-painel: 22 parâmetros em tempo real (grupos colapsáveis) |
| `frontend/src/components/hudTheme.js` | Tokens CSS-in-JS: paleta bioluminescente |
| `frontend/src/components/hud.css` | Pseudo-elementos (sliders, scrollbar) + animações |

## Fluxo de estado

**Refs "hot path"** (`SimulationCanvas.jsx:11–22`, não causam re-render):
```javascript
const latestWorldState = useRef(null);   // último state_update recebido
const viewTransformRef = useRef({ scale, offsetX, offsetY });
const selectedIdRef = useRef(null);      // creature.id inspecionada
const dragRef = useRef(null);
const wsRef = useRef(null);
```

**Estado "espelho reativo"** (`SimulationCanvas.jsx:25–28`), sincronizado por interval de **150 ms** (`INSPECT_INTERVAL_MS`, linhas 336–345):
```javascript
const [inspectedCreature, setInspectedCreature] = useState(null);
const [paused, setPaused] = useState(false);
const [speed, setSpeed] = useState(1);
const [params, setParams] = useState(null);
```
O interval lê `latestWorldState.current` e faz `setPaused/setSpeed/setParams/setInspectedCreature`.

## Layout atual do HUD

`ControlMenu.jsx:39–52` — painel absoluto `top: 12, left: 12, width: 244px`, `maxHeight: calc(100% - 24px)`, `overflowY: auto`, `zIndex: 10`. Seções internas: TEMPO → INSPETOR → PARÂMETROS. Status badge de conexão no top-right (`SimulationCanvas.jsx:363–390`).

## Tokens de estilo (hudTheme.js)

| Token | Valor | Uso |
|-------|-------|-----|
| `HUD.accent` | `#46e5b0` | bordas ativas, texto importante, glow |
| `HUD.warm` | `#f5a15a` | sinais negativos / energia baixa |
| `HUD.text` | `#e6f4ef` | texto principal |
| `HUD.textDim` | `rgba(230,244,239,0.55)` | labels |
| `HUD.track` | `rgba(230,244,239,0.14)` | trilha de sliders/barras |
| `HUD.panelBg` | `rgba(9,26,30,0.74)` | vidro do painel |
| `HUD.panelBorder` | `1px solid rgba(70,229,176,0.16)` | borda |
| `HUD.accentGlow` | `0 0 8px rgba(70,229,176,0.55)` | box-shadow ativo |

Classes reutilizáveis em `hud.css`: `.hud-btn`, `.hud-toggle`, `.hud-icon-btn`, `.hud-time-btn`, `.hud-group` (cabeçalho colapsável), `.hud-reset`, `.hud-range`, `.hud-scroll`, `.hud-panel-in` (animação de entrada 140ms).

## O que precisa ser feito

1. **Componente `MetricsPanel.jsx`**: recebe `metrics` (agregados + série temporal) e renderiza gráficos em sub-seções colapsáveis (padrão do `ParamsPanel`): população, energia, nascimentos/mortes
2. **Contrato WebSocket**: backend calcula e envia métricas (campo novo no `state_update` ou mensagem separada de menor frequência)
3. **Integração em `SimulationCanvas.jsx`**: `const [metrics, setMetrics] = useState(null)` sincronizado no `inspectInterval` existente; passar ao `ControlMenu`
4. **Nova seção no `ControlMenu.jsx`** com `SectionLabel` "Métricas"
5. **Lib de gráficos**: nada instalado. Candidatas: Recharts (SVG, React-friendly), Victory, Chart.js. **Recomendação do agente: Recharts** — mas dado o hot-path de 30 FPS e o estilo custom do HUD, canvas/SVG manual também é viável (as barras do InspectorPanel já são divs estilizadas)
6. **Série temporal**: buffer circular (no backend ou no frontend) — ex: últimos N pontos com `{time, population, energy_avg, births, deaths}`

## Perguntas em aberto
- Intervalo de agregação da série (a cada tick? 1 s?)
- Quantos pontos históricos manter?
- Quais métricas exatamente no painel?
- Escala dos gráficos fixa ou relativa ao máximo observado?
- Tipo de gráfico (linha, área, barras)?
