# Spec — BIT-34: Painel de Bibitinho Separado

**Linear:** N/A
**Risco:** low
**Camada(s):** Frontend

---

## Demanda

Atualmente, ao clicar num bibitinho, suas informações aparecem dentro do painel esquerdo (`ControlMenu`), misturadas com as configurações de ambiente (Métricas, Parâmetros, Controles de Tempo). O usuário quer dois painéis independentes:

1. **Painel esquerdo** — configuração do ambiente (permanece como está, sem InspectorPanel)
2. **Painel direito** — informações do bibitinho selecionado (novo, posicionado à direita do canvas)

Além disso, quando o bibitinho morre, o painel direito **não deve fechar**: deve congelar no último estado recebido e exibir um indicador visual de "Morto" para análise post-mortem. O painel só fecha ao clicar em outro bibitinho ou ao clicar no canvas vazio.

---

## Abordagem técnica

Solução 100% no frontend — nenhuma mudança de backend. O estado persistente (`lastInspectedCreature`, `lastInspectedGenome`, `isInspectedDead`) é mantido no `SimulationCanvas`. O sinal de morte é detectado pela ausência da criatura no próximo `state_update` (quando `selectedIdRef.current != null` mas a criatura não está em `data.creatures`). Um novo componente `CreatureDetailPanel` é posicionado como overlay absoluto à direita do canvas, espelhando o estilo visual do `ControlMenu`.

---

## Arquivos a tocar

| Arquivo (path relativo à raiz) | Alteração | Descrição |
|---|---|---|
| `frontend/src/components/SimulationCanvas.jsx` | modificar | Adicionar estado persistente, corrigir canvas render loop, atualizar sync interval, adicionar `<CreatureDetailPanel>` no JSX |
| `frontend/src/components/ControlMenu.jsx` | modificar | Remover props `creature` e `genome`; remover seção InspectorPanel e seu SectionLabel |
| `frontend/src/components/CreatureDetailPanel.jsx` | criar | Novo painel overlay direito: wrap de InspectorPanel + badge morto + botão fechar |

---

## Passos de implementação

### Passo 1 — Corrigir canvas render loop (`SimulationCanvas.jsx`)

Localizar o bloco de desenho do anel de seleção no render loop (dentro do `useEffect` do canvas, na função de draw):

```javascript
// ANTES (~linha 248-261):
if (selectedIdRef.current != null) {
  const sel = data.creatures.find(c => c.id === selectedIdRef.current);
  if (sel) {
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2 / scale;
    ctx.beginPath();
    ctx.arc(sel.x, sel.y, (sel.radius || 10) + 6, 0, Math.PI * 2);
    ctx.stroke();
  } else {
    selectedIdRef.current = null;  // ← REMOVER ESTA LINHA
  }
}
```

Remover apenas a linha `selectedIdRef.current = null`. O anel já não será desenhado se `sel` é falsy — o comportamento visual não muda.

---

### Passo 2 — Adicionar estado persistente (`SimulationCanvas.jsx`)

Após as declarações de estado existentes (próximo a `useState(null)` para `inspectedCreature`), adicionar:

```javascript
const [lastInspectedCreature, setLastInspectedCreature] = useState(null);
const [lastInspectedGenome, setLastInspectedGenome] = useState(null);
const [isInspectedDead, setIsInspectedDead] = useState(false);
```

---

### Passo 3 — Atualizar sync interval (`SimulationCanvas.jsx`)

Substituir o bloco de sincronização da criatura selecionada no `setInterval` (~150ms):

```javascript
// ANTES:
const id = selectedIdRef.current;
const sel = id != null && data.creatures
  ? data.creatures.find(c => c.id === id)
  : null;
setInspectedCreature(sel || null);

const insp = inspectedGenomeRef.current;
setInspectedGenome(insp && insp.creature_id === selectedIdRef.current ? insp.genome : null);
```

