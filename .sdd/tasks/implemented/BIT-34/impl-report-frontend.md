# BIT-34 — Relatório de Implementação: Painel de Bibitinho Separado

## Status
CONCLUÍDO

## Passos executados

1. **Passo 1 — Corrigir canvas render loop (SimulationCanvas.jsx)**
   Removida a linha `selectedIdRef.current = null` do bloco `else` do anel de seleção. O anel simplesmente deixa de ser desenhado quando a criatura não está no state_update, sem limpar a ref — permitindo que o painel direito detecte a morte.

2. **Passo 2 — Adicionar estado persistente (SimulationCanvas.jsx)**
   Adicionados três estados após `inspectedGenome`:
   - `lastInspectedCreature` — último snapshot da criatura (congelado ao morrer)
   - `lastInspectedGenome` — último genoma inspecionado
   - `isInspectedDead` — flag de morte para exibir badge no painel

3. **Passo 3 — Atualizar sync interval (SimulationCanvas.jsx)**
   Substituído o bloco de sincronização da criatura selecionada no setInterval por lógica com três ramos:
   - Criatura viva: atualiza `inspectedCreature`, `lastInspectedCreature`, limpa `isInspectedDead`
   - Criatura morta (id != null mas não no state): acende `isInspectedDead`, preserva `lastInspectedCreature`
   - Sem seleção (id == null): limpa tudo
   O genoma também propaga para `lastInspectedGenome` quando recebido.

4. **Passo 4 — Adicionar handleClosePanel (SimulationCanvas.jsx)**
   Adicionado `useCallback` ao import e criado `handleClosePanel` após `sendCommand`. Zera `selectedIdRef`, `inspectedGenomeRef` e os três estados persistentes.

5. **Passo 5 — Criar CreatureDetailPanel.jsx**
   Novo componente criado usando tokens reais do `hudTheme.js` (`HUD` e `panelStyle` — não existe export `theme`). Exibe `InspectorPanel` wrapped com opacidade/saturação reduzidas quando `isDead=true`. Header com label "Bibitinho", badge "Morto" em vermelho (`HUD.danger`) e botão fechar.

6. **Passo 6 — Adicionar CreatureDetailPanel no JSX (SimulationCanvas.jsx)**
   Adicionado import de `CreatureDetailPanel` e `useCallback`. Adicionado `<CreatureDetailPanel>` como irmão de `<ControlMenu>` no JSX, passando `lastInspectedCreature`, `lastInspectedGenome`, `isInspectedDead`, `onClose`. Removidas props `creature` e `genome` do `<ControlMenu>`.

7. **Passo 7 — Remover InspectorPanel do ControlMenu.jsx**
   Removido import de `InspectorPanel`. Removidas props `creature` e `genome` da assinatura. Removida a seção "Inspetor" (SectionLabel + renderização condicional). Removida constante `HINT_STYLE` que só era usada nessa seção.

## Arquivos modificados

| Arquivo | Tipo | Descrição |
|---|---|---|
| `frontend/src/components/SimulationCanvas.jsx` | modificado | Passos 1–4 e 6: render loop, estados persistentes, sync interval, handleClosePanel, import e JSX do CreatureDetailPanel |
| `frontend/src/components/CreatureDetailPanel.jsx` | criado | Passo 5: novo painel overlay direito |
| `frontend/src/components/ControlMenu.jsx` | modificado | Passo 7: remoção de InspectorPanel e props creature/genome |

## Problemas encontrados

- **Token `theme` inexistente em hudTheme.js**: A spec referencia `theme.glass`, `theme.border`, `theme.label`, mas o arquivo exporta `HUD` e `panelStyle`. Adaptado para usar `HUD.panelBg`, `HUD.panelBorder`, `HUD.accent` e `panelStyle` (spread). Comportamento visual idêntico ao proposto.
- **`HINT_STYLE` no ControlMenu**: A constante ficaria sem uso após remover o InspectorPanel. Removida junto com o bloco.

## Resultado dos gates

```
Backend:
  import main → OK - app importa
  pytest tests/ → 200 passed, 8 warnings in 5.76s

Frontend:
  npm run test → 1 passed (vitest)
  npm run build → built in 1.21s, 42 modules transformed, sem erros
```

## Próximos passos (se BLOQUEADO)
N/A — implementação concluída com sucesso.
