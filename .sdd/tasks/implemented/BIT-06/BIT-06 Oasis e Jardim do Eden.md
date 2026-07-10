# Spec — BIT-06: Oásis Migratórios com TTL + Jardim do Éden Real

**Linear:** N/A (ver memória `bibitinhos-workflow-sem-linear`)
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

Substituir o spawn de comida hoje aleatório/uniforme (5% de chance por frame, em qualquer ponto do mapa) por um sistema de **oásis migratórios**: zonas invisíveis com TTL, dentro das quais a comida nasce; quando o TTL expira, o oásis desaparece, forçando as criaturas a se deslocarem atrás do próximo. Implementar também o "Jardim do Éden" **real** (README §5.2): quando a população cai abaixo de 10 indivíduos, gerar oásis densos nas coordenadas de cada sobrevivente — hoje o código faz algo diferente (respawna 10 criaturas novas do zero, e só quando a população chega a exatamente zero).

## Abordagem técnica

Nova classe `Oasis` (dado puro, sem corpo Pymunk — é uma zona lógica, não um objeto físico) em `backend/simulation/oasis.py`. `SimulationEngine` passa a gerenciar uma lista de oásis ativos: cria novos periodicamente (até um teto), decrementa TTL a cada `step()` e remove os expirados, e só deixa `Food` nascer dentro do raio de um oásis ativo (nunca mais em qualquer ponto do mapa). O bloco de "Jardim do Éden" é reescrito para seguir o README à risca (trigger em `< 10`, oásis densos nos sobreviventes), mantendo separado o fallback de população `== 0` (caso não coberto pelo README, mas necessário como piso de segurança).

