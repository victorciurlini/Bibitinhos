## Arquivos relevantes

- `backend/simulation/creature.py` — `Creature.update()`, aplicação de impulso/torque (BIT-02)
- `backend/venv/Lib/site-packages/pymunk/vec2d.py` — API `Vec2d.rotated()`, usada para decompor velocidade em componentes local (frente/lado)

## Conteúdo relevante para a demanda

### Causa raiz do "andar sem controle" (`creature.py::update()`, estado pós-BIT-04)

```python
if self.life_stage != LifeStage.EGG:
    forward_impulse = (self.motor_forward * self.speed * dt, 0)
    self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
    self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE
    motor_cost = abs(self.motor_forward) * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05
```

O impulso já é aplicado no eixo local (`apply_impulse_at_local_point`, eixo x local = "frente" do body), então a força em si nunca empurra de lado. O problema é **inércia física sem atrito lateral**: o Pymunk é um motor de física livre (estilo "espaço", sem gravidade, `space.damping=0.9` uniforme em todas as direções). Quando a criatura gira (torque) enquanto já tem velocidade linear acumulada de antes, o vetor velocidade **não acompanha automaticamente** a nova direção do body — ele continua "deslizando" na direção antiga enquanto o body gira por baixo dele. Resultado visível: a criatura parece derrapar de lado ou andar de ré mesmo que só esteja aplicando impulso pra frente e torque pra girar. Isso é o comportamento correto de física newtoniana livre, mas indesejado para o efeito de navegação pretendido ("sempre pra frente, fazendo curvas").

Também não há nenhum clamp em `motor_forward`: a rede pode gerar valores negativos (saída `tanh`, range `[-1,1]`), que hoje viram impulso pra trás de propósito — o pedido do developer é eliminar isso (só avançar, nunca recuar deliberadamente).

### API validada ao vivo (pymunk 7.2.0 instalado)

```python
>>> from pymunk import Vec2d
>>> Vec2d(1,0).rotated(0.5)   # rotaciona CCW por padrão, mesma convenção de body.angle/arctan2 usada no projeto (sensors.py)
Vec2d(0.8775825618903728, 0.479425538604203)
>>> body.velocity.rotated(-body.angle)   # transforma velocidade do frame mundo para o frame local do body (x=frente, y=lado)
Vec2d(5.367722858950708, 0.4330719449445142)
```
`body.velocity` é um `Vec2d` (confirmado via `type()`), com `.rotated(angle)` disponível — permite decompor a velocidade em componente "frente" (x local) e "lado" (y local) do body, e recompor depois de amortecer só o componente lateral. Técnica padrão de "grip"/aderência de pneu em jogos 2D top-down (ex.: carros arcade), aplicável 1:1 aqui.

### Testes existentes relevantes (risco de regressão)

`grep` em `backend/tests/` por `motor_forward`/`motor_torque`/`body.velocity`: nenhum teste usa valor negativo de `motor_forward`, nenhum teste faz asserção sobre a direção/vetor de velocidade resultante do impulso. Os únicos usos são: range check `-1.0 <= x <= 1.0` (sobre `think()`, não afetado — clamp só entra em `update()`), e valores fixos `0.0`/`1.0` (não afetados por um clamp `max(0.0, x)`, já são `>=0`). **Baixo risco de regressão** nos 32 testes atuais — nenhum precisa ser alterado.

### Sobreposição com BIT-05 (ainda não implementada/aprovada)

BIT-05 (metabolismo passivo) também modifica `Creature.update()`, na mesma região do bloco `if self.life_stage != LifeStage.EGG:` (soma um `metabolism_cost` ao custo final). Não há dependência funcional entre as duas tasks, mas **ambas tocam a mesma função** — implementar em sequência (uma de cada vez, cada uma partindo de `develop` já com a outra mergeada) evita conflito de merge, seguindo o mesmo padrão já usado para BIT-02/03/04.

## O que precisa ser feito

1. Clampar o impulso de avanço para nunca ser negativo (`forward_thrust = max(0.0, self.motor_forward)`) — a rede ainda pode gerar `motor_forward` negativo internamente (não altera `think()`/contrato de I/O do NEAT), mas isso deixa de virar impulso/custo de energia para trás. Fisicamente, a criatura passa a só ser capaz de propelir a si mesma pra frente.
2. Adicionar "grip" lateral: a cada frame de física, decompor `self.body.velocity` em componente frente/lado (relativo a `self.body.angle`) e amortecer fortemente o componente lateral, preservando o componente de frente — elimina o deslizamento de lado sem remover a inércia de avanço (a criatura ainda "sente" física real ao ser empurrada por colisões, só não desliza de lado indefinidamente por conta própria).
3. Escopo fica inteiro em `creature.py::update()` — nenhuma mudança em `engine.py`, `think()`, contrato de I/O do NEAT, frontend ou protocolo WebSocket.

## Perguntas em aberto

Nenhuma — abordagem (clamp de avanço + grip lateral via decomposição de velocidade, mantendo física real em vez de sobrescrever velocidade de forma totalmente cinemática) foi validada tecnicamente contra a API real do pymunk instalado; decisão de manter inércia física (em vez de snap 100% cinemático) segue a filosofia já documentada do projeto ("física real via pymunk", ver memória `bibitinhos-project-overview`).
