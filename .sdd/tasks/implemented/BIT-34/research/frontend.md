## Arquivos relevantes

- `frontend/src/components/SimulationCanvas.jsx` — componente principal: canvas, WebSocket, todo o estado reativo
- `frontend/src/components/ControlMenu.jsx` — painel esquerdo expansível (contém InspectorPanel, MetricsPanel, TimeControls, ParamsPanel)
- `frontend/src/components/InspectorPanel.jsx` — renderiza dados do bibitinho selecionado
- `frontend/src/components/NeuralNetworkViewer.jsx` — visualização SVG da rede neural (usado dentro do InspectorPanel)
- `frontend/src/components/hudTheme.js` — tokens de design (cores, fonts, spacing)

## Estrutura de layout atual

```
<div> (SimulationCanvas — canvas fill viewport)
  <canvas>                       ← mundo 2D, renderizado via requestAnimationFrame
  <div> (status badge top-right)
  <ControlMenu>                  ← overlay absoluto esquerdo, 244px wide, left:12, top:12, z:10
    ├─ TimeControls
    ├─ InspectorPanel (criatura selecionada OU hint "Clique num bibite")
    ├─ MetricsPanel
    └─ ParamsPanel
```

**Tudo no painel esquerdo — não existe painel à direita.**

## Conteúdo relevante

### Estado em SimulationCanvas.jsx

```javascript
// Estado reativo (re-render)
const [inspectedCreature, setInspectedCreature] = useState(null);
const [inspectedGenome, setInspectedGenome] = useState(null);
const [paused, setPaused] = useState(false);
const [speed, setSpeed] = useState(1);
const [params, setParams] = useState(null);
const [metrics, setMetrics] = useState(null);
const [metricsSeries, setMetricsSeries] = useState([]);

// Refs quentes (não disparam re-render)
const selectedIdRef = useRef(null);       // ID do bibitinho clicado
const inspectedGenomeRef = useRef(null);  // resposta unicast creature_inspection
```

### Ciclo de sincronização (~150ms)

```javascript
const inspectInterval = setInterval(() => {
  const data = latestWorldState.current;
  // ...
  const id = selectedIdRef.current;
  const sel = id != null && data.creatures
    ? data.creatures.find(c => c.id === id)
    : null;
  setInspectedCreature(sel || null);  // ← NULL se morreu → painel fecha
  
  const insp = inspectedGenomeRef.current;
  setInspectedGenome(insp && insp.creature_id === selectedIdRef.current ? insp.genome : null);
}, INSPECT_INTERVAL_MS); // 150ms
```

### Problema 1: Canvas render loop limpa selectedIdRef quando criatura morre

```javascript
// ~linha 248-261 (canvas render loop)
if (selectedIdRef.current != null) {
  const sel = data.creatures.find(c => c.id === selectedIdRef.current);
  if (sel) {
    // draw selection ring
  } else {
    selectedIdRef.current = null;  // ← APAGA O ID, perde contexto de "quem estava selecionado"
  }
}
```

### Problema 2: sync interval limpa o painel

Quando `selectedIdRef.current = null`, o sync interval entra no branch `id == null → sel = null → setInspectedCreature(null)` → painel fecha.

### InspectorPanel.jsx

```javascript
const InspectorPanel = ({ creature, genome }) => {
  if (!creature) return null;  // ← simplesmente desaparece
  // ...renderiza dados
}
```

### ControlMenu.jsx (props atuais)

```javascript
const ControlMenu = ({ paused, speed, creature, genome, params, metrics, metricsSeries, onCommand })
```

Renderiza `<InspectorPanel creature={creature} genome={genome} />` internamente.

## O que precisa ser feito

1. **Remover InspectorPanel do ControlMenu** — ControlMenu deve mostrar apenas TimeControls, MetricsPanel, ParamsPanel

2. **Criar `CreatureDetailPanel.jsx`** — overlay absoluto posicionado à direita (right:12, top:12), z:10, mesmo visual que ControlMenu; mostra InspectorPanel + badge "Morto" quando `isDead`

3. **Adicionar estado persistente em SimulationCanvas.jsx:**
   ```js
   const [lastInspectedCreature, setLastInspectedCreature] = useState(null);
   const [lastInspectedGenome, setLastInspectedGenome] = useState(null);
   const [isInspectedDead, setIsInspectedDead] = useState(false);
   ```

4. **Corrigir canvas render loop** — remover `selectedIdRef.current = null` quando a criatura some; o anel já não é desenhado se `sel` é falsy, sem necessidade de limpar a ref

5. **Atualizar sync interval** com lógica de persistência:
   - `sel` existe → vivo: atualiza `lastInspectedCreature`, `isInspectedDead = false`
   - `id != null && !sel` → morreu: `isInspectedDead = true`, `lastInspectedCreature` congelado
   - `id == null` → deselectionado: limpa tudo

6. **Adicionar `<CreatureDetailPanel>` no JSX de SimulationCanvas** com props `creature={lastInspectedCreature}`, `genome={lastInspectedGenome}`, `isDead={isInspectedDead}`, `onClose={handleClosePanel}`

7. **Adicionar `handleClosePanel`** que limpa `selectedIdRef.current`, `inspectedGenomeRef.current` e todo o estado persistente

## Perguntas em aberto

- Nenhuma. Todas as decisões de design resolvidas pela pesquisa.
