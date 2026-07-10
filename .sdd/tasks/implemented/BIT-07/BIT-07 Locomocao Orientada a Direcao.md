# Spec — BIT-07: Locomoção Orientada a Direção

**Linear:** N/A
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

Hoje as criaturas parecem "andar sem controle" ao navegar: deslizam de lado ou parecem se mover de ré mesmo aplicando impulso pra frente e torque pra girar. Causa raiz: física newtoniana livre do Pymunk sem atrito lateral — quando a criatura gira enquanto já tem velocidade acumulada, o vetor velocidade não acompanha a nova direção do body, continuando a "derrapar" na direção antiga. Além disso, `motor_forward` (saída da rede NEAT) pode ser negativo e hoje isso vira impulso deliberado pra trás.

Tornar a locomoção orientada a direção: a criatura só propele a si mesma pra frente (nunca deliberadamente pra trás) e faz curvas via torque, sem deslizar de lado por inércia própria.

## Abordagem técnica

Duas mudanças isoladas em `Creature.update()`: (1) clampar o impulso de avanço para nunca ser negativo (`max(0.0, motor_forward)`), eliminando propulsão deliberada pra trás; (2) a cada frame de física, decompor `body.velocity` em componente frente/lado relativo a `body.angle` (via `Vec2d.rotated()`, API validada contra o pymunk 7.2.0 instalado) e amortecer fortemente o componente lateral, preservando o componente de frente — elimina deslizamento de lado sem descartar a física real (colisões ainda empurram a criatura fisicamente; ela só não desliza de lado indefinidamente por conta própria). Alternativa descartada: sobrescrever `body.velocity` 100% de forma cinemática (sempre exatamente alinhada ao heading, sem inércia nenhuma) — mais simples, mas contradiz a decisão arquitetural já documentada do projeto de manter física real via Pymunk; a abordagem de "grip" preserva inércia/colisões físicas de verdade.

**Sobreposição de arquivo com BIT-05** (metabolismo passivo, ainda não implementada): ambas tocam `Creature.update()` na mesma região. Sem dependência funcional, mas recomenda-se implementar uma de cada vez a partir de `develop` (a que for implementada primeiro mergeia antes da outra começar), para evitar conflito de merge — mesmo padrão já usado em BIT-02/03/04.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | `update()`: clamp de `motor_forward` para impulso/custo; novo bloco de "grip lateral" após aplicar impulso/torque |
| `backend/tests/test_locomotion.py` | criar | Testes: sem impulso pra trás mesmo com `motor_forward` negativo; velocidade lateral é amortecida ao longo de frames; velocidade de frente é preservada |

## Passos de implementação

> Passo 1 é independente; passo 2 depende do 1 (usa o mesmo bloco `if self.life_stage != LifeStage.EGG:`); passo 3 depende de 1-2.

1. **`creature.py`** — nova constante no topo do módulo, junto das existentes:
   ```python
   LATERAL_GRIP_RATE = 20.0  # taxa de amortecimento lateral, unidades: 1/segundo
   ```
   No bloco de movimento de `update()`, trocar:
   ```python
   if self.life_stage != LifeStage.EGG:
       forward_impulse = (self.motor_forward * self.speed * dt, 0)
       self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
       self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE
       motor_cost = abs(self.motor_forward) * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05
   ```
   por:
   ```python
   if self.life_stage != LifeStage.EGG:
       forward_thrust = max(0.0, self.motor_forward)  # sem propulsao deliberada pra tras
       forward_impulse = (forward_thrust * self.speed * dt, 0)
       self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
       self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE
       motor_cost = forward_thrust * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05

       # Grip lateral: elimina deslizamento de lado por inercia, mantendo a fisica real
       # (colisoes ainda empurram a criatura; ela so nao desliza de lado por conta propria)
       local_velocity = self.body.velocity.rotated(-self.body.angle)  # x=frente, y=lado
       lateral_damping = max(0.0, 1.0 - LATERAL_GRIP_RATE * dt)
       damped_local_velocity = (local_velocity.x, local_velocity.y * lateral_damping)
       self.body.velocity = pymunk.Vec2d(*damped_local_velocity).rotated(self.body.angle)
   ```
   Notas de implementação:
   - `self.motor_forward` (atributo cacheado por `think()`, BIT-02) continua podendo ser negativo — não alterar `think()` nem o contrato de I/O do NEAT. Só a variável local `forward_thrust` (usada pro impulso e pro custo de energia) é clampada.
   - `motor_cost` passa a usar `forward_thrust` (já não-negativo) em vez de `abs(self.motor_forward)` — resultado numérico idêntico quando `motor_forward >= 0` (caso mais comum), difere só quando negativo (agora custa 0 de propulsão, já que nenhum impulso é de fato aplicado).
   - `LATERAL_GRIP_RATE=20.0` com `dt=1/30s` (tick de física do projeto) dá `lateral_damping ≈ 0.333` por frame — componente lateral cai a ~33% do valor anterior a cada frame de física, praticamente eliminado (< 1% do valor original) em ~5 frames (~166ms). Valor tunável, documentar como tal no código.
   - `pymunk.Vec2d` já está disponível via `import pymunk` (não precisa de import adicional — `body.velocity` já retorna um `Vec2d`, e `pymunk.Vec2d(x, y)` constrói um novo).
   - Bloco só roda fora de `LifeStage.EGG` (mesmo guard já existente) — ovo continua sem nenhuma lógica de movimento/grip, preservando o comportamento já testado em BIT-02/03.

