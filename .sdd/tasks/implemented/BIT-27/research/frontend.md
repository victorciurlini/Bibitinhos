# Research — frontend (BIT-27: Inspetor de rede neural)

> Relatório do sub-agente Explore sobre `frontend/src/` para a demanda do inspetor de rede neural.

## Arquivos relevantes

| Arquivo | Responsabilidade |
|---------|-----------------|
| `frontend/src/components/InspectorPanel.jsx` | Painel atual — mostra métricas da criatura (energia, visão, saídas motoras) |
| `frontend/src/components/SimulationCanvas.jsx` | Seleção por clique (linha ~320: define `selectedIdRef`), WebSocket, estado espelhado a 150 ms |
| `frontend/src/components/ControlMenu.jsx` | Estrutura dos painéis HUD (top-left, 244px) |
| `frontend/src/components/hudTheme.js` / `hud.css` | Tokens de estilo bioluminescente e classes reutilizáveis |

## Situação atual

**Seleção de criatura já funciona (BIT-24):** clique no canvas define `selectedIdRef.current`; um interval de 150 ms encontra a criatura no `latestWorldState` e alimenta `inspectedCreature` → `InspectorPanel`.

**Dados disponíveis hoje no frontend** (via `creature.to_dict()` no `state_update`):
- `vision[0..8]` (9 floats), `motor_forward`, `motor_torque`, `action_mate`, `action_grab_drop`
- id, life_stage, age, energy/max_energy, diet, reproduction_cooldown

**Não é transmitido:** topologia do grafo (nós ocultos, conexões), pesos, biases, funções de ativação, ativações intermediárias.

## O que precisa ser feito

1. **Receber o genoma da criatura selecionada**: nova mensagem WebSocket (ex: cliente envia `{"action": "inspect_creature", "creature_id": 42}`; servidor responde `creature_inspection` com o grafo serializado). O genoma é imutável durante a vida da criatura — basta enviar uma vez por seleção.
2. **Componente `NeuralNetworkViewer.jsx`**: renderiza o grafo (nós + arestas):
   - Layout em camadas fixas (16 inputs à esquerda, hidden no meio, 4 outputs à direita) — a topologia NEAT é pequena (Gen 0: 20 nós, 64 conexões), dispensa force-directed
   - Cor da aresta por sinal do peso (acento `#46e5b0` positivo, `#f5a15a` negativo — consistente com o HUD), espessura ∝ |peso|; conexões `enabled: false` tracejadas ou omitidas
   - Labels dos inputs/outputs vêm do contrato fixo do rtneat_wrapper (Visual_Sector_0..8, Energy_Level, ..., Motor_Forward, etc.)
3. **Integrar ao InspectorPanel**: seção colapsável "Rede Neural" (padrão `.hud-group` do ParamsPanel) ou sub-aba
4. **Lib de visualização**: candidatas d3, Cytoscape.js, canvas/SVG puro. Dado o tamanho pequeno do grafo, o layout em camadas trivial e o estilo custom do HUD, **SVG/canvas puro sem dependência é suficiente** (recomendação do agente era Cytoscape, mas o custo de dep não se justifica para ~20-30 nós)

## Perguntas em aberto
- Enviar só topologia + pesos, ou também ativações em tempo real (exigiria capturar estado interno da rede a cada think)?
- Zoom/pan no grafo ou desenho estático dimensionado ao painel (244px)?
- Comparação parent vs child (fora de escopo provável)?
