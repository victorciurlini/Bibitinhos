# Review — BIT-10: Visual de Ciclo de Vida

## Veredito: **APROVADO COM RESSALVAS**

Nenhum bug real encontrado que bloqueie o merge. As ressalvas abaixo são observações de comportamento (algumas já previstas/exigidas pela própria spec) e um risco de robustez de baixa probabilidade no frontend — nenhuma delas quebra os critérios de aceite.

---

## O que foi validado

### Escopo
`git status --porcelain` no worktree confirma exatamente os arquivos esperados:
- `M backend/simulation/creature.py`
- `M frontend/src/components/SimulationCanvas.jsx`
- `?? backend/tests/test_creature_life_visuals.py` (novo)
- `?? .sdd/tasks/implementer/` (o próprio report/spec)

Nenhum arquivo fora de escopo tocado.

### Testes e build
- `pytest tests/ -v` → **70 passed, 0 failed** (rodei eu mesmo, não confiei no report). 6 warnings de deprecation do `neat-python`, pré-existentes, não relacionados.
- `python -c "import main"` dentro de `backend/` → import limpo, sem erro.
- `npm run build` no frontend → sucesso, 32 módulos, sem warnings de JSX.

### `compute_life_color` / `compute_visual_scale` — matemática nas bordas

Testei manualmente os limites `age == 2`, `age == 10`, `age == 30` contra o código real (`backend/simulation/creature.py:54-78`):

- **`age == 2`**: `compute_life_color` cai no branch `age <= 10`; como `age > 2` é `False` (2 não é `> 2`), `t = 0.0` → cor azul pura. `compute_visual_scale` cai no branch `age <= 2` → `0.7`. Isso é **consistente** com `life_stage` (que só vira `JUVENILE` quando `age > 2`, estritamente). Sem descontinuidade nem off-by-one.
- **`age == 10`**: `compute_life_color` com `t = (10-2)/8 = 1.0` → verde puro; o branch seguinte (`elif age <= 30`) também retorna verde puro — **contínuo** na fronteira. `compute_visual_scale` idem: `0.7 + 0.3*1.0 = 1.0`, igual ao branch `age <= 30` (`1.0`) — **contínuo**.
- **`age == 30` → `age == 30.0001`**: aqui existe uma **descontinuidade real, mas intencional e exigida pela spec**: no plateau (`age <= 30`) a cor é sempre verde puro (`#22c55e`), independente da energia; um instante depois (`age > 30`, com energia cheia) a cor pula direto para `#6b7280` (cinza `ELDER_START`), sem transição suave entre verde e cinza no eixo idade. Isso é exatamente o que os critérios de aceite pedem (`compute_life_color(age=31, energy=100, ...)` → `#6b7280`), então **não é bug** — é assim que a spec desenhou o gradiente (transição guiada por idade até 30, depois guiada só por energia). Vale registrar como observação de UX: o sprite "pula" de verde para cinza no instante exato em que cruza idade 30 se a criatura estiver com energia alta, em vez de esmaecer gradualmente. `compute_visual_scale`, por outro lado, **não** tem esse pulo: no boundary `age=30→30+ε` com energia cheia, o valor permanece `1.0` em ambos os lados (plateau adulto = 1.0, e elder com `energy_fraction=1.0` também dá `1.0`). Só a cor tem esse degrau, não a escala.

### Casos de borda de `energy`/`max_energy`

- `max_energy` é fixado em `100.0` no `__init__` (`creature.py:111`) e **nunca é mutado** em nenhum outro lugar do código (`grep` confirma: só leitura em `to_dict`, `think`, e o cap em `engine.py:34: creature.energy = min(creature.energy + food.energy_value, creature.max_energy)`). Logo, divisão por zero em `energy / max_energy` não é alcançável no fluxo real.
- `energy` pode ficar negativa (`self.energy -= dt * (...)` em `update()`, checado só depois com `if self.energy <= 0: self.is_alive = False`). Verifiquei o fluxo em `engine.py` (`step()`, linhas 140-151): a criatura morta é filtrada de `self.creatures` (`alive_creatures`/`c.die()`) **no mesmo `step()`**, antes de `main.py` chamar `engine.get_state()` na sequência (`main.py:62-63: engine.step(...); state = engine.get_state()`). Ou seja, **na prática, `to_dict()` nunca é chamado para uma criatura com energia negativa** — o cenário descrito no pedido de revisão não se manifesta no código atual.
- Mesmo assim, as funções são defensivamente corretas: o clamp `max(0.0, min(1.0, energy / max_energy))` é aplicado **depois** da divisão, mas como `max_energy` é sempre positivo e fixo, isso não inverte sinal — se `energy` fosse negativa, a fração seria negativa e o `max(0.0, ...)` a zeraria corretamente em ambas funções (`compute_life_color` e `compute_visual_scale`). Testei mentalmente `energy=-10, max_energy=100` → fração `-0.1` → clamped para `0.0` → cor = `LIFE_COLOR_DEATH` puro, escala = `0.85`. Comportamento correto caso a função seja chamada assim no futuro (ex.: por um teste direto).