```javascript
// DEPOIS:
const id = selectedIdRef.current;
const sel = id != null && data.creatures
  ? data.creatures.find(c => c.id === id)
  : null;

if (sel) {
  // Criatura viva: atualiza painel e backup
  setInspectedCreature(sel);
  setLastInspectedCreature(sel);
  setIsInspectedDead(false);
} else if (id != null) {
  // selectedIdRef aponta pra algo que sumiu da lista → morreu
  setInspectedCreature(null);
  setIsInspectedDead(true);
  // lastInspectedCreature NÃO é atualizado (preserva último estado)
} else {
  // Nada selecionado (clique no vazio ou estado inicial)
  setInspectedCreature(null);
  setIsInspectedDead(false);
  setLastInspectedCreature(null);
  setLastInspectedGenome(null);
}

const insp = inspectedGenomeRef.current;
if (insp && insp.creature_id === id) {
  setInspectedGenome(insp.genome);
  setLastInspectedGenome(insp.genome);
}
```

---

### Passo 4 — Adicionar `handleClosePanel` (`SimulationCanvas.jsx`)

Adicionar um callback (próximo a outros callbacks como `sendCommand`):

```javascript
const handleClosePanel = useCallback(() => {
  selectedIdRef.current = null;
  inspectedGenomeRef.current = null;
  setLastInspectedCreature(null);
  setLastInspectedGenome(null);
  setIsInspectedDead(false);
}, []);
```

---

### Passo 5 — Criar `CreatureDetailPanel.jsx`

Criar o arquivo `frontend/src/components/CreatureDetailPanel.jsx`:

```jsx
import React from 'react';
import InspectorPanel from './InspectorPanel';
import { theme } from './hudTheme';

const PANEL_STYLE = {
  position: 'absolute',
  right: 12,
  top: 12,
  width: 260,
  maxHeight: 'calc(100vh - 24px)',
  overflowY: 'auto',
  background: theme.glass,
  border: `1px solid ${theme.border}`,
  borderRadius: 8,
  zIndex: 10,
  pointerEvents: 'auto',
  display: 'flex',
  flexDirection: 'column',
};

const HEADER_STYLE = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '8px 10px',
  borderBottom: `1px solid ${theme.border}`,
  flexShrink: 0,
};

const LABEL_STYLE = {
  color: theme.label,
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
};

const DEAD_BADGE_STYLE = {
  fontSize: 9,
  fontWeight: 700,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: '#ff6b6b',
  border: '1px solid #ff6b6b',
  borderRadius: 3,
  padding: '1px 5px',
  marginLeft: 6,
};

const CLOSE_BTN_STYLE = {
  background: 'none',
  border: 'none',
  color: theme.label,
  cursor: 'pointer',
  fontSize: 16,
  lineHeight: 1,
  padding: '0 2px',
};

export default function CreatureDetailPanel({ creature, genome, isDead, onClose }) {
  if (!creature) return null;

  return (
    <div style={PANEL_STYLE}>
      <header style={HEADER_STYLE}>
        <span style={LABEL_STYLE}>
          Bibitinho
          {isDead && <span style={DEAD_BADGE_STYLE}>Morto</span>}
        </span>
        <button style={CLOSE_BTN_STYLE} onClick={onClose}>×</button>
      </header>
      <div style={{
        opacity: isDead ? 0.65 : 1,
        filter: isDead ? 'saturate(0.35)' : 'none',
        transition: 'opacity 0.4s, filter 0.4s',
      }}>
        <InspectorPanel creature={creature} genome={genome} />
      </div>
    </div>
  );
}
```

**Nota sobre `theme`:** verificar se `theme.glass` e `theme.border` são as chaves corretas exportadas por `hudTheme.js`. Se o módulo exportar tokens com outros nomes (ex: `T.glass`), ajustar a importação.

---

