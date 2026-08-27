# Implementação — BIT-10: Visual de Ciclo de Vida

## O que foi implementado

### Backend (`backend/simulation/creature.py`)
- Constantes de cor RGB (`LIFE_COLOR_EGG`, `LIFE_COLOR_MATURE`, `LIFE_COLOR_ELDER_START`, `LIFE_COLOR_DEATH`) e de escala visual (`VISUAL_SCALE_EGG`, `VISUAL_SCALE_ADULT`, `VISUAL_SCALE_ELDER_MIN`), adicionadas logo após `METABOLISM_RATE_BY_STAGE`, como no exemplo da spec.
- Helpers puros `_lerp_rgb` e `_rgb_to_hex`.
- `compute_life_color(age, energy, max_energy)` e `compute_visual_scale(age, energy, max_energy)`, implementados literalmente conforme o código da spec (interpolação azul→verde entre idade 2-10, platô verde 10-30, e cinza→quase-preto guiado pela fração de energia restante após idade 30).
- `Creature.to_dict()` atualizado: `"radius"` agora é `self.size * compute_visual_scale(...)` e `"color"` agora é `compute_life_color(...)`. `self.size` não foi tocado (continua `10.0` fixo, usado em `motor_cost`); o raio de colisão Pymunk (`pymunk.Circle(self.body, 10.0)`) também não foi alterado — mudança é puramente cosmética no payload.

### Frontend (`frontend/src/components/SimulationCanvas.jsx`)
- Constantes de módulo `OFFSCREEN_TINT_SIZE = 64` e `TINT_ALPHA = 0.55`.
- `tintCanvasRef` (useRef) e função `drawTintedSprite(ctx, img, size, color)` dentro do componente, implementada exatamente como no exemplo da spec: canvas offscreen 64x64 reutilizado a cada chamada, `source-atop` + `fillRect` com alpha parcial para tingir preservando o detalhe do sprite, depois `drawImage` do offscreen escalado para o tamanho final no canvas principal.
- No branch de render por sprite (`bibity.png`/`egg.png`), o `ctx.drawImage(img, ...)` direto foi substituído por `drawTintedSprite(ctx, img, s, creature.color || '#4CAF50')`. O branch de fallback (círculo, sem sprite carregado) foi mantido intacto — já usava `creature.color`.

### Testes (`backend/tests/test_creature_life_visuals.py`, novo)
Duas classes de teste (`TestComputeLifeColor`, `TestComputeVisualScale`) cobrindo, sem instanciar `Creature`/Pymunk:
- Os 4 pontos-chave exatos dos critérios de aceite (idade 0 → `#3b82f6`; idade 10 → `#22c55e`; idade 31 energia cheia → `#6b7280`; idade 31 energia zero → `#111827`; escala 0.7/1.0/0.85 nos mesmos pontos).
- Platô verde/escala 1.0 entre idades 10 e 30.
- Interpolação estritamente intermediária (não igual aos extremos) nos pontos de transição (idade 6 na fase ovo→maduro; energia 50% na fase ELDER).
- Monotonicidade crescente da escala entre idade 2 e 10.

## Resultado dos testes
`cd backend && venv/Scripts/python.exe -m pytest tests/ -v` → **70 passed**, 0 failed (6 warnings de deprecation do `neat-python`, pré-existentes, não relacionados a esta mudança).

`python -c "import main"` (dentro de `backend/`) → sem erro, sem output (import limpo).

## Resultado do build do frontend
`cd frontend && npm run build` → sucesso (`vite build`, 32 módulos transformados, build em ~1.85s, sem erros/warnings de JSX).

## Decisões tomadas (não 100% explícitas na spec)
- Nos testes, além dos pontos exatos dos critérios de aceite, adicionei asserts de "não é igual a nenhum extremo" nos pontos intermediários (idade 6, energia 50%) para garantir que a interpolação realmente acontece (evita um teste que passaria com uma implementação constante por engano). Não altera o comportamento, só reforça a cobertura.
- Mantive o nome e assinatura de `drawTintedSprite` e das constantes exatamente como no exemplo da spec, sem introduzir parâmetros extras.

## Riscos conhecidos
- **Performance do tint por frame**: `drawTintedSprite` faz `clearRect` + `drawImage` + `fillRect` num canvas offscreen 64x64 para *cada* criatura, *todo frame* (via `requestAnimationFrame`, tipicamente 60 FPS). Com poucas dezenas de criaturas isso deve ser trivial, mas se a população crescer para centenas simultâneas pode valer a pena revisitar (ex.: cache de sprites pré-tintados por faixa de cor, ou throttle do tint). Fora de escopo desta task — a spec já previu o buffer fixo 64x64 reutilizado justamente para mitigar realocação, o que foi seguido à risca.
- **Resultado visual esperado**: não pude verificar visualmente no navegador (sem acesso a browser neste ambiente). A verificação manual (`/run` ou dev server + observar uma criatura do nascimento até ELDER) fica pendente para o coordenador, conforme a spec já previa no critério de aceite correspondente.
- **Conflito de merge em `creature.py`**: este arquivo está sendo modificado em paralelo por outro sub-agente (BIT-09) em worktree separado. As mudanças desta task tocam apenas nas constantes/funções novas e no `to_dict()`; o coordenador precisará reconciliar os dois diffs ao mergear.

## Escopo
Confirmado via `git status --porcelain` no worktree: apenas `backend/simulation/creature.py` (modificado), `frontend/src/components/SimulationCanvas.jsx` (modificado) e `backend/tests/test_creature_life_visuals.py` (novo) foram tocados, além deste próprio relatório em `.sdd/tasks/implementer/BIT-10/impl-report.md`. Nenhum comando `git` além de `status`/`diff` foi executado.
