# Spec — BIT-12: Cones de Visão no Canvas

**Linear:** N/A
**Risco:** low
**Camada(s):** Múltiplas (Backend aditivo + Frontend)

---

## Demanda

O sensor de visão (9 cones ao redor de cada criatura, `compute_vision()` em `sensors.py`) já existe e já alimenta a rede neural desde o BIT-06, mas é invisível — não há nenhuma representação visual no frontend. O developer quer enxergar o leque de visão de cada criatura no canvas, como um cone verde claro com 50% de opacidade, para poder observar e depurar visualmente como as criaturas percebem o ambiente.

## Abordagem técnica

Adicionar `vision_radius` ao payload do `get_state()` (único dado que falta no frontend — posição, rotação e o array `vision` já são transmitidos) e desenhar, no `SimulationCanvas.jsx`, um leque de setores translúcidos por criatura, usando as mesmas transformações (`translate`/`rotate`) já aplicadas ao sprite. Os 9 setores ficam sempre visíveis e uniformes (não diferenciam ativo/inativo) — puramente uma visualização do alcance/formato do sensor, sem nenhuma mudança de comportamento da simulação.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/engine.py` | modificar | `get_state()` passa a incluir `"vision_radius": VISION_RADIUS` |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | Desenhar leque de setores de visão por criatura |

## Passos de implementação

1. **`engine.py`** — importar `VISION_RADIUS` de `simulation.sensors` (junto do import existente de `compute_vision`) e adicionar a chave no dicionário retornado por `get_state()`:
   ```python
   from simulation.sensors import compute_vision, VISION_RADIUS
   ...
   def get_state(self):
       return {
           "time": self.time_elapsed,
           "generation": self.current_generation,
           "width": self.width,
           "height": self.height,
           "vision_radius": VISION_RADIUS,
           "creatures": [c.to_dict() for c in self.creatures],
           "foods": [f.to_dict() for f in self.foods],
           "oases": [o.to_dict() for o in self.oases]
       }
   ```

2. **`SimulationCanvas.jsx`** — dentro do `forEach` que já desenha cada `creature` (antes do bloco que desenha o sprite, para o cone ficar atrás da criatura), adicionar:
   ```jsx
   const visionRadius = data.vision_radius || 200;
   data.creatures.forEach(creature => {
     if (creature.vision && creature.vision.length > 0) {
       const sectorCount = creature.vision.length;
       const sectorWidth = (Math.PI * 2) / sectorCount;
       const rotation = creature.rotation || 0;

       ctx.save();
       ctx.translate(creature.x, creature.y);
       ctx.fillStyle = 'rgba(144, 238, 144, 0.5)'; // verde claro, 50% opacidade
       for (let i = 0; i < sectorCount; i++) {
         const centerAngle = rotation + i * sectorWidth;
         const startAngle = centerAngle - sectorWidth / 2;
         const endAngle = centerAngle + sectorWidth / 2;
         ctx.beginPath();
         ctx.moveTo(0, 0);
         ctx.arc(0, 0, visionRadius, startAngle, endAngle);
         ctx.closePath();
         ctx.fill();
       }
       ctx.restore();
     }

     // ... bloco existente que desenha o sprite/circulo da criatura, inalterado
   });
   ```
   Nota: `ctx.arc` usa o mesmo sistema de ângulos (0 = eixo +x, crescente = sentido horário no canvas por causa do eixo Y invertido) já usado implicitamente por `ctx.rotate(creature.rotation)` no sprite — como o cone usa a mesma `rotation` crua vinda do backend e a mesma convenção de `ctx.arc`, a orientação visual dos cones fica automaticamente consistente com a orientação do sprite (não precisa inverter sinal).

3. Rodar `npm run build` (garante que o JSX compila) e `npm run test` (suíte atual, mesmo sem cobertura de canvas).

4. Validação manual obrigatória (canvas não é unit-testável de forma significativa): subir `manager.py` → Start Tudo → abrir o frontend → confirmar visualmente que cada criatura tem um leque verde claro de 9 fatias ao seu redor, girando junto com a rotação da criatura.

## Contratos técnicos

### API/WebSocket
- `get_state()` payload ganha campo aditivo `"vision_radius": float` (200.0 hoje) no nível raiz, ao lado de `width`/`height`. Não remove nem renomeia nenhum campo existente — mudança estritamente aditiva, sem risco de quebra.

### Frontend
- `SimulationCanvas.jsx`: novo bloco de desenho por criatura, lido de `creature.vision.length` (não hardcoded `9`) e `data.vision_radius` (não hardcoded `200`) — evita duplicar constantes que já existem no backend.

## Critérios de aceite

- [ ] `data.vision_radius` chega no frontend com o valor de `VISION_RADIUS` (200.0).
- [ ] Cada criatura no canvas exibe um leque de setores verde claro (`rgba(144, 238, 144, 0.5)`), cobrindo os 360° ao redor dela, sempre visível (não pisca/não depende de haver algo detectado).
- [ ] O leque gira junto com `creature.rotation` (setor "frontal" sempre alinhado à frente do sprite).
- [ ] `npm run build` e `npm run test` sem erros.
- [ ] Nenhuma regressão visual nos elementos já desenhados (fundo, sprites, comida).

## Rollback

Reverter `SimulationCanvas.jsx` (remover o bloco de desenho dos setores) e `engine.py` (remover `vision_radius` de `get_state()` e o import de `VISION_RADIUS`).
