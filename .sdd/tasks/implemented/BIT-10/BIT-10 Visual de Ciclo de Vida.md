# Spec — BIT-10: Visual de Ciclo de Vida

**Linear:** N/A
**Risco:** medium
**Camada(s):** Múltiplas (Backend/Simulação + Frontend)

---

## Demanda

Adicionar um indicador visual do ciclo de vida de cada bibite: a cor do sprite muda de azul (recém-nascido) para verde (maduro, pronto para reproduzir), e depois para cinza e quase-preto conforme se aproxima da morte. O tamanho também varia levemente ao longo da vida (ovo menor, adulto no tamanho cheio, idoso ligeiramente encolhido).

## Abordagem técnica

O backend já calcula `age`, `energy`, `max_energy` e `life_stage` por criatura, mas não expõe uma cor/tamanho derivados desses valores — o campo `color` existente hoje só varia por dieta e nunca é usado visualmente no caminho de renderização principal (o frontend desenha sprites via `drawImage`, que ignora `fillStyle`). A solução calcula, em `Creature.to_dict()`, uma cor hexadecimal e um multiplicador de escala a partir de `age`/`energy` (reaproveitando os mesmos limiares de idade 2/10/30 já usados para `LifeStage`), e o frontend passa a **tingir o sprite** (`bibity.png`/`egg.png`) com essa cor via canvas offscreen (`source-atop` + alpha parcial), em vez de desenhar um círculo sólido — preservando o detalhe do sprite original.

Como não existe teto de morte por idade (a morte só ocorre quando `energy <= 0`), o trecho cinza→quase-preto do gradiente (fase ELDER, idade > 30) é conduzido pela fração de energia restante, não pela idade — isso liga o visual à causa real da morte iminente.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | Constantes de cor/escala, funções `compute_life_color` e `compute_visual_scale`, `to_dict()` atualizado |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | Função `drawTintedSprite` (canvas offscreen reutilizável) e uso no branch de render por sprite |
| `backend/tests/test_creature_life_visuals.py` | criar | Testes unitários de `compute_life_color`/`compute_visual_scale` |

## Passos de implementação

1. **Backend — constantes e funções puras** em `creature.py` (módulo-level, ao lado de `METABOLISM_RATE_BY_STAGE`):

   ```python
   LIFE_COLOR_EGG = (59, 130, 246)          # #3b82f6 azul — recem-nascido
   LIFE_COLOR_MATURE = (34, 197, 94)        # #22c55e verde — maduro/pronto p/ reproduzir
   LIFE_COLOR_ELDER_START = (107, 114, 128) # #6b7280 cinza — inicio da velhice, energia cheia
   LIFE_COLOR_DEATH = (17, 24, 39)          # #111827 quase-preto — energia perto de zero

   VISUAL_SCALE_EGG = 0.7
   VISUAL_SCALE_ADULT = 1.0
   VISUAL_SCALE_ELDER_MIN = 0.85

   def _lerp_rgb(c1, c2, t):
       t = max(0.0, min(1.0, t))
       return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))

   def _rgb_to_hex(rgb):
       return '#{:02x}{:02x}{:02x}'.format(*rgb)

   def compute_life_color(age, energy, max_energy):
       """Azul (0-2) -> verde (2-10, flat 10-30) -> cinza/preto por energia (30+)."""
       if age <= 10:
           t = max(0.0, (age - 2) / 8.0) if age > 2 else 0.0
           rgb = _lerp_rgb(LIFE_COLOR_EGG, LIFE_COLOR_MATURE, t)
       elif age <= 30:
           rgb = LIFE_COLOR_MATURE
       else:
           energy_fraction = max(0.0, min(1.0, energy / max_energy))
           rgb = _lerp_rgb(LIFE_COLOR_DEATH, LIFE_COLOR_ELDER_START, energy_fraction)
       return _rgb_to_hex(rgb)

   def compute_visual_scale(age, energy, max_energy):
       """0.7 (ovo) -> 1.0 (adulto) -> encolhe ate 0.85 conforme energia cai no estagio ELDER."""
       if age <= 2:
           return VISUAL_SCALE_EGG
       elif age <= 10:
           t = (age - 2) / 8.0
           return VISUAL_SCALE_EGG + (VISUAL_SCALE_ADULT - VISUAL_SCALE_EGG) * t
       elif age <= 30:
           return VISUAL_SCALE_ADULT
       else:
           energy_fraction = max(0.0, min(1.0, energy / max_energy))
           return VISUAL_SCALE_ADULT - (VISUAL_SCALE_ADULT - VISUAL_SCALE_ELDER_MIN) * (1.0 - energy_fraction)
   ```

2. **Backend — atualizar `to_dict()`** para usar as novas funções:

   ```python
   def to_dict(self):
       return {
           "x": self.body.position.x,
           "y": self.body.position.y,
           "rotation": self.body.angle,
           "radius": self.size * compute_visual_scale(self.age, self.energy, self.max_energy),
           "color": compute_life_color(self.age, self.energy, self.max_energy),
           "energy": self.energy,
           "diet": self.diet,
           "life_stage": self.life_stage.name,
           "vision": self.vision
       }
   ```

   Importante: **não** alterar `self.size` em si — ele continua fixo e é usado no cálculo de `motor_cost` em `update()`; a escala visual é aplicada só no valor enviado ao frontend, para não alterar o balanceamento de energia existente.

