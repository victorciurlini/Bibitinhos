# Spec — BIT-41: Otimizações de Rendering Canvas

**Linear:** N/A
**Risco:** low
**Camada(s):** Frontend
**Depende de:** BIT-40 (introduz `drawTadpole`, que recebe o parâmetro `now`)

---

## Demanda

Três gargalos de rendering foram identificados em `SimulationCanvas.jsx` que aumentam o custo de CPU/GPU por frame sem benefício visual:

1. O gradiente de fundo do mundo (`createLinearGradient`) é recriado a cada frame, mas suas dimensões e cores nunca mudam enquanto o canvas não é redimensionado.
2. O cone de visão de cada criatura é desenhado com 9 chamadas `arc` + `fill` separadas, todas com a **mesma cor e opacidade** — os valores individuais de `creature.vision` não são utilizados no render. O efeito visual é idêntico a um único arco que cobre todo o campo de visão.
3. `Date.now()` é chamado dentro de `drawTadpole()` uma vez por criatura por frame. Com N criaturas, isso gera N chamadas de relógio; criaturas processadas em microssegundos diferentes ficam com fases de oscilação ligeiramente distintas dentro do mesmo frame.

---

## Abordagem técnica

Todas as alterações são em `frontend/src/components/SimulationCanvas.jsx`. Sem mudanças de protocolo WebSocket, sem mudanças de backend.

- **Gradiente cacheado:** `worldGradientRef` guarda o objeto `CanvasGradient` entre frames. Recriar apenas quando `canvas.width` ou `canvas.height` mudar (detectado comparando com `worldGradientSizeRef`).
- **Cone colapsado:** substituir o `for` de 9 arcos por um único `arc` de `fovStart` até `fovStart + visionFovRadians`. O resultado visual é idêntico porque todos os setores têm o mesmo `fillStyle`.
- **`Date.now()` único:** extrair `const now = Date.now()` antes do `forEach` de criaturas e passar como terceiro parâmetro para `drawTadpole(ctx, creature, now)`.

---

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `frontend/src/components/SimulationCanvas.jsx` | modificar | Cache de gradiente, cone colapsado, `now` centralizado |

---

## Passos de implementação

### Passo 1 — Cache do gradiente de fundo do mundo

Declarar dois refs adicionais logo onde os outros `useRef` são criados (linha ~40):

```javascript
const worldGradientRef    = useRef(null);
const worldGradientSizeRef = useRef({ w: 0, h: 0 });
```

Substituir o bloco de criação do `worldGradient` (atualmente linhas 184-188) por:

```javascript
// Recria o gradiente de fundo apenas quando o canvas foi redimensionado
const canvW = canvas.width;
const canvH = canvas.height;
const wgs   = worldGradientSizeRef.current;
if (!worldGradientRef.current || wgs.w !== canvW || wgs.h !== canvH) {
  const g = ctx.createLinearGradient(0, 0, 0, worldHeight);
  g.addColorStop(0, '#1a5079');
  g.addColorStop(1, '#0d2c44');
  worldGradientRef.current = g;
  worldGradientSizeRef.current = { w: canvW, h: canvH };
}
ctx.fillStyle = worldGradientRef.current;
ctx.fillRect(0, 0, worldWidth, worldHeight);
```

> **Por que comparar pelo tamanho do canvas e não pelo do mundo?** O gradiente é criado no sistema de coordenadas *after* `ctx.scale(scale, scale)`, portanto as dimensões relevantes para invalidar o cache são as do canvas físico, não as do mundo simulado.

---

### Passo 2 — Cone de visão: 9 arcos → 1 arco

Substituir o `for` de setores (atualmente linhas 222-230) por um único path:

