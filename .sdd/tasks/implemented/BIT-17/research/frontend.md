## Arquivos relevantes

- `frontend/src/components/SimulationCanvas.jsx` — único componente que desenha no `<canvas>`; renderiza fundo, criaturas, comida e cones de visão
- `frontend/public/sprites/fundo.png` — imagem de fundo atual (inspecionada visualmente e via metadados)
- `frontend/src/App.css`, `frontend/src/index.css` — boilerplate do Vite, sem relação com o canvas de simulação (não têm constantes de cor reaproveitáveis)

## Conteúdo relevante para a demanda

**Valores de cor atuais em `SimulationCanvas.jsx`:**
- Linha 43: `images.current.fundo = loadImg('/sprites/fundo.png');`
- Linha 55 (`resizeCanvas`, roda 1x no mount/resize): `ctx.fillStyle = '#1e1e1e'; ctx.fillRect(0, 0, canvas.width, canvas.height);`
- Linha 92 (`renderLoop`, roda todo frame antes de desenhar o mundo): mesmo `#1e1e1e` fill
- Linhas 108-111 (dentro do bloco transformado `ctx.save()/translate/scale`, coordenadas de mundo): `if (images.current.fundo && ...complete) { ctx.drawImage(images.current.fundo, 0, 0, worldWidth, worldHeight); }`
- Linha 221: `<canvas style={{ ..., backgroundColor: '#1e1e1e' }} />` — fallback CSS

**Achado crítico (ordem de desenho):** `fundo.png` foi inspecionado e é **1914×830, RGB puro sem canal alpha — 100% opaco**. Ele é desenhado (linha 110) **depois e por cima** do fill plano da linha 92, dentro da mesma área do mundo (0,0)-(worldWidth,worldHeight). Como é opaco, ele **encobre completamente** qualquer cor definida no `fillStyle` daquela região. Ou seja: hoje, trocar só a cor do fill (linha 92) **não teria nenhum efeito visual** dentro da área do mundo — só mudaria a faixa de letterbox/pillarbox fora do quadrado do mundo (quando a proporção do canvas não é 1:1 com `worldWidth:worldHeight`).

Consequência adicional: hoje não existe nenhum `strokeRect`/contorno desenhado para os limites do mapa (confirmado via busca no arquivo) — a única razão da fronteira do mapa ser hoje visualmente distinguível do letterbox é o contraste acidental entre o branco do `fundo.png` e o `#1e1e1e` do fill externo.

**Padrões reaproveitáveis já existentes:**
- Nenhum `createLinearGradient`/`createRadialGradient` existe no código hoje — seria o primeiro uso, mas é uma API padrão do Canvas 2D, sem necessidade de biblioteca nova.
- Cones de visão (linhas 121-140, BIT-12/13/14) usam fills translúcidos simples (`rgba(144, 238, 144, 0.5)`) desenhados como setores de arco — não é um padrão de gradiente, mas confirma que fills coloridos diretos já são a convenção do arquivo.
- `drawTintedSprite` (linhas 14-32) é o único "efeito" visual mais elaborado (composite op `source-atop` para tingir sprites) — não é reaproveitável aqui pois o objetivo não é tingir um sprite existente, e sim substituir o fundo.
- Render loop roda via `requestAnimationFrame` incondicionalmente todo frame (linhas 87-193), independente de nova mensagem WebSocket ter chegado — logo, recriar um `fillStyle`/gradiente a cada frame (barato: 2 paradas de cor) não tem custo perceptível.
- Não existe arquivo de constantes de cor (`theme.js`/`colors.js`) — todas as cores são strings literais inline no próprio componente; a convenção do projeto é essa (inline), não um módulo de config central.

## O que precisa ser feito

1. Remover a linha 43 (`images.current.fundo = loadImg(...)`) e o bloco `drawImage` das linhas 108-111 — parar de usar `fundo.png` (o arquivo em si fica intocado no disco, sem outro consumidor).
2. No lugar do bloco removido, desenhar um gradiente vertical de 2 paradas em coordenadas de mundo: `ctx.createLinearGradient(0, 0, 0, worldHeight)`, stop 0 = `#1a5079`, stop 1 = `#0d2c44`, seguido de `ctx.fillRect(0, 0, worldWidth, worldHeight)`.
3. Trocar `#1e1e1e` → `#0a1e2e` nas linhas 55, 92 e 221 (fill externo/letterbox + fallback CSS) — mantém o contraste que hoje delimita a fronteira do mapa, só que de forma intencional em vez de acidental.

## Perguntas em aberto

Nenhuma — a escolha "cor/gradiente sólido" (em vez de efeito animado) já foi confirmada explicitamente pelo developer, e a ordem de desenho foi verificada lendo o arquivo linha a linha, não é uma suposição.