**Sem sobreposição com BIT-05** (multiplicadores de energia por LifeStage, em refinamento paralelo nesta mesma janela de tempo): BIT-05 só toca `creature.py`; esta task só toca `engine.py` + `oasis.py` novo. Podem ser implementadas em paralelo sem conflito de arquivo.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/oasis.py` | criar | Classe `Oasis` (dado puro: `x`, `y`, `radius`, `ttl`, `food_cap`) + constantes de configuração |
| `backend/simulation/engine.py` | modificar | `self.oases: list`; bloco de spawn de comida reescrito (spawn só dentro de oásis); bloco "Jardim do Éden" reescrito (trigger `<10`, oásis densos nos sobreviventes, com histerese); `get_state()` ganha campo `"oases"` |
| `backend/tests/test_oasis.py` | criar | Testes de ciclo de vida do oásis (TTL/expiração), spawn de comida restrito ao raio, cap por oásis e cap global, trigger do Jardim do Éden com histerese, fallback de população zero preservado |

## Passos de implementação

> Passo 1 é independente; passos 2-4 dependem do 1 e são sequenciais (todos em `engine.step()`); passo 5 é independente (só `get_state()`).

1. **Criar `backend/simulation/oasis.py`**:
   ```python
   import math
   import random

   MAX_ACTIVE_OASES = 4
   OASIS_SPAWN_CHANCE_PER_FRAME = 0.01
   OASIS_RADIUS = 150.0
   OASIS_TTL_MIN = 15.0
   OASIS_TTL_MAX = 40.0
   OASIS_FOOD_CAP = 8
   OASIS_FOOD_SPAWN_CHANCE = 0.08
   MAX_TOTAL_FOOD = 50

   EDEN_POPULATION_THRESHOLD = 10
   EDEN_OASIS_RADIUS = 200.0
   EDEN_OASIS_TTL = 30.0
   EDEN_OASIS_FOOD_CAP = 20

   class Oasis:
       def __init__(self, x, y, radius=OASIS_RADIUS, ttl=None, food_cap=OASIS_FOOD_CAP):
           self.x = x
           self.y = y
           self.radius = radius
           self.ttl = ttl if ttl is not None else random.uniform(OASIS_TTL_MIN, OASIS_TTL_MAX)
           self.food_cap = food_cap

       def random_point_inside(self):
           """Amostragem uniforme dentro do circulo (evita concentracao nos cantos)."""
           angle = random.uniform(0, 2 * math.pi)
           r = self.radius * math.sqrt(random.random())
           return self.x + r * math.cos(angle), self.y + r * math.sin(angle)

       def to_dict(self):
           return {"x": self.x, "y": self.y, "radius": self.radius, "ttl": self.ttl}
   ```
   Valores de raio/TTL/cap não estão especificados no README (só a mecânica) — são constantes novas, tunáveis, documentadas como ponto de partida razoável, não bloqueantes.

2. **`engine.py` — imports e estado novo**, no topo e em `__init__`:
   ```python
   from simulation.oasis import Oasis, MAX_ACTIVE_OASES, OASIS_SPAWN_CHANCE_PER_FRAME, OASIS_FOOD_SPAWN_CHANCE, MAX_TOTAL_FOOD, EDEN_POPULATION_THRESHOLD, EDEN_OASIS_RADIUS, EDEN_OASIS_TTL, EDEN_OASIS_FOOD_CAP
   ...
   # __init__:
   self.oases = []
   self._eden_active = False
   ```

3. **`engine.py` — substituir o bloco "1. Spawn aleatório de comida"** por gestão de oásis + spawn restrito:
   ```python
   # 1. Ciclo de vida dos oasis: expira os antigos, nasce novos, comida só dentro deles
   for oasis in self.oases:
       oasis.ttl -= dt
   self.oases = [o for o in self.oases if o.ttl > 0]

   if len(self.oases) < MAX_ACTIVE_OASES and random.random() < OASIS_SPAWN_CHANCE_PER_FRAME:
       x = random.uniform(0, self.width)
       y = random.uniform(0, self.height)
       self.oases.append(Oasis(x, y))

   if len(self.foods) < MAX_TOTAL_FOOD:
       for oasis in self.oases:
           food_in_oasis = sum(
               1 for f in self.foods
               if (f.body.position.x - oasis.x) ** 2 + (f.body.position.y - oasis.y) ** 2 <= oasis.radius ** 2
           )
           if food_in_oasis < oasis.food_cap and random.random() < OASIS_FOOD_SPAWN_CHANCE:
               fx, fy = oasis.random_point_inside()
               fx = max(0, min(self.width, fx))
               fy = max(0, min(self.height, fy))
               self.add_food(Food(self, fx, fy))
               if len(self.foods) >= MAX_TOTAL_FOOD:
                   break
   ```
   Sem oásis ativos, nenhuma comida nasce — é o comportamento pretendido (força as criaturas a perseguirem os oásis, "pressão de seleção" do README).

4. **`engine.py` — reescrever o bloco "5./6. Respawn (Jardim do Éden)"**:
   ```python
   # Jardim do Eden: fallback de extincao total (populacao == 0, nao coberto pelo README)
   # + regra real do README (populacao < 10, com sobreviventes: oasis denso nas posicoes deles)
   if len(self.creatures) == 0:
       for _ in range(10):
           self.add_creature(Creature(self))
       self._eden_active = False
   elif len(self.creatures) < EDEN_POPULATION_THRESHOLD:
       if not self._eden_active:
           self._eden_active = True
           for creature in self.creatures:
               self.oases.append(Oasis(
                   creature.body.position.x, creature.body.position.y,
                   radius=EDEN_OASIS_RADIUS, ttl=EDEN_OASIS_TTL, food_cap=EDEN_OASIS_FOOD_CAP,
               ))
   else:
       self._eden_active = False
   ```
   A flag `self._eden_active` evita empilhar um oásis novo por frame enquanto a população continuar abaixo de 10 — só dispara uma vez até a população voltar a `>= 10` (histerese).

5. **`engine.py` — `get_state()`** ganha uma linha:
   ```python
   "oases": [o.to_dict() for o in self.oases],
   ```
   Campo aditivo — não quebra nenhum consumidor atual do WebSocket/frontend (frontend não vai renderizar isso nesta task).

6. **`backend/tests/test_oasis.py`**: instanciar `SimulationEngine` real e cobrir:
   - Um `Oasis` criado manualmente e adicionado a `engine.oases`: após `step()` suficientes para o `ttl` zerar, o oásis some da lista.
   - Com um oásis ativo, `Food` só nasce dentro do raio dele (checar todas as `engine.foods` após vários `step()` com `random.seed` fixo, ou usar `monkeypatch` para forçar `random.random()`/`random.uniform()` determinísticos e afirmar a posição exata).
   - Cap por oásis (`food_cap`) respeitado: popular manualmente um oásis com `food_cap` comidas dentro do raio e confirmar que nenhuma nova nasce ali.
   - Sem nenhum oásis ativo, nenhuma `Food` nasce, mesmo após vários `step()`.
   - Jardim do Éden: `engine.creatures` com 5 sobreviventes → após `step()`, exatamente 5 novos oásis nascem (um por sobrevivente), nas posições deles; rodar mais `step()` com população ainda `< 10` e confirmar que **não** nascem oásis extras (histerese); subir a população para `>= 10` e voltar a cair — confirmar que o trigger dispara de novo.
   - Fallback de população `== 0`: preservado, 10 criaturas novas nascem (mesmo comportamento de antes, sem quebrar o teste existente já implícito nisso).

## Contratos técnicos

### Backend (Simulação)
- `Oasis(x, y, radius=150.0, ttl=None, food_cap=8)` — classe pura, sem Pymunk, em `backend/simulation/oasis.py`.
- `SimulationEngine.oases: list[Oasis]` — novo atributo público.
- `SimulationEngine.get_state()["oases"]` — lista de `{"x", "y", "radius", "ttl"}`, campo aditivo no payload WebSocket (`state_update`), retrocompatível.

## Critérios de aceite

- [ ] Comida só nasce dentro do raio de um oásis ativo — nunca mais em ponto aleatório do mapa inteiro.
- [ ] Oásis expira e desaparece de `engine.oases` quando o TTL chega a zero.
- [ ] Novos oásis nascem organicamente ao longo do tempo, respeitando `MAX_ACTIVE_OASES`.
- [ ] Cap de comida por oásis (`food_cap`) e cap global (`MAX_TOTAL_FOOD`) respeitados.
- [ ] População `< 10` (com pelo menos 1 sobrevivente) gera um oásis denso na posição de cada sobrevivente, uma única vez, sem repetir a cada frame enquanto a população continuar baixa (histerese).
- [ ] População `== 0` continua fazendo respawn de 10 criaturas novas (fallback existente preservado, não coberto pelo README mas necessário).
- [ ] `get_state()` inclui `"oases"` (lista, vazia quando não há oásis ativos).
- [ ] `pytest backend/tests/test_oasis.py` 100% verde.
- [ ] Nenhuma regressão: `pytest backend/tests/` continua 100% verde.
- [ ] Simulação completa roda sem erro por alguns segundos com o novo spawn (`manager.py` → Start Tudo).

## Rollback

Deletar `backend/simulation/oasis.py` e `backend/tests/test_oasis.py`; reverter `engine.py` para o spawn de comida aleatório uniforme e o bloco de respawn antigo (`if len(self.creatures) == 0`); remover `"oases"` de `get_state()`. Sem estado persistente/migração envolvida.
