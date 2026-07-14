# Review Report — BIT-17: Ambiente Aquático

## Veredito
APROVADO

## O que foi verificado

1. **Diff exato contra a spec.** As mudanças estão no working tree (não commitadas ainda na branch `BIT-17`), então comparei `git diff develop -- backend/simulation/physics.py backend/simulation/creature.py frontend/src/components/SimulationCanvas.jsx`:
   - `physics.py:11`: `space.damping = 0.9` → `0.35`, com o comentário exatamente como especificado.
   - `creature.py:14-17`: `LATERAL_GRIP_RATE = 20.0` mantido inalterado, comentário de decisão adicionado logo abaixo, texto idêntico ao pedido na spec.
   - `SimulationCanvas.jsx`: removida a linha `images.current.fundo = loadImg(...)`; os 3 call-sites de `#1e1e1e` trocados para `#0a1e2e` (linhas 55/92/221 originais); bloco `drawImage(images.current.fundo, ...)` substituído pelo gradiente vertical `createLinearGradient` com os stops `#1a5079`/`#0d2c44` exatamente como no passo 3 da spec.
   - Todas as mudanças batem 1:1 com o "Passos de implementação" e a tabela "Arquivos a tocar" da spec. Nenhuma mudança fora de escopo nesses 3 arquivos.
   - Fora de escopo (ignorado conforme instrução): `.gitignore` (entrada `.codegraph/`) e `.claude/settings.local.json` (permissões de `WebFetch`) — não relacionados a esta task.

2. **Suíte de testes.** Rodei eu mesmo `venv/Scripts/python.exe -m pytest tests/ -v` em `backend/`: **85 passed, 6 warnings** (warnings são `DeprecationWarning` pré-existentes do pacote `neat`, não relacionados). `test_locomotion.py` (5 testes, incluindo `test_lateral_velocity_is_damped_towards_zero_over_frames`) e `test_food_physics.py` (4 testes) 100% verdes. Inspecionei o corpo desses dois arquivos: nenhum assert depende de valor numérico atrelado a `space.damping=0.9` — `test_food_physics` só verifica deslocamento relativo (`moved > 1.0`) ou posição parada sob força zero; `test_locomotion` testa monotonicidade e limiar (`< 1.0`), não velocidades absolutas amarradas ao damping antigo. Portanto o teste passar não é coincidência frágil.

3. **Busca por outros consumidores fora dos 3 arquivos.** `grep -r "fundo"` no repo inteiro: único código-fonte que referenciava é o próprio `SimulationCanvas.jsx` (já corrigido); demais ocorrências são documentação (`.sdd/tasks/...`), sem impacto funcional. `grep -r "damping"`: única ocorrência de `space.damping` é `physics.py`; as demais ocorrências de "damping" no código são `LATERAL_GRIP_RATE`/`lateral_damping` em `creature.py`, mecanismo ortogonal já contemplado pela spec. Nenhum outro módulo (engine.py, manager.py, sensors.py) hardcoda expectativas de velocidade ligadas ao damping antigo.

4. **Validação empírica do `space.damping=0.35` com Pymunk real do venv**, usando as classes reais do projeto (`SimulationEngine` + `Creature.update()`, não uma reimplementação simplificada). Script em `C:\Users\victo.000\AppData\Local\Temp\claude\...\scratchpad\validate_damping.py`, comparando `damping=0.9` (antigo) vs `0.35` (novo):
   - **Impulso contínuo** (`motor_forward=1.0` todo frame, criatura fixada no centro do mapa para evitar colisão com parede): com `0.35` a velocidade converge para um terminal de **~46 u/s em ~2-4s** (bate com o cálculo teórico da spec, `v_term = speed/ln(1/damping) ≈ 47.6`). Com `0.9`, a velocidade ainda está subindo (**~163 u/s aos 4s**, longe do terminal teórico de ~475 u/s) — confirma empiricamente o diagnóstico da spec de que o damping antigo era "impercebível em qualquer janela realista".
   - **Impulso intermitente** (0.3s empurrando / 1.0s parado, repetido): com `0.35`, a velocidade retém exatamente **35% após 1s parado** (perde 65% em 1 segundo — efeito bem perceptível) e o valor de velocidade entre ciclos **não cresce indefinidamente** (fica oscilando entre ~13-17 u/s), ou seja, a criatura realmente "precisa se forçar periodicamente" como pedido. Com `0.9`, retenção de 90%/s e a velocidade **cresce sem limite claro entre ciclos** (14.7 → 27.6 → 38.8 → 48.6 u/s e subindo), reproduzindo a sensação "flutuante"/gelo descrita no problema.
   - Conclusão: `0.35` não é agressivo nem fraco demais — produz exatamente o comportamento qualitativo pedido (arrasto de água perceptível, mas movimento sob impulso contínuo ainda ocorre e converge rápido a um terminal utilizável).