### Passo 6 — Adicionar `<CreatureDetailPanel>` no JSX de `SimulationCanvas.jsx`

No JSX retornado por `SimulationCanvas`, adicionar o novo componente como irmão do `<ControlMenu>`:

```jsx
import CreatureDetailPanel from './CreatureDetailPanel';

// No return:
<>
  <canvas ref={canvasRef} /* ... */ />
  {/* badge de conexão */}
  <ControlMenu
    paused={paused}
    speed={speed}
    // creature e genome REMOVIDOS
    params={params}
    metrics={metrics}
    metricsSeries={metricsSeries}
    onCommand={sendCommand}
  />
  <CreatureDetailPanel
    creature={lastInspectedCreature}
    genome={lastInspectedGenome}
    isDead={isInspectedDead}
    onClose={handleClosePanel}
  />
</>
```

---

### Passo 7 — Remover InspectorPanel do `ControlMenu.jsx`

Em `ControlMenu.jsx`:

1. Remover `creature` e `genome` da desestruturação de props
2. Remover o import de `InspectorPanel` (se não usado em outro lugar)
3. Remover o bloco:
   ```jsx
   <SectionLabel>Inspetor</SectionLabel>
   {creature
     ? <InspectorPanel creature={creature} genome={genome} />
     : <p style={HINT_STYLE}>Clique num bibite para inspecionar.</p>
   }
   ```
   (nomes exatos podem variar — localizar pelo padrão `creature ?`)

---

## Contratos técnicos

### Frontend

**Novos estados em `SimulationCanvas`:**
```javascript
const [lastInspectedCreature, setLastInspectedCreature] = useState(null); // Creature | null
const [lastInspectedGenome, setLastInspectedGenome] = useState(null);     // Genome | null
const [isInspectedDead, setIsInspectedDead] = useState(false);             // boolean
```

**Props de `CreatureDetailPanel`:**
```typescript
{
  creature: CreatureDTO | null,  // último estado conhecido
  genome: GenomeDTO | null,
  isDead: boolean,               // true quando a criatura sumiu do state_update
  onClose: () => void,           // limpa seleção e estado persistente
}
```

**Props removidas de `ControlMenu`:**
- `creature`
- `genome`

### Backend

Nenhuma mudança. O protocolo WebSocket permanece inalterado.

---

## Critérios de aceite

- [ ] Ao clicar num bibitinho, o painel de detalhes abre à **direita** do canvas (não dentro do ControlMenu esquerdo)
- [ ] O ControlMenu esquerdo não exibe mais dados de bibitinho (seção "Inspetor" removida)
- [ ] Quando o bibitinho morre, o painel direito **permanece aberto** com o último estado capturado
- [ ] Badge vermelho "Morto" aparece no cabeçalho do painel quando o bibitinho morre
- [ ] O conteúdo do painel fica visualmente dessaturado/opaco quando `isDead = true`
- [ ] Clicar em outro bibitinho vivo substitui o painel com as informações do novo bibitinho
- [ ] Clicar no canvas vazio (sem hit em nenhum bibitinho) fecha o painel direito
- [ ] O botão `×` no cabeçalho do painel fecha o painel
- [ ] O anel de seleção branco no canvas desaparece quando o bibitinho morre (comportamento visual preservado)
- [ ] `pytest backend/tests/` continua com todos os testes passando (sem regressão de backend)

---

## Rollback

Mudança é 100% frontend. Para reverter:

1. **`SimulationCanvas.jsx`**: restaurar `selectedIdRef.current = null` no canvas render loop; remover os 3 novos estados e `handleClosePanel`; reverter sync interval para versão anterior; remover `<CreatureDetailPanel>` do JSX; restaurar props `creature` e `genome` no `<ControlMenu>`
2. **`ControlMenu.jsx`**: restaurar props `creature` e `genome`, restaurar bloco InspectorPanel
3. **`CreatureDetailPanel.jsx`**: deletar arquivo