### `drawTintedSprite` (frontend)

- **Técnica de tint**: `source-atop` + `globalAlpha` parcial (`0.55`) + `fillRect` no canvas offscreen é a técnica correta para tingir preservando o alpha/detalhe do sprite original (não vira silhueta sólida) — `source-atop` só desenha o `fillRect` onde o sprite já tinha pixels opacos, e o alpha parcial mistura com a cor original em vez de substituí-la.
- **Vazamento de estado**: `globalAlpha`/`globalCompositeOperation` são setados no contexto **offscreen** (`octx`), não no contexto principal (`ctx`) usado para o resto do desenho (linha de direção, comida, fundo). Como são objetos de contexto diferentes, não há vazamento para o `ctx` principal em uso normal. Risco teórico de baixa probabilidade: se `fillRect`/`drawImage` lançassem exceção *entre* `octx.globalCompositeOperation = 'source-atop'` e o reset para `'source-over'` (linhas 25-30), o estado ficaria "sujo" no `octx` reutilizado; na próxima chamada, `clearRect` zera o canvas para transparente e o `drawImage(img,...)` seguinte rodaria sob `source-atop` contra um destino 100% transparente — o que faria o sprite **não aparecer** (ficar em branco) até o próximo ciclo de reset. Não encontrei caminho realista para essa exceção ocorrer (cores vêm sempre como hex válido do backend, `fillRect`/`drawImage` não lançam em uso normal) — não é um bug reproduzível, é uma observação de robustez.
- **Reuso do buffer 64x64**: confirmado que não há resíduo visual entre criaturas — a sequência é sempre `clearRect` (zera para transparente) **antes** de `drawImage(img,...)`, então qualquer tint da criatura anterior é descartado antes do próximo sprite ser desenhado. `clearRect` de fato zera o canal alfa (limpa para `rgba(0,0,0,0)`), então não há bleed do tint anterior.
- **Distorção de proporção**: `bibity.png` tem dimensões reais **18x33** (não quadrado — confirmei lendo o chunk `IHDR` do PNG), `egg.png` é 34x35 (quase quadrado). O código força `drawImage(img, 0, 0, 64, 64)`, distorcendo a proporção original de `bibity.png`. **Isso não é uma regressão desta task**: o código anterior já fazia `ctx.drawImage(img, -s/2, -s/2, s, s)` diretamente no canvas principal, forçando o mesmo formato quadrado `s x s` a partir da imagem não-quadrada — ou seja, a mesma distorção já existia antes. A etapa nova (64x64 → `size x size`) é um reescalonamento uniforme (proporção 1:1 mantida entre largura e altura do buffer quadrado), então não introduz distorção adicional além da que já existia.

### Campo `color`/`diet` legado

`grep` por `diet` e por padrões de cor antiga (`#00ff00`, `#ff0000`) em todo o repo (backend + frontend) não encontrou nenhum uso residual dependente do valor antigo baseado em dieta. `diet` continua sendo enviado no payload (`to_dict()["diet"]`) e não foi removido — só deixou de alimentar `color`, exatamente como a spec previa. Nenhum outro ponto do frontend lê `creature.diet` para decidir cor.

---

## Ressalvas (não bloqueantes)

1. **Pulo abrupto de cor em `age == 30`** (verde puro → cinza `ELDER_START`, sem fade, quando a energia está cheia): comportamento exigido explicitamente pelos critérios de aceite da spec, não é bug de implementação — mas é uma característica visual que pode valer revisitar em uma iteração futura de polish (ex.: um pequeno blend também no eixo idade perto de 30).
2. **Robustez teórica do `drawTintedSprite`**: se uma exceção interrompesse a função entre o `source-atop` e o reset, o próximo frame tingiria contra um canvas transparente e o sprite sumiria temporariamente. Não é um cenário realista com os dados atuais (cor sempre vem como hex válido do backend), mas não há um `try/finally` protegendo o reset — mencionado como nice-to-have, não como bloqueio.
3. **Verificação visual manual no navegador** (critério de aceite explícito da spec) não foi feita nesta revisão nem pelo implementador — nenhum dos dois teve acesso a browser no ambiente. Fica pendente para quem fizer o merge/smoke test final.

## Recomendação

Aprovar o merge. Nenhum bug funcional real bloqueia — a lógica de `compute_life_color`/`compute_visual_scale` bate exatamente com os critérios de aceite testados (age 0/10/31, energia 0/50/100), os testes automatizados passam (70/70), o build do frontend é limpo, e o escopo tocado é exatamente o previsto na spec. Sugiro apenas: (a) fazer a verificação visual manual pendente antes de considerar a task 100% fechada, e (b) opcionalmente abrir uma nota de backlog para suavizar o degrau de cor em `age == 30` se o efeito visual incomodar na prática.
