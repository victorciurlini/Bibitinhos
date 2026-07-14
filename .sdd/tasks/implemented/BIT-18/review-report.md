# Review Report — BIT-18: Renovação de Comida e Visualização dos Oásis

## Veredito

**APROVADO COM RESSALVAS**

## O que foi verificado

- **Diff completo** (`git diff HEAD` — a implementação está no working tree do branch `BIT-18`, ainda não commitada; o branch aponta para o mesmo commit que `develop`) contra os passos 1-6 da spec:
  - `backend/simulation/food.py`: `FOOD_TTL = 30.0` e `self.ttl = FOOD_TTL` no `__init__`, exatamente como especificado. `to_dict()` intocado (correto, spec pede isso).
  - `backend/simulation/oasis.py`: `MAX_TOTAL_OASES = 10`, `self.ttl_initial = self.ttl` logo após a linha de `self.ttl`, `to_dict()` com `ttl_fraction` clampado em `max(0.0, ...)`. Bate com a spec linha a linha.
  - `backend/simulation/engine.py`: bloco "0.5" de expiração de comida inserido imediatamente antes do bloco "1. Ciclo de vida dos oasis" (âncora correta); `MAX_TOTAL_OASES` importado de `simulation.oasis`; loop do Éden agora tem `if len(self.oases) >= MAX_TOTAL_OASES: break` antes do `append`, histerese (`self._eden_active`) inalterada.
  - `frontend/src/components/SimulationCanvas.jsx`: bloco `data.oases.forEach` inserido logo após o `worldGradient.fillRect` (fundo do BIT-17) e antes de `if (data.creatures)`. Confirmei lendo o arquivo inteiro: a ordem real de desenho é fundo → **oásis** → criaturas (com cones de visão) → comida. Z-order correta, atrás de tudo que é vivo/comestível, sem conflito com o gradiente do BIT-17.
  - `backend/tests/test_oasis.py`: os 4 testes novos batem com o que a spec pede no passo 6.

- **Suíte de testes**: rodei `venv/Scripts/python.exe -m pytest tests/ -v` e depois `-q` para confirmar o exit code. **89 passed, 0 failed**, incluindo os 9 testes antigos de `test_oasis.py` (nenhuma regressão) e os 4 novos.

- **Qualidade dos testes novos** (não são tautológicos):
  - `test_food_expires_and_is_removed_after_ttl`: roda `FOOD_TTL*30+1` steps e confirma `is_active is False`, `food not in engine.foods` **e** `food.body not in engine.physics.space.bodies` — verifica identidade do objeto e remoção física real, não só contagem.
  - `test_food_renews_after_ttl_expiry_at_global_cap`: satura o cap global manualmente (50 `Food` dentro de um oásis de `ttl=1000`), força spawn determinístico via monkeypatch (`OASIS_SPAWN_CHANCE_PER_FRAME=0`, `OASIS_FOOD_SPAWN_CHANCE=1`), roda `(FOOD_TTL+2)*30` steps e afirma `len(engine.foods) > 0` **e** `not any(f in original_foods for f in engine.foods)`. Verifiquei manualmente a mecânica interna do `step()`: como o bloco 0.5 (expira) e o bloco 5 (filtra `is_active`) rodam no mesmo `step()`, as 50 comidas originais (mesmo TTL, criadas no mesmo instante) expiram e são removidas da lista *no mesmo frame*; só depois disso o spawn começa a repopular. O teste realmente prova identidade de objetos, não só contagem — cobre o cenário de regressão do Bug A.
  - `test_eden_respects_max_total_oases_cap`: pré-popula `MAX_TOTAL_OASES - 2` (8) oásis com `ttl=100` (não expiram no step) e 5 criaturas ADULT (mais sobreviventes do que as 2 vagas restantes), roda 1 step, confirma `len(engine.oases) == MAX_TOTAL_OASES` (exatamente 2 adicionados, não 5) e `_eden_active is True`. Isso força de fato o cenário de estouro descrito na spec (Bug B).
  - `test_oasis_to_dict_includes_ttl_fraction`: cobre 1.0 / 0.5 / clamp em 0.0 para `ttl` negativo.

- **Diagnóstico headless reproduzido** (seed 42, 10 criaturas iniciais, dt=1/30, 180s = 5400 steps), instrumentando `engine.add_food` para contar todas as `Food` criadas (não só `len(engine.foods)` final):
  ```
  t= 15s | foods_now=22 | oases_now= 3 | creatures=10 | foods_created_cum=22
  t= 30s | foods_now=50 | oases_now=10 | creatures= 3 | foods_created_cum=52
  t= 60s | foods_now=50 | oases_now= 4 | creatures=10 | foods_created_cum=102
  t= 90s | foods_now=50 | oases_now= 6 | creatures= 6 | foods_created_cum=154
  t=105s | foods_now=48 | oases_now= 4 | creatures= 1 | foods_created_cum=173
  t=120s | foods_now=32 | oases_now=10 | creatures= 9 | foods_created_cum=186
  t=150s | foods_now=50 | oases_now= 0 | creatures= 3 | foods_created_cum=238
  t=180s | foods_now=50 | oases_now= 9 | creatures= 8 | foods_created_cum=288
  ```
  **Total de `Food` criadas em 180s: 288** (vs. ~56 no diagnóstico original do research) — ordem de centenas, satisfaz o critério de aceite. Renovação contínua confirmada (cresce de forma sustentada até o fim, não estagna como antes).

