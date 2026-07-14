## Arquivos relevantes

- `backend/simulation/physics.py` — criação do `pymunk.Space` (`create_space()`, linhas 8-33) e `PhysicsEngine.step()` (linhas 39-40)
- `backend/simulation/creature.py` — constantes de locomoção (linhas 10-15), corpo/shape da criatura (linhas 84-103), `Creature.update()` (linhas 151-186, inclui o "grip lateral")
- `backend/simulation/food.py` — corpo Pymunk dinâmico da comida (linhas 6-28)
- `backend/simulation/engine.py` — `BRAIN_TICK_INTERVAL = 1/10.0` (linha 19), acumulador de brain tick (linhas 176-183), `SimulationEngine.step()` (linha 108+) chama `creature.update()` e depois `self.physics.step(dt)`
- `backend/main.py` — `simulation_loop()` (linhas 59-69): `engine.step(1/30.0)` + `sleep(1/30.0)` → tick de física real é **30 FPS**, não 60 (o `docs/implementation_plan.md` menciona 60 FPS como meta aspiracional nunca implementada — não é um item pendente de nenhuma BIT-XX)
- `backend/tests/test_locomotion.py` — testes de grip lateral e preservação de velocidade frontal
- `backend/tests/test_food_physics.py` — teste de deslocamento de comida ao ser empurrada

## Conteúdo relevante para a demanda

**`physics.py:8-33`:**
```python
def create_space():
    space = pymunk.Space()
    space.gravity = (0.0, 0.0)
    space.damping = 0.9          # <- alvo da mudança
    ...
    walls: elasticity=1.0, friction=0.5 (paredes estáticas, sem velocidade, não afetadas por damping)
```

**`creature.py:10-15`:**
```python
MOTOR_TORQUE_SCALE = 20.0
KINETIC_LINEAR_NORM = 200.0   # só normalização de sensor, não é teto físico real
KINETIC_ANGULAR_NORM = 10.0
LATERAL_GRIP_RATE = 20.0      # taxa de amortecimento lateral (1/s), tunavel
CREATURE_MASS = 1.0
```

**`creature.py:151-186` (`update`)**: aplica impulso frontal (`apply_impulse_at_local_point`) proporcional a `motor_forward * speed * dt`, torque via `motor_torque * MOTOR_TORQUE_SCALE`, e depois um bloco de "grip lateral" que decompõe `body.velocity` no frame local da criatura e amortece só o componente lateral (y) por `lateral_damping = max(0, 1 - LATERAL_GRIP_RATE*dt)`, preservando o componente frontal (x) intacto. Esse bloco **não chama `space.step()`** e é isolado do damping global do `Space` — os testes de locomoção chamam `creature.update()` diretamente, sem física global, então não são afetados por mudanças em `space.damping`.

**Validação empírica real (rodada contra `backend/venv`, Pymunk 7.2.0):**
```python
# space.damping=0.9, v0=(100,0): após 1s real de step (qualquer subdivisão de dt) -> v=(90.0, 0.0)
# Chipmunk aplica damping como pow(damping, dt) por step — é fração de velocidade retida POR SEGUNDO REAL,
# independente da taxa de sub-passos (30 FPS atual). Não há composição surpresa por causa de rodar a 30Hz.
```
Velocidade terminal sob thrust contínuo: `v_term = a / ln(1/damping)`, com `a = speed = 50.0` (thrust=1.0):
| damping | v_term | retenção após 1s parado |
|---|---|---|
| 0.9 (atual) | ~475 u/s | 90% |
| 0.35 (recomendado) | ~47.6 u/s | 35% |

Com 0.9, a criatura nunca sente arrasto em qualquer janela realista de simulação — daí a sensação "flutuante" relatada.

**`test_locomotion.py:30-46`** (`test_lateral_velocity_is_damped_towards_zero_over_frames`): parte de velocidade lateral pura 100 u/s, roda 10x `creature.update(1/30, engine)`, exige `lateral_speeds[-1] < 1.0`. Isso implica matematicamente `LATERAL_GRIP_RATE > ~11.07` — o valor atual (20.0) tem margem confortável; não precisa mudar para o objetivo desta task (arrasto longitudinal, não lateral).

**`food.py:6-7`**: `FOOD_MASS = CREATURE_MASS * 0.01` — corpo Pymunk **dinâmico** (não estático), então recebe o mesmo `space.damping` do ambiente. `test_food_physics.py::test_food_is_displaced_when_hit_by_a_moving_creature` não quebra com damping menor (colisão ocorre no frame 0 independente do damping subsequente).

## O que precisa ser feito

1. `backend/simulation/physics.py:11` — `space.damping = 0.9` → `space.damping = 0.35`.
2. `backend/simulation/creature.py:14` — manter `LATERAL_GRIP_RATE = 20.0` inalterado; adicionar comentário documentando a decisão (considerada e rejeitada) de não alterá-lo, para histórico.
3. Nenhuma mudança em `MOTOR_TORQUE_SCALE`, `speed`, `food.py`, `engine.py` ou `main.py`.

## Perguntas em aberto

Nenhuma — todas as decisões técnicas foram resolvidas e validadas empiricamente (ver seção acima) antes da consolidação da spec.
