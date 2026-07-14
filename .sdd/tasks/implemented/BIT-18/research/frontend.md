# Research — Frontend (frontend/src/) — BIT-18

> Investigação feita diretamente pelo orquestrador (leitura de código), sem sub-agente.

## Arquivos relevantes

- `frontend/src/components/SimulationCanvas.jsx` — único componente de renderização (canvas 2D + WebSocket)
- `frontend/src/tests/App.test.jsx` — único teste de frontend existente

## Conteúdo relevante para a demanda

- O componente conecta em `ws://localhost:8001/ws`, guarda o último `state_update` em
  `latestWorldState.current` e desenha num `requestAnimationFrame` loop.
- Ordem de desenho atual dentro do `renderLoop` (após `translate`/`scale` do mundo):
  1. Fundo (`images.current.fundo`, sprite `fundo.png` esticado no mundo inteiro)
  2. Criaturas (`data.creatures.forEach`) — cone de visão translúcido + sprite tintado
  3. Comida (`data.foods.forEach`) — sprite `food.png` ou círculo amarelo fallback
- **Não há nenhuma menção a `oases`** em `frontend/src` — o campo já chega no payload
  (`get_state()["oases"]` desde a BIT-06) e é simplesmente ignorado.
- O contexto já está escalado para coordenadas do mundo quando os objetos são desenhados,
  então o oásis pode ser desenhado direto com `x`, `y`, `radius` do payload.

## O que precisa ser feito

- Inserir um bloco `data.oases.forEach(...)` **entre o fundo e as criaturas** (zona de fertilidade
  fica atrás de tudo que é vivo/comestível).
- Desenho: `createRadialGradient(x, y, 0, x, y, radius)` — centro verde translúcido, borda
  transparente; opacidade proporcional a `ttl_fraction` (fade-out conforme o oásis expira).
- Payload atual do oásis: `{"x", "y", "radius", "ttl"}`. O backend passará a enviar também
  `ttl_fraction` (campo aditivo); o frontend usa fallback `?? 1` para retrocompatibilidade.

## Perguntas em aberto

Nenhuma.
