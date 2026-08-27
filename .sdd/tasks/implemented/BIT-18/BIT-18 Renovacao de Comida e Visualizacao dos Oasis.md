# Spec — BIT-18: Renovação de Comida e Visualização dos Oásis

**Linear:** N/A (ver memória `bibitinhos-workflow-sem-linear`)
**Risco:** medium
**Camada(s):** Múltiplas (Backend Simulação + Frontend)

---

## Demanda

O sistema de oásis (BIT-06) existe mas não funciona como pretendido na prática. Sintomas reportados pelo developer: "as comidas do mapa não são renovadas e não tem nenhum input visual de que o oasis está funcional". Diagnóstico validado empiricamente (simulação headless de 180s, seed 42, dt=1/30 — detalhes em `research/simulation-core.md`):

- **Bug A — saturação do cap global de comida:** `Food` não tem TTL; comida não consumida de oásis já expirados fica no mapa para sempre. Aos ~30s o mapa atinge `MAX_TOTAL_FOOD = 50` e a renovação praticamente cessa (~5 comidas novas em 150s de simulação).
- **Bug B — Jardim do Éden ignora o cap de oásis:** `MAX_ACTIVE_OASES = 4` só limita o spawn natural; o Éden faz `append` sem teto e, com a população oscilando por fome (consequência do Bug A), redispara em loop — observados 13 oásis simultâneos.
- **Gap C — zero feedback visual:** `get_state()["oases"]` já é enviado via WebSocket, mas `SimulationCanvas.jsx` não desenha nada.

Corrigir A e B e implementar C.

## Abordagem técnica

Comida passa a apodrecer: `Food` ganha `ttl` (constante `FOOD_TTL = 30.0`s) decrementado em `engine.step()`; ao expirar, é removida via `consume()` (reaproveita a remoção do corpo Pymunk e o filtro `is_active` já existentes) — isso libera o cap global e restaura a renovação contínua. Um teto duro `MAX_TOTAL_OASES = 10` passa a valer inclusive para o Éden. No frontend, os oásis são desenhados como círculos com gradiente radial verde translúcido entre o fundo e as criaturas, com opacidade proporcional ao TTL restante — para isso `Oasis.to_dict()` ganha o campo aditivo `ttl_fraction`.

