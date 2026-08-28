# Spec — BIT-40: Visual Girino com Cauda Animada

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação) + Frontend

---

## Demanda

As criaturas são atualmente renderizadas como sprites estáticos (`bibity.png`) coloridos e rotacionados, ou como círculos com linha de direção no fallback. Esse visual não transmite vida ou movimento. O objetivo é redesenhar as criaturas para que se assemelhem a girinos: corpo ovalado com cabeça maior, e uma cauda que oscila senoidalmente quando a criatura está em movimento (speed > threshold) e fica reta quando parada.

Ovos (`life_stage === 'EGG'`) mantêm o sprite atual.

---

## Abordagem técnica

O backend expõe `self.body.velocity.length` (já calculado internamente) adicionando o campo `speed` ao `to_dict()`. O frontend substitui a lógica de sprite/círculo por uma função `drawTadpole()` que desenha proceduralmente, no sistema de coordenadas local da criatura, um corpo elíptico + cabeça + cauda bezier com oscilação calculada com `Date.now()`. Nenhuma mudança de protocolo WebSocket — apenas um novo campo no payload existente.

---

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | Adicionar campo `"speed"` ao `to_dict()` |
| `backend/tests/test_creature_life_visuals.py` | modificar | Adicionar asserção de que `to_dict()` contém `"speed"` com valor float >= 0 |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | Criar `drawTadpole()` e substituir lógica de sprite/círculo para não-EGG |

---

## Passos de implementação

### Passo 1 — Backend: expor `speed` em `to_dict()`

Em `backend/simulation/creature.py`, no método `to_dict()` (atualmente linha 244), adicionar o campo `"speed"` antes do `return`:

```python
def to_dict(self):
    return {
        # ... todos os campos existentes ...
        "children_count": self.children_count,
        "speed": self.body.velocity.length,   # <-- NOVO: magnitude em px/s
    }
```

`self.body.velocity.length` retorna um `float` (Pymunk `Vec2d.length`), sempre >= 0. Não requer import adicional.

---

### Passo 2 — Backend: teste para `speed`

Em `backend/tests/test_creature_life_visuals.py`, adicionar ao final do arquivo:

```python
def test_to_dict_has_speed_field():
    from backend.simulation.engine import SimulationEngine
    from backend.simulation.creature import Creature
    engine = SimulationEngine()
    creature = Creature(engine)
    d = creature.to_dict()
    assert "speed" in d
    assert isinstance(d["speed"], float)
    assert d["speed"] >= 0.0
```

> Criaturas recém-criadas estão paradas (`body.velocity = (0, 0)`), então `speed = 0.0`.

---

### Passo 3 — Frontend: função `drawTadpole`

Em `frontend/src/components/SimulationCanvas.jsx`, **antes da função `renderLoop`** (atualmente linha 159), inserir a função `drawTadpole`:

```javascript
const TADPOLE = {
  BODY_HALF_LEN:   0.90,  // * radius — semieixo maior da elipse do corpo (X)
  BODY_HALF_WID:   0.55,  // * radius — semieixo menor da elipse do corpo (Y)
  HEAD_RADIUS:     0.55,  // * radius — raio do círculo da cabeça
  HEAD_OFFSET_X:   0.75,  // * radius — deslocamento da cabeça para frente (+X)
  TAIL_CTRL_X:    -1.80,  // * radius — X do ponto de controle bezier da cauda
  TAIL_TIP_X:     -2.90,  // * radius — X da ponta da cauda
  TAIL_WIDTH:      0.25,  // * radius — espessura (lineWidth) da cauda
  OSC_FREQ:        4.0,   // Hz — frequência de oscilação da cauda
  OSC_AMP:         0.70,  // * radius — amplitude máxima da oscilação
  MOVE_THRESHOLD:  35.0,  // px/s — abaixo disso, cauda fica reta
};

const drawTadpole = (ctx, creature) => {
  const r = creature.radius || 10;
  const color = creature.color || '#4CAF50';
  const speed = creature.speed || 0;
  const isMoving = speed > TADPOLE.MOVE_THRESHOLD;

  // Oscilação da ponta da cauda em Y (perpendicular ao eixo de movimento)
  const oscY = isMoving
    ? Math.sin((Date.now() / 1000) * TADPOLE.OSC_FREQ * Math.PI * 2) * (r * TADPOLE.OSC_AMP)
    : 0;

  ctx.save();
  ctx.translate(creature.x, creature.y);
  ctx.rotate(creature.rotation || 0);

  // Corpo: elipse ovalada centrada na origem
  // +X = frente (direção de movimento), +Y = perpendicular
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(0, 0, r * TADPOLE.BODY_HALF_LEN, r * TADPOLE.BODY_HALF_WID, 0, 0, Math.PI * 2);
  ctx.fill();

  // Cabeça: círculo centrado ligeiramente à frente do corpo
  ctx.beginPath();
  ctx.arc(r * TADPOLE.HEAD_OFFSET_X, 0, r * TADPOLE.HEAD_RADIUS, 0, Math.PI * 2);
  ctx.fill();

  // Cauda: quadratic bezier partindo da traseira do corpo (-BODY_HALF_LEN, 0)
  // Ponto de controle: (CTRL_X, oscY * 0.5) — segura a curvatura suavemente
  // Ponta: (TIP_X, oscY)
  ctx.strokeStyle = color;
  ctx.lineWidth = Math.max(0.5, r * TADPOLE.TAIL_WIDTH);
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(-r * TADPOLE.BODY_HALF_LEN, 0);
  ctx.quadraticCurveTo(
    r * TADPOLE.TAIL_CTRL_X, oscY * 0.5,  // ponto de controle
    r * TADPOLE.TAIL_TIP_X,  oscY          // ponta da cauda
  );
  ctx.stroke();

  ctx.restore();
};
```

