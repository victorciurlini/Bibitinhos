# BIT-21 — Correcao pontual: testes flaky em test_food_and_mate_seeking.py

## Status
CONCLUIDO

## Passos executados
1. Li a spec de correcao e o estado atual de `backend/tests/test_food_and_mate_seeking.py`.
2. Converti os dois testes flaky de "1 amostra deterministica" para "assercao estatistica
   deterministica sobre N amostras", conforme a correcao pedida:
   - `test_sated_adult_wants_to_mate_with_nothing_in_sight`
   - `test_ready_adult_turns_toward_partner`
3. Adicionei `import random` e fixei `random.seed(42)` no inicio de cada teste (reproducibilidade).
4. Defini parametros locais nomeados no arquivo de teste: `SAMPLE_SIZE = 200` e
   `MIN_SUCCESS_FRACTION = 0.85` (literais do teste, nao constantes de producao).
5. Cada teste agora gera 200 amostras, conta a fracao que satisfaz a propriedade
   (mate desejado / `motor_torque > 0`) e afirma `fraction >= MIN_SUCCESS_FRACTION`.
6. Deixei comentario curto em pt-BR explicando que a semente e probabilistica e por isso o teste
   e estatistico com limiar conservador.
7. Rodei o gate: arquivo do teste, 15 rodadas isoladas dos dois testes, e suite completa.

## Arquivos modificados
- `backend/tests/test_food_and_mate_seeking.py` — unico arquivo tocado. Import de `random`,
  bloco de parametros (`SAMPLE_SIZE` / `MIN_SUCCESS_FRACTION`) com comentario explicativo,
  e reescrita dos dois testes flaky como laco de 200 amostras com seed fixa e assercao de fracao.
  As assercoes intra-amostra (`vision == [0.0]*9`, sinais positivos/nao-repulsivos) foram
  preservadas dentro do laco. Nenhuma constante hardcodada — as importacoes de
  `simulation.rtneat_wrapper` / `simulation.sensors` seguem intactas.

## Problemas encontrados
- `pytest-repeat` (`--count`) nao esta instalado no venv. Usei um laco de shell (15 rodadas)
  como fallback, conforme previsto na spec.
- Nenhuma divergencia com a spec. Escopo respeitado: nao toquei em codigo de producao,
  em `test_exploration_pressure.py`, `engine.py`, `creature.py`, nem no restante do arquivo
  (grupos 1, 3-parcial e 5 permaneceram inalterados).

## Resultado dos gates
- `import main` -> `OK - app importa`
- `pytest tests/test_food_and_mate_seeking.py -v` -> **8 passed**.
- Rodadas repetidas (laco de shell, 15x rodando os DOIS testes flaky juntos):
  **RESULTADO: 15 passaram / 0 falharam de 15 rodadas** (flakiness eliminada).
- Suite completa `pytest tests/ -q` -> **1 failed, 115 passed**.
  A unica falha e a pre-existente e fora de escopo:
  `test_exploration_pressure.py::test_newborn_still_has_to_eat_before_mating`.

## Proximos passos
Nenhum — correcao concluida. A falha remanescente de `test_exploration_pressure.py` e
pre-existente e explicitamente fora do escopo desta task.