- **Teto de oásis**: assertei `len(engine.oases) <= MAX_TOTAL_OASES` a cada um dos 5400 steps (não só no final). **Nenhuma violação encontrada**; o máximo simultâneo observado foi exatamente 10 (bateu no teto, nunca ultrapassou), inclusive nos instantes em que o Éden disparou repetidamente (t=30s, t=120s).

- **Frontend build**: `cd frontend && npm run build` — build limpo, sem erros/warnings (`vite v5.4.21`, 32 módulos, ~2.2s).

## Divergências da spec

Nenhuma divergência material. Duas observações cosméticas, sem impacto funcional:
- O comentário `# 0.5. Comida apodrece...` fica posicionado, no arquivo final, *depois* do bloco `# 1.5. Reproducao assexuada` (que já existia antes do bloco de oásis). A spec só exigia a âncora "imediatamente antes do bloco 1. Ciclo de vida dos oasis", o que foi respeitado — mas a numeração "0.5" após "1.5" no código-fonte é logicamente estranha de se ler (ordem de execução real é: física → 1.5 → 0.5 → 1 → ... → 6). Puramente estético.
- `test_eden_respects_max_total_oases_cap` confirma `_eden_active is True` após o primeiro step, mas não roda um segundo step para reconfirmar que a histerese barra novos `append`s mesmo com vaga sobrando. A cobertura desse comportamento já existe em outro teste mais antigo (`test_eden_does_not_retrigger_every_frame_while_population_stays_low`), então não é lacuna real, só não é 100% recombinada com o cap novo no mesmo teste.

## Riscos encontrados

1. **`ZeroDivisionError` real em `Oasis.to_dict()` se `ttl=0.0` for passado explicitamente ao construtor.** Testei isoladamente:
   ```python
   Oasis(0, 0, ttl=0.0).to_dict()  # ZeroDivisionError: float division by zero
   ```
   Motivo: `ttl_initial = self.ttl` congela o valor passado, e `to_dict()` faz `self.ttl / self.ttl_initial` sem guarda contra `ttl_initial == 0`. **Não é atualmente alcançável pelo código de produção** — busquei todas as chamadas `Oasis(` no repo: o spawn natural (`Oasis(x, y)`, `ttl=None` → sorteado em `[15,40]`) e o Éden (`ttl=EDEN_OASIS_TTL=30.0`, constante) nunca passam `0`. É uma fragilidade latente, não um bug em produção hoje — mas fica sem defesa caso algum código futuro (ou um teste) construa um oásis com `ttl=0` ou um valor que dependa de entrada externa. Recomendo um guard simples (`self.ttl_initial or 1.0`, ou tratar `ttl_initial <= 0` no `to_dict()`), mas não bloqueio a aprovação por isso já que não é exercitável pelo fluxo real do jogo.

2. **Interação `MAX_TOTAL_OASES` × `MAX_ACTIVE_OASES`**: verifiquei a lógica combinada, não só o bloco do Éden isolado. O spawn natural só age quando `len(self.oases) < MAX_ACTIVE_OASES` (4), valor bem abaixo do teto global (10); e ele roda *antes* do bloco do Éden no mesmo `step()`, então o Éden sempre vê o `len(self.oases)` já atualizado pelo spawn natural daquele frame antes de aplicar seu próprio guard. Não há caminho de overshoot combinado — confirmado também empiricamente pelos 5400 steps do diagnóstico headless sem nenhuma violação.

3. **Nenhum caminho de criação de `Food` contorna `__init__`.** Busquei todos os `Food(` do repo (produção e testes): todos passam pelo construtor normal, `ttl` sempre inicializado com `FOOD_TTL`. Sem risco de comida "órfã" sem TTL.

4. Nenhum problema encontrado na ordem de desenho do frontend (fundo → oásis → criaturas → comida, correto e sem conflito com BIT-17).

## Recomendação

Aprovar a implementação para merge em `develop`. Os 4 critérios de aceite verificáveis por mim foram todos confirmados empiricamente (expiração de comida, renovação contínua em ordem de centenas — 288 vs ~56 —, teto de oásis nunca violado em 5400 frames, payload com `ttl_fraction` retrocompatível, suíte 100% verde, build de frontend limpo). A única ressalva é o `ZeroDivisionError` latente em `Oasis.to_dict()` para `ttl_initial == 0`: sugiro abrir um follow-up de baixo risco (não bloqueante) para adicionar um guard, já que hoje nenhum caminho de produção o alcança.
