# Pesquisa: Renderização de criaturas no canvas (BIT-10)

## Arquivos relevantes

- `frontend\src\components\SimulationCanvas.jsx` — único componente que desenha no canvas; contém toda a lógica de render (fundo, criaturas, comida) e a conexão WebSocket.
- `frontend\src\App.jsx` — apenas renderiza `<SimulationCanvas />`, sem lógica própria.
- `frontend\public\sprites\bibity.png`, `egg.png`, `food.png`, `fundo.png` — sprites usados no canvas (não há sprite variando por life_stage/energia, só EGG vs. resto).
- `frontend\src\tests\App.test.jsx` — teste placebo (`expect(true).toBe(true)`), não cobre o canvas nem o parsing do payload.
- `backend\main.py` — endpoint WebSocket `/ws` e loop de simulação (30 FPS) que faz `broadcast(engine.get_state())`.
- `backend\simulation\engine.py` — monta o payload `get_state()` que vira o JSON do WebSocket; define `MIN_ENERGY_TO_MATE = 50.0`.
- `backend\simulation\creature.py` — define `Creature`, `LifeStage` (enum), regras de idade/estágio e o método `to_dict()` (payload por criatura).
- `backend\simulation\oasis.py` — `to_dict()` de oásis (x, y, radius, ttl) — chega no payload mas **não é desenhado** no frontend atualmente (dead data no canvas).

## Conteúdo relevante para a demanda

### Fluxo de dados

`backend/main.py` roda `simulation_loop()` a 30 FPS: `engine.step(dt)` → `state = engine.get_state()` → `state["type"] = "state_update"` → `manager.broadcast(state)` (JSON via `websocket.send_text`).

O frontend abre `new WebSocket('ws://localhost:8001/ws')` em `SimulationCanvas.jsx` e em `onmessage` faz `JSON.parse` guardando o resultado inteiro em `latestWorldState.current` (um ref, não state React — o desenho é feito via `requestAnimationFrame`, dissociado do fluxo de mensagens).

### Payload atual de cada criatura (`Creature.to_dict()`)

```python
def to_dict(self):
    return {
        "x": self.body.position.x,
        "y": self.body.position.y,
        "rotation": self.body.angle,
        "radius": self.size,
        "color": "#00ff00" if self.diet == "herbivore" else "#ff0000",
        "energy": self.energy,
        "diet": self.diet,
        "life_stage": self.life_stage.name,   # "EGG" | "JUVENILE" | "ADULT" | "ELDER"
        "vision": self.vision
    }
```

Observações:
- `color` hoje só varia por diet (verde herbívoro / vermelho carnívoro).
- `radius` vem de `self.size`, constante (`10.0`), nunca muda ao longo da vida.
- `age` (usada internamente para transição de estágio) **não é enviada** no payload.
- `max_energy` (100.0 fixo) e `mate_cooldown` **não são enviados**.
- `MIN_ENERGY_TO_MATE = 50.0` existe em `engine.py` (usado para elegibilidade de reprodução).

### Função que desenha cada criatura no canvas (`SimulationCanvas.jsx`, linhas ~90-121)

```jsx
if (data.creatures) {
  data.creatures.forEach(creature => {
    if (images.current.bibity && images.current.bibity.complete && images.current.egg && images.current.egg.complete) {
      const img = creature.life_stage === 'EGG' ? images.current.egg : images.current.bibity;
      ctx.save();
      ctx.translate(creature.x, creature.y);
      ctx.rotate(creature.rotation || 0);
      const s = (creature.radius || 10) * 2;
      ctx.drawImage(img, -s/2, -s/2, s, s);
      ctx.restore();
    } else {
      ctx.fillStyle = creature.color || '#4CAF50';
      ctx.beginPath();
      ctx.arc(creature.x, creature.y, creature.radius || 5, 0, Math.PI * 2);
      ctx.fill();
      // + linha de direção com strokeStyle branco
    }
  });
}
```

Ponto crítico: existem **dois caminhos de render**. O caminho "sprite" (normal em produção, pois as imagens carregam rápido) usa `drawImage` puro e **ignora `creature.color` totalmente** — hoje a cor do payload não tem efeito visual nenhum na prática. O caminho "fallback" (círculo colorido) só roda antes do load das imagens.

`radius`/tamanho: `s = (creature.radius || 10) * 2`. Como `radius` nunca muda no backend, todas as criaturas (exceto ovo, que usa outro sprite mas mesmo `s`) têm o mesmo tamanho visual a vida toda.

Não há interpolação/easing de cor ou tamanho no frontend — redesenho discreto a cada frame com o valor cru do JSON.

Oásis chegam no payload mas não são desenhados (dado morto, fora de escopo desta demanda).

## O que precisa ser feito

**Backend (`creature.py`):**
1. Calcular cor (hex) e escala de tamanho por criatura a partir de `age`/`energy`/`life_stage`, expor no `to_dict()` via `color` (repurposed) e `radius` (escalado).
2. Como o `color` por diet nunca foi visível de fato (dead code no caminho sprite), repurposar esse campo para o gradiente de vida é seguro — não há regressão visual real.
3. Definir constantes de cor (blue → green → gray → black) e função de interpolação.

**Frontend (`SimulationCanvas.jsx`):**
1. Usuário optou por **tingir o sprite inteiro** (não halo/aura) — implementar tint via canvas offscreen (`source-atop` + fillRect com a cor, alpha parcial para preservar detalhe do sprite).
2. Aplicar isso tanto para `bibity.png` quanto `egg.png`.
3. Tamanho: `s` já deriva de `creature.radius`, que passará a variar — não precisa de lógica adicional no frontend além de já usar o valor recebido.

## Perguntas em aberto (resolvidas no refiner)

- "Pronto para reproduzir" e "prestes a morrer" não são `LifeStage` formais — resolvido no refiner como estados de cor contínuos (interpolação), não exigem novo enum.
- Não há teto de morte por idade (só energia <= 0) — resolvido: usar `energy/max_energy` para dirigir a transição cinza→preto dentro do estágio ELDER.
- Tamanho é puramente cosmético (`self.size` usado em `to_dict` já é dissociado do raio de colisão físico fixo em `pymunk.Circle(self.body, 10.0)`) — decisão: manter `self.size` intocado (usado em cálculo de custo de motor) e aplicar a escala só no campo `radius` enviado, para não alterar o balanceamento de energia/custo existente.
