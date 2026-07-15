# Review Report (delta) — BIT-21: correcao dos 2 testes flaky

Revisao FOCADA do delta em `backend/tests/test_food_and_mate_seeking.py`. O codigo de
producao ja fora aprovado em `review-report.md`; aqui so confirmo a estabilizacao dos
dois testes de comportamento que eu havia marcado como [MELHORIA]/flaky.

## Veredito
APROVADO

## Escopo do delta (confirmado)
- Unico arquivo tocado nesta correcao: `backend/tests/test_food_and_mate_seeking.py`
  (mtime 07:59, posterior a todos os arquivos de producao; impl-report-fix as 08:00).
- Nenhum codigo de producao foi alterado neste delta. As mudancas em
  `rtneat_wrapper.py` / `sensors.py` / etc. sao o trabalho de producao ja aprovado
  antes, nao parte desta correcao.

## Resultado dos gates (rodados por mim)
- `import main`: OK
- Rodadas repetidas dos 2 testes (10x em laco de shell): **10/10 verde** (flakiness eliminada).
- Suite completa `pytest tests/ -q`: **115 passed / 1 failed**.
  - Unica falha: `test_exploration_pressure.py::test_newborn_still_has_to_eat_before_mating`
    — PRE-EXISTENTE e FORA DE ESCOPO (arquivo untracked, invariante de BIT-20). Nada novo quebrou.

## Achados

### [OK] Determinismo
`random.seed(42)` no inicio de cada teste + laco de `SAMPLE_SIZE=200` amostras torna o
resultado deterministico. 10 rodadas isoladas consecutivas: 100% verde.

### [OK] Os testes NAO viraram tautologicos — pegam a regressao real (verificado empiricamente)
Medi a fracao de sucesso em dois regimes:
- Com as sementes (estado correto atual): **0.98 / 0.98** para mate / partner -> passa com folga.
- SEM as sementes (emulando a regressao: zerando os pesos food-taxis e o bias de Action_Mate
  e reconstruindo a net): **0.545** (mate) e **0.46** (partner) -> AMBOS abaixo de 0.85 -> os
  testes FALHARIAM. Bate com o ~47-56% previsto e com o comentario de producao
  (`rtneat_wrapper.py:67`: "com bias 0.0 so 56% ... disparam mate").
O limiar 0.85 fica limpo entre os dois regimes (0.98 vs ~0.5): pega a regressao sem falso-negativo.

### [OK] Robustez estatistica do limiar
Fracao real ~0.98 sobre N=200; desvio-padrao da estimativa ~0.01. Margem para 0.85 e enorme
(~13 desvios), entao 0.85 nunca falha por acaso mas fica bem acima do regime de regressao (~0.5).
Comentario em pt-BR no arquivo (linhas 124-129) explica corretamente a natureza probabilistica.

### [OK] Assercoes intra-amostra preservadas
Dentro do laco os invariantes fortes seguem checados a cada amostra:
`vision == [0.0]*9` (nada em vista) e `any(v>0)` em `vision[5:]` + `all(v>=0)` (parceiro atrativo,
sem sinal repulsivo). Nao foram diluidos pela agregacao estatistica.

### [OK] Sem hardcode / demais grupos intactos
`SAMPLE_SIZE` e `MIN_SUCCESS_FRACTION` sao parametros locais nomeados (literais de teste,
nao constantes de producao — correto). Imports de `rtneat_wrapper`/`sensors` seguem intactos.
Grupos 1, 3 e 5 inalterados; nenhuma constante magica duplicada.

## Resumo
Correcao APROVADA. Os dois testes viraram assercoes estatisticas deterministicas, sao verdes
10/10 em rodadas repetidas, e comprovadamente NAO sao tautologicos (com a semente removida a
fracao cai para ~0.5, abaixo do limiar 0.85, e o teste falharia). Nenhum codigo de producao
foi tocado. A task BIT-21 pode ser FECHADA (movida para implemented/), ressalvada apenas a
falha pre-existente de `test_exploration_pressure.py`, que e de outra task (BIT-20).