```javascript
// ANTES (remover):
ctx.fillStyle = 'rgba(144, 238, 144, 0.5)';
for (let i = 0; i < sectorCount; i++) {
  const startAngle = fovStart + i * sectorWidth;
  const endAngle   = startAngle + sectorWidth;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.arc(0, 0, visionRadius, startAngle, endAngle);
  ctx.closePath();
  ctx.fill();
}

// DEPOIS (inserir):
ctx.fillStyle = 'rgba(144, 238, 144, 0.5)';
ctx.beginPath();
ctx.moveTo(0, 0);
ctx.arc(0, 0, visionRadius, fovStart, fovStart + visionFovRadians);
ctx.closePath();
ctx.fill();
```

As variáveis `sectorCount` e `sectorWidth` passam a ser desnecessárias — removê-las do bloco. A variável `fovStart` e o check `if (creature.vision && creature.vision.length > 0)` permanecem iguais (o cone só é desenhado quando a criatura tem dados de visão).

> **Nota de design:** os valores numéricos de `creature.vision[i]` (intensidade por setor) existem no payload mas não são utilizados no render atualmente. Se no futuro for desejado mostrar gradiente de intensidade por setor, o loop de arcos deve ser reintroduzido com `fillStyle` variável. Essa é uma decisão conscientemente adiada — a spec BIT-12 que criou o cone nunca implementou a variação por setor.

---

### Passo 3 — `Date.now()` capturado uma vez por frame

**3a.** No `renderLoop`, antes do `data.creatures.forEach(...)`, adicionar:

```javascript
const now = Date.now();
```

**3b.** Na chamada de `drawTadpole` dentro do `forEach`, passar `now` como terceiro argumento:

```javascript
drawTadpole(ctx, creature, now);
```

**3c.** Na assinatura de `drawTadpole` (introduzida pelo BIT-40), substituir `Date.now()` interno pelo parâmetro:

```javascript
// ANTES:
const drawTadpole = (ctx, creature) => {
  // ...
  const oscY = isMoving
    ? Math.sin((Date.now() / 1000) * TADPOLE.OSC_FREQ * Math.PI * 2) * (r * TADPOLE.OSC_AMP)
    : 0;

// DEPOIS:
const drawTadpole = (ctx, creature, now) => {
  // ...
  const oscY = isMoving
    ? Math.sin((now / 1000) * TADPOLE.OSC_FREQ * Math.PI * 2) * (r * TADPOLE.OSC_AMP)
    : 0;
```

---

## Contratos técnicos

### Frontend

**`drawTadpole(ctx, creature, now)`** — assinatura estendida em relação ao BIT-40:
- `now: number` — valor de `Date.now()` capturado uma única vez pelo `renderLoop` antes do `forEach`

Nenhuma outra interface muda.

### Backend / WebSocket

Nenhuma mudança. Esta spec não toca contratos de dados.

---

## Critérios de aceite

- [ ] O gradiente aquático de fundo aparece visualmente igual ao atual
- [ ] O gradiente não é recriado a cada frame (verificável com `console.count` temporário no bloco de criação)
- [ ] O cone de visão verde aparece visualmente igual ao atual (mesmo ângulo, mesma cor, mesma opacidade)
- [ ] Todas as criaturas no mesmo frame têm a mesma fase de oscilação da cauda (sem "descasamento" entre a primeira e a última criatura do `forEach`)
- [ ] Testes de backend passam sem regressão (`pytest backend/tests/`) — nenhum teste de frontend existe
- [ ] Inspetor de desempenho do browser (Chrome DevTools → Performance → Rendering) mostra redução de draw calls por frame

---

## Rollback

Todos os rollbacks são no bloco correspondente de `SimulationCanvas.jsx`:

1. **Gradiente:** remover `worldGradientRef`, `worldGradientSizeRef` e restaurar o `ctx.createLinearGradient(...)` direto.
2. **Cone:** restaurar o `for` de 9 arcos (pode-se recuperar do git diff de BIT-12 ou do snapshot da spec atual).
3. **`Date.now()`:** remover parâmetro `now` de `drawTadpole` e restaurar `Date.now()` interno.