2. **`backend/tests/test_locomotion.py`** (criar), casos mínimos:
   - `motor_forward` negativo (ex. `-1.0`) numa criatura `ADULT`: após `update()`, a velocidade no eixo local de frente não deve ser negativa (sem propulsão pra trás) — usar `body.velocity.rotated(-body.angle).x >= 0` (com alguma tolerância se já havia velocidade residual de um teste anterior; preferir corpo com velocidade inicial zero).
   - Criatura com velocidade lateral inicial forte (ex. setar `body.velocity` manualmente para um vetor perpendicular ao `body.angle`) e `motor_forward=motor_torque=0`: após alguns `update()` consecutivos, o componente lateral da velocidade (decomposto do mesmo jeito que a implementação) deve diminuir monotonicamente e ficar próximo de zero.
   - Criatura com `motor_forward=1.0`, `motor_torque=0.0`, sem velocidade lateral inicial: após `update()`, o componente de frente da velocidade aumenta (grip lateral não anula a propulsão pra frente).
   - Smoke test: `SimulationEngine` real com algumas criaturas, 30+ steps, sem exceção (confirma que a decomposição de `Vec2d`/reatribuição de `body.velocity` não quebra a integração com o resto do engine).

3. **Rodar a suíte completa** (`backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`) e confirmar 100% verde — hoje 41 testes (ou 41+N se BIT-05 já tiver sido mergeada antes desta), nenhum deveria quebrar (nenhum teste existente usa `motor_forward` negativo nem faz asserção sobre vetor de velocidade, conforme levantamento em `research/simulation-core.md`).

## Contratos técnicos

### Backend (Simulação)
- Nova constante em `creature.py`: `LATERAL_GRIP_RATE: float = 20.0` (1/segundo, tunável).
- `Creature.update(dt, engine)`: comportamento estendido, mesma assinatura pública. `self.motor_forward` continua podendo ser lido como negativo (cache de `think()`, inalterado); a propulsão física efetiva e o custo de energia associado passam a ser sempre `>= 0`.
- Nenhuma mudança em `SimulationEngine`, `think()`, `rtneat_wrapper.py`, `neat_config.ini`, protocolo WebSocket ou frontend.

## Critérios de aceite

- [ ] Uma criatura com `motor_forward` negativo não recebe impulso pra trás (velocidade no eixo local de frente nunca fica negativa só por causa disso).
- [ ] Uma criatura com velocidade lateral (deslizamento de lado) e motores em zero tem essa velocidade lateral amortecida ao longo de poucos frames, tendendo a zero.
- [ ] Uma criatura com `motor_forward` positivo continua acelerando normalmente pra frente (grip lateral não amortece o componente de avanço).
- [ ] Custo de energia de movimento (`motor_cost`) nunca é gerado por propulsão pra trás (já que ela não existe mais fisicamente).
- [ ] `EGG` continua sem nenhuma lógica de movimento/grip (comportamento herdado intocado).
- [ ] `pytest backend/tests/test_locomotion.py` 100% verde.
- [ ] Nenhuma regressão: suíte completa 100% verde.
- [ ] Validação visual (manual, pós-merge): rodando `manager.py` → Start Tudo, as criaturas visivelmente fazem curvas suaves em vez de deslizar de lado/ré — não é um critério automatizável, mas deve ser conferido antes de considerar a task realmente concluída do ponto de vista de produto.

## Rollback

Reverter o bloco de movimento em `creature.py::update()` para a versão anterior (impulso direto de `self.motor_forward` sem clamp, sem bloco de grip lateral) e remover `LATERAL_GRIP_RATE`; deletar `backend/tests/test_locomotion.py`. Sem estado persistente/migração envolvida.