**Por que `quadraticCurveTo`?** Uma bezier quadrática com controle em Y/2 cria uma curva suave e biologicamente plausível, mais simples que a cúbica e suficiente para o efeito.

---

### Passo 4 — Frontend: substituir lógica de sprite no `renderLoop`

No `renderLoop`, localizar o bloco atual de renderização de criatura (linhas 234-261). Substituir **todo o bloco** (tanto o branch com sprite quanto o fallback sem sprite) pela lógica abaixo:

```javascript
// ANTES (linhas 234-261):
if (images.current.bibity && images.current.bibity.complete && ...) {
  const img = creature.life_stage === 'EGG' ? images.current.egg : images.current.bibity;
  // ... drawTintedSprite ...
} else {
  // ... ctx.arc fallback ...
}

// DEPOIS:
if (creature.life_stage === 'EGG') {
  // Ovos mantêm sprite original (ou fallback círculo pequeno)
  if (images.current.egg && images.current.egg.complete) {
    ctx.save();
    ctx.translate(creature.x, creature.y);
    ctx.rotate(creature.rotation || 0);
    const s = (creature.radius || 10) * 2;
    drawTintedSprite(ctx, images.current.egg, s, creature.color || '#4CAF50');
    ctx.restore();
  } else {
    ctx.fillStyle = creature.color || '#4CAF50';
    ctx.beginPath();
    ctx.arc(creature.x, creature.y, creature.radius || 5, 0, Math.PI * 2);
    ctx.fill();
  }
} else {
  // JUVENILE / ADULT / ELDER — girino procedural
  drawTadpole(ctx, creature);
}
```

O anel de seleção (círculo branco quando a criatura está selecionada, linhas 267-276) **não muda** — continua usando `creature.x`, `creature.y` e `creature.radius`.

---

## Contratos técnicos

### Backend (Simulação)

**`Creature.to_dict()`** — novo campo adicionado:
```python
"speed": float  # self.body.velocity.length, sempre >= 0.0, em px/s
```

**Constante de referência (já existe, não alterar):**
```python
MOVEMENT_REFERENCE_SPEED = 35.0  # px/s — mesmo threshold usado no frontend
```

### Frontend

**`drawTadpole(ctx: CanvasRenderingContext2D, creature: object): void`**

Campos consumidos do objeto `creature`:
- `x: float`, `y: float` — posição no espaço de mundo
- `rotation: float` — ângulo em radianos (direção de movimento)
- `radius: float` — raio visual (determina todas as proporções)
- `color: string` — hex color para preenchimento e cauda
- `speed: float` — magnitude da velocidade (nova, do backend)

**Constante de oscilação (local à função):**
```
TADPOLE.MOVE_THRESHOLD = 35.0   // px/s
TADPOLE.OSC_FREQ       = 4.0    // Hz
TADPOLE.OSC_AMP        = 0.70   // * radius
```

### API/WebSocket

Nenhuma mudança de formato de mensagem. O payload `state_update` continua igual — apenas o objeto de cada criatura ganha um campo `speed` (float) extra, que clientes existentes ignoram silenciosamente.

---

## Critérios de aceite

- [ ] `creature.to_dict()` retorna campo `"speed"` com valor `float >= 0`
- [ ] Testes de backend passam sem regressão (`pytest backend/tests/`)
- [ ] No canvas, criaturas JUVENILE/ADULT/ELDER são desenhadas como girinos (corpo ovalado + cabeça + cauda)
- [ ] Cauda oscila visivelmente enquanto a criatura se move (`speed > 35 px/s`)
- [ ] Cauda fica reta quando a criatura está parada (`speed <= 35 px/s`)
- [ ] Ovos (`life_stage === 'EGG'`) continuam com sprite de ovo (ou fallback círculo) — sem girino
- [ ] Anel de seleção (clique na criatura) continua funcionando corretamente
- [ ] Cone de visão (setor verde) continua aparecendo quando ativado

---

## Rollback

Se precisar desfazer:
1. `creature.py` — remover a linha `"speed": self.body.velocity.length` do `to_dict()`
2. `test_creature_life_visuals.py` — remover `test_to_dict_has_speed_field()`
3. `SimulationCanvas.jsx` — remover a `const TADPOLE = {...}` e a função `drawTadpole`, e reverter o bloco de renderização de criatura para o original (sprite ou `ctx.arc`)