3. **Frontend — helper de tint** em `SimulationCanvas.jsx` (fora do `useEffect` ou como `useRef` + função auxiliar dentro do componente):

   ```jsx
   const tintCanvasRef = useRef(null);
   const OFFSCREEN_TINT_SIZE = 64;
   const TINT_ALPHA = 0.55;

   const drawTintedSprite = (ctx, img, size, color) => {
     if (!tintCanvasRef.current) {
       const c = document.createElement('canvas');
       c.width = OFFSCREEN_TINT_SIZE;
       c.height = OFFSCREEN_TINT_SIZE;
       tintCanvasRef.current = c;
     }
     const off = tintCanvasRef.current;
     const octx = off.getContext('2d');
     octx.clearRect(0, 0, OFFSCREEN_TINT_SIZE, OFFSCREEN_TINT_SIZE);
     octx.drawImage(img, 0, 0, OFFSCREEN_TINT_SIZE, OFFSCREEN_TINT_SIZE);
     octx.globalCompositeOperation = 'source-atop';
     octx.globalAlpha = TINT_ALPHA;
     octx.fillStyle = color;
     octx.fillRect(0, 0, OFFSCREEN_TINT_SIZE, OFFSCREEN_TINT_SIZE);
     octx.globalAlpha = 1;
     octx.globalCompositeOperation = 'source-over';
     ctx.drawImage(off, -size / 2, -size / 2, size, size);
   };
   ```

   O canvas offscreen tem tamanho fixo (64x64) e é reutilizado a cada criatura/frame — `drawImage` sempre escala a origem para o destino, então não é necessário redimensionar o buffer por criatura (evita realocação cara a cada frame).

4. **Frontend — usar `drawTintedSprite` no branch de sprite** (substituindo o `ctx.drawImage(img, ...)` direto):

   ```jsx
   if (images.current.bibity && images.current.bibity.complete && images.current.egg && images.current.egg.complete) {
     const img = creature.life_stage === 'EGG' ? images.current.egg : images.current.bibity;
     ctx.save();
     ctx.translate(creature.x, creature.y);
     ctx.rotate(creature.rotation || 0);
     const s = (creature.radius || 10) * 2;
     drawTintedSprite(ctx, img, s, creature.color || '#4CAF50');
     ctx.restore();
   } else {
     // fallback de circulo colorido inalterado (ja usa creature.color)
     ...
   }
   ```

5. **Testes backend** em `backend/tests/test_creature_life_visuals.py`: cobrir `compute_life_color` e `compute_visual_scale` isoladamente (sem precisar instanciar `Creature`/Pymunk), nos pontos-chave do gradiente (ver Critérios de aceite).

## Contratos técnicos

### Backend (Simulação)

- `compute_life_color(age: float, energy: float, max_energy: float) -> str` — retorna hex `#rrggbb`.
- `compute_visual_scale(age: float, energy: float, max_energy: float) -> float` — retorna multiplicador entre `0.7` e `1.0`.
- `Creature.to_dict()["color"]` passa a ser derivado de `compute_life_color` (antes: fixo por `diet`).
- `Creature.to_dict()["radius"]` passa a ser `self.size * compute_visual_scale(...)` (antes: `self.size` fixo).
- `self.size` e o raio de colisão Pymunk (`pymunk.Circle(self.body, 10.0)`) permanecem **inalterados** — mudança é cosmética, não afeta física nem `motor_cost`.

### API/WebSocket

Nenhuma mudança de formato — o payload de cada criatura continua com os mesmos campos (`x, y, rotation, radius, color, energy, diet, life_stage, vision`); só o **valor** de `color`/`radius` muda de significado (de diet-based para life-cycle-based).

### Frontend

- Nova função `drawTintedSprite(ctx, img, size, color)` em `SimulationCanvas.jsx`.
- Substituição do `ctx.drawImage` direto no branch de sprite por essa função tintada.
- Branch de fallback (círculo, sem sprite carregado) permanece sem alteração — já usa `creature.color`.

## Critérios de aceite

- [ ] `compute_life_color(age=0, energy=100, max_energy=100)` retorna `#3b82f6` (azul puro)
- [ ] `compute_life_color(age=10, energy=100, max_energy=100)` retorna `#22c55e` (verde puro), e o mesmo para qualquer idade entre 10 e 30
- [ ] `compute_life_color(age=31, energy=100, max_energy=100)` retorna `#6b7280` (cinza — início ELDER, energia cheia)
- [ ] `compute_life_color(age=31, energy=0, max_energy=100)` retorna `#111827` (quase-preto — energia zerada)
- [ ] `compute_visual_scale(age=0, ...)` retorna `0.7`; `compute_visual_scale(age=10, ...)` retorna `1.0`; `compute_visual_scale(age=31, energy=0, max_energy=100)` retorna `0.85`
- [ ] `pytest backend/tests` passa sem regressões
- [ ] Rodando a simulação (`/run` ou manual), o sprite da criatura visualmente muda de tom conforme a idade avança (verificação manual no navegador — acompanhar uma criatura do nascimento até fase ELDER)
- [ ] Nenhuma mudança perceptível de comportamento físico (colisão/movimento) das criaturas

## Rollback

Reverter `backend/simulation/creature.py` e `frontend/src/components/SimulationCanvas.jsx` para o estado anterior (git); remover `backend/tests/test_creature_life_visuals.py`.
