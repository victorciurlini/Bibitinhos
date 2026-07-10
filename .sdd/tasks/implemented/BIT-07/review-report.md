# Review Report — BIT-07: Locomoção Orientada a Direção

Revisor independente. Branch `BIT-07`, working tree não commitada. Revisão baseada em leitura do diff, leitura da spec, e verificação empírica (scripts Python rodando pymunk real + suíte pytest).

## Veredito

**APROVADO**

Nenhum bug de correção encontrado. A matemática da decomposição/recomposição de velocidade foi verificada empiricamente com pymunk real (não só por leitura) e está correta. Todos os critérios de aceite automatizáveis estão atendidos, a suíte completa passa 100%, e os testes novos não são flaky (10 execuções consecutivas, resultado idêntico).

## Critérios de aceite — checklist

1. **Criatura com `motor_forward` negativo não recebe impulso pra trás** — **atendido**. `forward_thrust = max(0.0, self.motor_forward)` clampa antes do impulso. Confirmado por `test_negative_motor_forward_produces_no_backward_thrust` e por script manual (criatura com velocidade de frente pré-existente `(5,0)`, `motor_forward=-1.0`: velocidade local de frente permanece exatamente `5.0`, sem redução — o clamp zera o impulso, não subtrai nada da velocidade existente, como esperado).

2. **Velocidade lateral amortecida ao longo de frames, tendendo a zero** — **atendido**. Verificado com `test_lateral_velocity_is_damped_towards_zero_over_frames` e reproduzido manualmente: decaimento geométrico com fator `(1 - 20/30) ≈ 0.333` por frame a `dt=1/30`, monotonicamente decrescente, sem drift.

3. **`motor_forward` positivo continua acelerando pra frente (grip não amortece componente de avanço)** — **atendido**. `test_forward_velocity_is_preserved_by_grip` passa. Smoke test próprio (90 frames, `motor_forward=1.0`, `motor_torque=0.5` constante) mostra componente de frente crescendo de `1.67` para `87.3` enquanto componente lateral permanece sempre `< 0.1` em módulo — comportamento de "andar pra frente fazendo curva", não "deslizar".

4. **`motor_cost` nunca gerado por propulsão pra trás** — **atendido**. `motor_cost = forward_thrust * ...` usa a variável já clampada. Verificação numérica: criatura com `motor_forward=-1.0`, `motor_torque=3.0` — energia gasta bateu exatamente com `(1/30) * (0 [custo de frente] + abs(3.0)*size*0.05 [custo de torque] + 0.8 [metabolismo ADULT])`, ou seja, custo de propulsão à ré é exatamente zero, só torque e metabolismo contam.

5. **`EGG` sem nenhuma lógica de movimento/grip** — **atendido**. Bloco inteiro (impulso, torque, custo, grip) está dentro do mesmo `if self.life_stage != LifeStage.EGG:`. Busca por qualquer outra atribuição a `body.velocity`/`apply_impulse`/`body.torque` em `backend/simulation/` confirma que a única atribuição de velocidade do projeto é essa linha, guardada pelo mesmo `if`. Não há caminho indireto (colisões físicas continuam via solver do Pymunk, não são afetadas por este diff). `test_egg_has_no_locomotion_or_grip_logic` confirma igualdade exata de `Vec2d`.

6. **`pytest backend/tests/test_locomotion.py` 100% verde** — **atendido**. 5 passed. Rodado 10x seguidas para checar flakiness: 5 passed em todas as 10 execuções, sem variação. O teste de monotonicidade não tem risco real de flakiness aqui: como o teste chama `creature.update()` diretamente (sem `engine.step()`/`space.step()`), `body.angle` nunca muda entre as chamadas (fica travado em `0.0`, sem torque aplicado), então a decomposição lateral é uma multiplicação geométrica pura por um fator fixo `< 1` a cada frame — sem termos cruzados de rotação que poderiam introduzir ruído de ponto flutuante ascendente.

7. **Suíte completa 100% verde (nenhuma regressão)** — **atendido**. `53 passed` (ver seção abaixo).

8. **Validação visual manual (pós-merge)** — **não verificável por este review** (a própria spec marca como não-automatizável). Como proxy automatizado, smoke test com torque constante mostra trajetória compatível com "curva suave sem deslizamento" (ver item 3), mas isso não substitui a checagem visual real no `manager.py` que a spec pede antes de considerar a task concluída do ponto de vista de produto.

## Resultado real do pytest

```
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
...
======================= 53 passed, 6 warnings in 0.81s ========================
```

Todos os 53 testes passaram, incluindo os 5 novos de `test_locomotion.py`. Os warnings são `DeprecationWarning` do `neat-python` (pré-existentes, não relacionados ao diff).

## Bugs / problemas encontrados

Nenhum bug de correção encontrado.

### Validação empírica da matemática de rotação (ponto crítico do pedido)

Script rodado com pymunk real, `body.angle = 0.7` (não-trivial) e um vetor de velocidade mundo conhecido `(30, -10)`:

- `body.velocity.rotated(-body.angle)` bateu exatamente com a matriz de rotação manual `R(-0.7)·v` — confirma que decompõe corretamente para o frame local (x=frente, y=lado).
- `damped_local.rotated(body.angle)` (recomposição) bateu exatamente com `R(0.7)·damped_local` — confirma volta correta pro frame mundo.
- Confirmado também que a convenção de `apply_impulse_at_local_point((F,0), (0,0))` (usada para o impulso de avanço) é consistente com a mesma convenção de `Vec2d.rotated(angle)`: aplicar impulso local `(5,0)` num body com `angle=0.7` produz `body.velocity == (5·cos(0.7), 5·sin(0.7))`, que é exatamente o "eixo x local" usado na decomposição do grip. Ou seja, o eixo "frente" do impulso e o eixo "frente" (x) da decomposição de grip são o mesmo eixo — não há descasamento de convenção entre as duas operações.

Nenhuma divergência numérica encontrada em nenhum dos testes manuais.

## Observações de qualidade (não bloqueantes)

- **Overshoot de `LATERAL_GRIP_RATE * dt`** (ponto 3 do pedido): matematicamente, para `dt > 0.05s` (< 20 FPS), `1.0 - 20*dt` ficaria negativo, mas o `max(0.0, ...)` evita inversão de sinal — nesse caso o efeito é apenas "amortecimento total em 1 frame" (lateral zerado de uma vez) em vez de inverter a velocidade, o que é um degrade aceitável, não uma explosão numérica. Na prática o projeto usa `dt=1/30` fixo (`backend/main.py:62`, `20*1/30 ≈ 0.667`), então isso nunca ocorre em produção. Não é um bug, apenas um comentário de robustez como o próprio pedido antecipou.
- **Latência de um frame entre torque e grip**: dentro de um mesmo `engine.step()`, `physics.step(dt)` roda antes de `creature.update()` (ver `backend/simulation/engine.py:100-142`), então o `body.torque` setado em `update()` só afeta `body.angle` no próximo `engine.step()`. Isso é o padrão de integração semi-implícita já existente no projeto (não introduzido por este diff) e não causa problema de correção — só significa que o "grip" de um frame usa o ângulo resultante do torque do frame anterior, o que é esperado.
- Pequena diferença estilística entre spec e implementação: a spec usa uma tupla intermediária (`damped_local_velocity = (x, y)` seguido de `pymunk.Vec2d(*damped_local_velocity)`), a implementação constrói o `Vec2d` diretamente (`pymunk.Vec2d(local_velocity.x, local_velocity.y * lateral_damping)`). Resultado idêntico, código levemente mais direto — não é um problema.
