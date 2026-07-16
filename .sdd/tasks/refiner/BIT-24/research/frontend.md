# Research — BIT-22 / frontend

## Arquivos relevantes

- `frontend/src/components/SimulationCanvas.jsx` (243 linhas — lido integralmente)
- `frontend/src/App.jsx` — renderiza só `<SimulationCanvas />`, sem layout adicional

## Conteúdo relevante para a demanda

### Transformação de coordenadas (essencial para clique/arrasto)
O render usa:
```js
const scale = Math.min(canvas.width / worldWidth, canvas.height / worldHeight);
const offsetX = (canvas.width - worldWidth * scale) / 2;
const offsetY = (canvas.height - worldHeight * scale) / 2;
ctx.translate(offsetX, offsetY); ctx.scale(scale, scale);
```
`scale`/`offsetX`/`offsetY` são **recalculados dentro do renderLoop** e não ficam acessíveis
fora dele. A inversa (tela→mundo) é:
```js
worldX = (mouseX - offsetX) / scale;   worldY = (mouseY - offsetY) / scale;
```
com `mouseX/Y = e.clientX/Y - canvas.getBoundingClientRect().left/top`.
→ Guardar a transform corrente num ref (`viewTransformRef`) a cada frame.

### Estado e ciclo de render
- Último state do WS fica em `latestWorldState.current` (ref, sem re-render React);
  o canvas desenha via `requestAnimationFrame`. **Padrão a preservar**: o painel de inspeção
  não deve fazer `setState` a 30 FPS — usar um `setInterval` de ~150ms que copia os dados da
  criatura selecionada do ref para um estado React (re-render barato só do painel).
- O socket `ws` vive dentro do `useEffect`; para enviar comandos, guardar em `wsRef` e expor
  helpers (`sendCommand(obj)` com guard de `readyState === OPEN`).
- Não há **nenhum** listener de mouse no canvas hoje. Não há nenhum componente de UI
  além do badge de status de conexão.

### Dados disponíveis por criatura (após mudanças do backend)
`id, x, y, rotation, radius, color, energy, max_energy, age, diet, life_stage, vision[9],
reproduction_cooldown, motor_forward, motor_torque, action_mate, action_grab_drop`
+ `paused`/`speed` no topo do state.

## O que precisa ser feito

1. **Refs de interação**: `wsRef`, `viewTransformRef`, `selectedIdRef`, `dragRef`
   (`{creatureId, moved}` durante um gesto).
2. **Hit-test local** no `mousedown`: converter para mundo, achar criatura mais próxima com
   `dist <= radius + 6` (slop de ~6px-mundo). Achou → candidato a clique E a drag.
3. **Clique vs drag**: threshold de 5px de tela; abaixo = clique (seleciona/deseleciona),
   acima = drag (envia `drag start/move/end`, move ~30 msg/s no `mousemove` — já é a taxa
   natural do evento; sem necessidade de throttle agressivo).
4. **Highlight de seleção**: anel branco pulsante (ou fixo) em volta da criatura selecionada,
   desenhado no renderLoop procurando `id === selectedIdRef.current` no state corrente.
   Se o id sumir do state (morreu), limpar seleção.
5. **`InspectorPanel`** (novo componente): overlay à direita; mostra id, fase, idade,
   barra de energia (energy/max_energy), cooldown, dieta, mini-visualização dos 9 setores de
   visão (barras coloridas por sinal +/−) e outputs do cérebro (motor, torque, mate, grab).
6. **`TimeControls`** (novo componente): overlay inferior central; botões ⏸/▶ e velocidades
   0.5x / 1x / 2x / 4x; destaca o ativo com base em `paused`/`speed` ecoados no state.
7. Cursor: `grab` ao passar sobre criatura, `grabbing` durante drag (opcional, barato via
   hit-test no `mousemove` quando não arrastando — ok pular se custoso).

## Perguntas em aberto

- Nenhuma bloqueante. (Decidido: painel como overlay sobre o canvas — mantém `App.jsx`
  intocado exceto se optar por compor lá; estilo inline seguindo o padrão existente.)
