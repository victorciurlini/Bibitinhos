# Research: Frontend — Renderização de Criaturas

## Arquivos relevantes
- `frontend/src/components/SimulationCanvas.jsx` — componente principal de renderização

## Renderização atual das criaturas (linhas 234-276)

### Path 1: com sprite bibity.png
```jsx
if (images.current.bibity && images.current.bibity.complete) {
  const img = creature.life_stage === 'EGG' ? images.current.egg : images.current.bibity;
  ctx.save();
  ctx.translate(creature.x, creature.y);
  ctx.rotate(creature.rotation || 0);
  const s = (creature.radius || 10) * 2;
  drawTintedSprite(ctx, img, s, creature.color || '#4CAF50');
  ctx.restore();
}
```

`drawTintedSprite` (linhas 68-86): cria canvas offscreen 64x64, aplica `source-atop` com `creature.color`.

### Path 2: fallback círculo (sem sprite)
```jsx
ctx.fillStyle = creature.color || '#4CAF50';
ctx.beginPath();
ctx.arc(creature.x, creature.y, creature.radius || 5, 0, Math.PI * 2);
ctx.fill();
// + linha de direção branca se rotation !== undefined
```

## Dados disponíveis por criatura no frontend
- `x`, `y` — posição
- `rotation` — ângulo Pymunk em radianos (direção que está olhando)
- `radius` — tamanho visual (`size * compute_visual_scale(...)`)
- `color` — hex string calculado por `compute_life_color(...)`
- `life_stage` — `EGG | JUVENILE | ADULT | ELDER`
- `motor_forward`, `motor_torque` — outputs da rede neural (usados só no painel)
- `vision` — sensores visuais (não usados no canvas)
- **`speed`** — NÃO enviado ainda (precisa ser adicionado ao backend)

## Loop de animação
- `requestAnimationFrame` → `renderLoop()` no `SimulationCanvas.jsx`
- Não há timestamps locais — apenas renderiza o estado recebido do backend
- Backend envia 30 FPS; RAF dispara a ~60 FPS
- Para animação da cauda: usar `Date.now()` localmente no frontend

## Sistema de coordenadas local (após ctx.rotate)
Após `ctx.translate(x, y)` + `ctx.rotate(rotation)`:
- Eixo X local → frente da criatura (direção de movimento)
- Eixo Y local → perpendicular ao movimento
- Cabeça fica em X positivo, cauda em X negativo

## O que precisa ser feito

### Criar função `drawTadpole(ctx, creature)`:
1. Corpo: elipse com eixo maior no X (`ellipse(0, 0, bodyHalfLen, bodyHalfWid)`)
2. Cabeça: círculo/elipse levemente maior centrada na frente (`(bodyHalfLen * 0.6, 0)`)
3. Cauda: bezier partindo de `(-bodyHalfLen, 0)` até ponta
   - Ponta com oscilação senoidal em Y quando `speed > MOVEMENT_REFERENCE_SPEED`
   - Ponta reta (Y=0) quando parado

### Modificar renderLoop():
- Criaturas não-EGG → `drawTadpole()`
- EGG → sprite de ovo (mantido) ou fallback círculo

### Constantes de proporção:
```javascript
const TADPOLE_BODY_HALF_LENGTH = 0.9;   // * radius
const TADPOLE_BODY_HALF_WIDTH  = 0.55;  // * radius
const TADPOLE_HEAD_RADIUS      = 0.55;  // * radius
const TADPOLE_TAIL_LENGTH      = 2.0;   // * radius
const TADPOLE_TAIL_WIDTH       = 0.25;  // * radius (lineWidth)
const TADPOLE_OSCILLATION_FREQ = 4.0;   // Hz
const TADPOLE_OSCILLATION_AMP  = 0.7;   // * radius
const MOVEMENT_THRESHOLD       = 35.0;  // px/s (= MOVEMENT_REFERENCE_SPEED do backend)
```
