# Research — Simulação (backend/simulation/) — BIT-18

> Investigação feita diretamente pelo orquestrador (leitura de código + validação empírica via
> simulação headless com o venv do projeto), sem sub-agente.

## Arquivos relevantes

- `backend/simulation/oasis.py` — classe `Oasis` (BIT-06) + constantes de configuração
- `backend/simulation/engine.py` — ciclo de vida dos oásis, spawn de comida, Jardim do Éden (dentro de `step()`)
- `backend/simulation/food.py` — classe `Food` (corpo Pymunk dinâmico leve, `is_active`, `consume()`)
- `backend/main.py` — loop de simulação: `engine.step(1/30.0)` a 30 FPS
- `backend/tests/test_oasis.py` — 9 testes cobrindo TTL de oásis, spawn restrito, caps, Éden com histerese

## Conteúdo relevante para a demanda

### Estado atual (BIT-06, commit `e2f583b`)

- `Oasis(x, y, radius=150.0, ttl=None, food_cap=8)` — zona lógica invisível, sem corpo Pymunk.
  `ttl` sorteado em `[15, 40]`s. `to_dict()` → `{"x", "y", "radius", "ttl"}`.
- Constantes: `MAX_ACTIVE_OASES = 4`, `OASIS_SPAWN_CHANCE_PER_FRAME = 0.01`,
  `OASIS_FOOD_SPAWN_CHANCE = 0.08`, `MAX_TOTAL_FOOD = 50`,
  `EDEN_POPULATION_THRESHOLD = 10`, `EDEN_OASIS_RADIUS = 200.0`, `EDEN_OASIS_TTL = 30.0`, `EDEN_OASIS_FOOD_CAP = 20`.
- `engine.step()`: decrementa TTL dos oásis e remove expirados; spawn natural respeita
  `len(self.oases) < MAX_ACTIVE_OASES`; comida só nasce dentro de oásis ativo, gated por
  `len(self.foods) < MAX_TOTAL_FOOD` e pelo `food_cap` por oásis.
- Jardim do Éden (`engine.py`, bloco 6): população `< 10` com sobreviventes → um oásis denso por
  sobrevivente, one-shot com histerese (`self._eden_active`). População `== 0` → respawn de 10 criaturas.
- `Food`: sem TTL. `consume()` marca `is_active = False` e remove corpo+shape do space Pymunk
  (com try/except para dupla remoção). `engine.step()` filtra `self.foods` por `is_active` a cada frame.

### Diagnóstico empírico (simulação headless, 180s, seed 42, 10 criaturas iniciais, dt=1/30)

| t | foods | oases | creatures | comidas criadas (acum.) |
|---|---|---|---|---|
| 15s | 24 | 3 | 10 | 25 |
| 30s | 50 | 12 | 4 | 51 |
| 105s | 50 | 1 | 2 | 52 |
| 180s | 50 | 13 | 9 | 56 |

**Bug A — saturação do cap global de comida.** Comida não consumida de oásis expirados fica no
mapa para sempre (sem TTL). Aos ~30s `len(foods)` atinge `MAX_TOTAL_FOOD = 50` e a renovação
praticamente cessa (~5 comidas novas em 150s). Causa direta do sintoma reportado
("as comidas do mapa não são renovadas").

**Bug B — Éden ignora o cap de oásis.** `MAX_ACTIVE_OASES` só limita o spawn natural; o bloco do
Éden faz `append` sem teto. Com a população oscilando por fome (10→4→2→respawn 10), o Éden
redispara a cada ciclo — observados **13 oásis simultâneos**.

## O que precisa ser feito

1. `Food` ganha TTL (`FOOD_TTL = 30.0`s): `engine.step()` decrementa e expira via `consume()`
   (reaproveita a remoção do corpo Pymunk e o filtro `is_active` já existentes).
2. Teto duro `MAX_TOTAL_OASES = 10` em `oasis.py`, respeitado também pelo Éden.
3. `Oasis` ganha `ttl_initial` + `to_dict()["ttl_fraction"]` (para fade-out no frontend — campo aditivo).
4. Novos testes em `test_oasis.py`: expiração de comida, renovação contínua após saturação,
   teto do Éden.

## Perguntas em aberto

Nenhuma — valores de constantes decididos na spec (tunáveis, não bloqueantes).