**Dependência/conflito com BIT-17 (Ambiente Aquático, em refinamento paralelo):** BIT-17 também modifica `SimulationCanvas.jsx` (remove o desenho de `fundo.png` e muda o fundo para gradiente azul). Não há dependência lógica, mas quem implementar por último resolve merge nesse arquivo. Por isso o passo 5 ancora o desenho do oásis em "imediatamente antes do bloco `data.creatures`", que existe nas duas versões — **não** ancorar no bloco do `fundo.png`.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/food.py` | modificar | constante `FOOD_TTL = 30.0`; atributo `self.ttl = FOOD_TTL` no `__init__` |
| `backend/simulation/oasis.py` | modificar | constante `MAX_TOTAL_OASES = 10`; `self.ttl_initial` no `__init__`; `to_dict()` ganha `"ttl_fraction"` |
| `backend/simulation/engine.py` | modificar | bloco de expiração de comida no `step()`; Éden respeita `MAX_TOTAL_OASES` |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | bloco `data.oases.forEach(...)` com gradiente radial, antes do bloco de criaturas |
| `backend/tests/test_oasis.py` | modificar | novos testes: expiração de comida, renovação contínua pós-saturação, teto do Éden |

## Passos de implementação

> Passos 1 e 2 são independentes entre si; 3 depende de 1 e 2; 4 depende de 2; 5 depende de 4 (campo novo no payload); 6 depende de 1-4.

1. **`backend/simulation/food.py`** — TTL da comida:
   ```python
   FOOD_TTL = 30.0  # segundos ate a comida apodrecer e liberar vaga no cap global
   ```
   e no `__init__`, junto de `self.is_active = True`:
   ```python
   self.ttl = FOOD_TTL
   ```
   Não alterar `to_dict()` (o frontend não precisa do TTL da comida nesta task).

2. **`backend/simulation/oasis.py`** — teto duro e fração de TTL:
   ```python
   MAX_TOTAL_OASES = 10  # teto duro, vale inclusive para o Jardim do Eden
   ```
   No `__init__`, após a linha que define `self.ttl`:
   ```python
   self.ttl_initial = self.ttl
   ```
   E `to_dict()` passa a ser:
   ```python
   def to_dict(self):
       return {
           "x": self.x, "y": self.y, "radius": self.radius, "ttl": self.ttl,
           "ttl_fraction": max(0.0, self.ttl / self.ttl_initial),
       }
   ```

3. **`backend/simulation/engine.py`** — expiração de comida. Importar `FOOD_TTL` não é necessário (o TTL já nasce dentro de `Food`). Inserir imediatamente **antes** do bloco "1. Ciclo de vida dos oasis" em `step()`:
   ```python
   # 0.5. Comida apodrece: TTL libera vaga no cap global (MAX_TOTAL_FOOD), sem isso
   # comida orfa de oasis expirados satura o mapa e a renovacao para (BIT-18).
   for food in self.foods:
       food.ttl -= dt
       if food.ttl <= 0 and food.is_active:
           food.consume()
   ```
   O filtro existente `self.foods = [f for f in self.foods if f.is_active]` (bloco 5) já remove as expiradas da lista.

4. **`backend/simulation/engine.py`** — teto do Éden. Adicionar `MAX_TOTAL_OASES` ao import de `simulation.oasis` e trocar o loop do Éden (bloco 6) por:
   ```python
   for creature in self.creatures:
       if len(self.oases) >= MAX_TOTAL_OASES:
           break
       self.oases.append(Oasis(
           creature.body.position.x, creature.body.position.y,
           radius=EDEN_OASIS_RADIUS, ttl=EDEN_OASIS_TTL, food_cap=EDEN_OASIS_FOOD_CAP,
       ))
   ```
   A flag `self._eden_active` (histerese) fica inalterada.

5. **`frontend/src/components/SimulationCanvas.jsx`** — desenhar oásis. Inserir imediatamente **antes** de `if (data.creatures) {` (dentro do bloco escalado do mundo — não ancorar no bloco do `fundo.png`, que a BIT-17 remove):
   ```jsx
   // Oasis: zona de fertilidade, atras de tudo que e vivo/comestivel.
   // Opacidade cai junto com o TTL (fade-out natural antes de expirar).
   if (data.oases) {
     data.oases.forEach(oasis => {
       const frac = oasis.ttl_fraction ?? 1;
       const grad = ctx.createRadialGradient(oasis.x, oasis.y, 0, oasis.x, oasis.y, oasis.radius);
       grad.addColorStop(0, `rgba(80, 200, 120, ${0.10 + 0.15 * frac})`);
       grad.addColorStop(1, 'rgba(80, 200, 120, 0)');
       ctx.fillStyle = grad;
       ctx.beginPath();
       ctx.arc(oasis.x, oasis.y, oasis.radius, 0, Math.PI * 2);
       ctx.fill();
     });
   }
   ```

6. **`backend/tests/test_oasis.py`** — novos testes (seguir o padrão dos 9 existentes: `SimulationEngine` real, `random.seed`/monkeypatch para determinismo):
   - **Comida expira:** adicionar uma `Food` manualmente, rodar `step()` até acumular mais de `FOOD_TTL` segundos simulados → `is_active == False` e fora de `engine.foods`; corpo removido do space (mesma verificação usada nos testes de consumo, se houver).
   - **Renovação pós-saturação:** popular `engine.foods` com `MAX_TOTAL_FOOD` comidas manualmente, com um oásis ativo de `ttl` alto; rodar `step()` por mais de `FOOD_TTL` segundos simulados (forçando spawn com monkeypatch em `random.random`) → o total de comidas criadas desde o início cresce (novas nasceram após as antigas apodrecerem).
   - **Teto do Éden:** `engine.oases` pré-populado com `MAX_TOTAL_OASES - 2` oásis e 5 sobreviventes (população `< 10`) → após `step()`, `len(engine.oases) == MAX_TOTAL_OASES` (só 2 adicionados), e a histerese continua funcionando.
   - **`ttl_fraction` no payload:** `Oasis(0, 0, ttl=10.0)` recém-criado → `to_dict()["ttl_fraction"] == 1.0`; após decrementar `ttl` para 5.0 → `0.5`; para `-1` → `0.0`.

## Contratos técnicos

### Backend (Simulação)
- `Food.ttl: float` — novo atributo, inicia em `FOOD_TTL = 30.0` (constante nova em `food.py`).
- `Oasis.ttl_initial: float` — novo atributo, congela o TTL de nascimento.
- `MAX_TOTAL_OASES = 10` — constante nova em `oasis.py`, teto duro para `len(engine.oases)` (spawn natural já respeitava `MAX_ACTIVE_OASES = 4`, que fica inalterado; o teto novo vale para o Éden).
- Nenhuma assinatura de método muda.

### API/WebSocket
- `state_update.oases[i]` ganha campo aditivo:
  ```json
  {"x": 512.0, "y": 300.0, "radius": 150.0, "ttl": 22.4, "ttl_fraction": 0.83}
  ```
  Retrocompatível — nenhum campo removido ou renomeado.

### Frontend
- `SimulationCanvas.jsx` consome `data.oases` do `state_update` (WebSocket `ws://localhost:8001/ws`), com fallback `ttl_fraction ?? 1`.

## Critérios de aceite

- [ ] Comida expira após `FOOD_TTL` segundos simulados e sai de `engine.foods` (corpo removido do space Pymunk).
- [ ] Renovação contínua: re-rodando o diagnóstico headless de 180s (`research/simulation-core.md`), o total acumulado de comidas criadas cresce continuamente (ordem de centenas, não ~56 como hoje).
- [ ] `len(engine.oases) <= MAX_TOTAL_OASES` em todos os frames, inclusive com o Éden disparando repetidamente.
- [ ] Oásis visíveis no canvas como manchas verdes translúcidas que esmaecem conforme o TTL cai e somem ao expirar.
- [ ] `state_update.oases[i].ttl_fraction` presente, em `[0, 1]`; payload retrocompatível.
- [ ] `pytest backend/tests/` 100% verde (novos testes + nenhuma regressão nos 9 existentes de `test_oasis.py`).
- [ ] Simulação completa roda sem erro (`manager.py` → Start Tudo) com comida visivelmente nascendo e apodrecendo dentro dos oásis.

## Rollback

Reverter `backend/simulation/food.py`, `backend/simulation/oasis.py`, `backend/simulation/engine.py` e `frontend/src/components/SimulationCanvas.jsx` (git checkout); remover os testes novos de `backend/tests/test_oasis.py`. Sem estado persistente/migração envolvida.