5. **`npm run build`** rodado em `frontend/`: build limpo, sem erros (`✓ built in 1.62s`, 32 módulos transformados).

6. **Gradiente recriado por frame.** Confirmei no código (`SimulationCanvas.jsx:106-112`) que `ctx.createLinearGradient` roda dentro do `renderLoop` chamado via `requestAnimationFrame`. `CanvasGradient` é um objeto leve, local à função, sem retenção externa — é coletado pelo GC a cada frame sem acumular. O custo de criar+preencher um gradiente linear de 2 stops é desprezível frente ao resto do loop (que já itera todas as criaturas desenhando cones de visão com múltiplos arcos, sprites tingidos, etc.); não há vazamento nem custo perceptível.

## Divergências da spec (se houver)

Nenhuma. Todas as 3 mudanças (backend `physics.py`, `creature.py`, frontend `SimulationCanvas.jsx`) correspondem exatamente ao texto da spec, incluindo os comentários adicionados.

## Riscos encontrados

- **Baixo, não-bloqueante — normalização do sensor cinético.** `KINETIC_LINEAR_NORM = 200.0` (`creature.py:12`) normaliza `body.velocity.length` como entrada da rede neural (`creature.py:145`). Com o damping antigo (0.9), o terminal teórico sob impulso contínuo era ~475 u/s, então o sensor tinha alguma chance de se aproximar da saturação (±1.0) em cenários de impulso sustentado. Com o damping novo (0.35), o terminal cai para ~46-50 u/s — bem abaixo do norm de 200 — então esse sensor de entrada da rede tende a operar quase sempre numa faixa estreita (~0 a ~0.25), reduzindo a riqueza desse canal de sinal para a evolução via NEAT. Isso não é um bug (nada quebra, nenhum teste falha) e a spec não pediu para tocar em `KINETIC_LINEAR_NORM` — é apenas um efeito colateral emergente que vale documentar para uma eventual task futura de retuning dos sensores, não bloqueia esta task.
- **Não é risco:** confirmei que `Food` (corpo dinâmico) realmente recebe o novo damping (não há isolamento por corpo no Pymunk — `space.damping` é global), como a spec já previa e aceitava explicitamente; os testes de `test_food_physics.py` continuam verdes porque não dependem de magnitude absoluta de velocidade.
- **Não é risco:** paredes (`static_body`) e `Oasis` (sem corpo Pymunk) de fato não são afetadas pelo damping, confirmado por leitura do código de `physics.py` e ausência de qualquer corpo dinâmico associado a `Oasis`.

## Recomendação

Nenhuma ação obrigatória antes de finalizar. Sugestão não-bloqueante para backlog: considerar revisar `KINETIC_LINEAR_NORM` numa task futura de tuning de sensores, já que o novo teto de velocidade prático (~46-50 u/s) ficou bem abaixo do valor de normalização atual (200.0), o que pode enfraquecer esse canal de entrada da rede neural ao longo de gerações. Também recomendo, quando a branch for commitada, rodar a validação manual do passo 5 da spec (observar via `manager.py` por alguns minutos) já que esta revisão cobriu evidência automatizada/empírica mas não a validação visual manual em tempo real.
