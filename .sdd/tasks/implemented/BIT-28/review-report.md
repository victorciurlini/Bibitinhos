# Relatório de revisão — BIT-28 Modo Headless

## Veredito
APROVADO

## Resultado dos gates (rodados pelo revisor)
- `import main`: OK (`OK - app importa`)
- `pytest tests/ -q`: **180 passed** — rodado 2x, ambos verdes (7.09s / 7.21s), 8 warnings pré-existentes de deps
- `pytest tests/test_headless.py tests/test_oasis.py -q` (encadeamento direto do ponto delicado): 18 passed
- Smoke CLI: `cli.py --ticks 120 --seed 7` → exit 0, imprime resumo do tick final
- Reprodutibilidade fim-a-fim: dois runs de `cli.py --ticks 300 --seed 42 --output ...` → `snapshots` byte-idênticos; JSON com `{"metadata": {ticks, initial_creatures, snapshot_interval, seed}, "snapshots": [...]}` e todos os 9 campos do contrato de `compute_metrics()` (BIT-26)

## Análise do desvio declarado (fixture de RNG)
O ponto mais delicado da revisão foi verificado em três frentes:
- **(a) Isolamento**: a fixture `_preserva_random_global` (`backend/tests/test_headless.py:13-20`) é `autouse=True` definida no próprio módulo — pytest aplica fixtures de módulo de teste apenas aos testes daquele módulo, e autouse cobre TODOS os 5 testes (inclusive `test_populate`, que consome o stream global sem seed). Salva `random.getstate()` antes e restaura via `random.setstate()` depois de cada teste — o resto da suíte vê exatamente o stream que veria sem o BIT-28.
- **(b) Ordem de coleta**: confirmado via `--collect-only` que `test_headless.py` é coletado antes de `test_oasis.py` (ordem alfabética); com a restauração por teste, o stream que chega em `test_oasis` é idêntico ao do baseline develop.
- **(c) Estabilidade**: suíte completa rodada 2x, 180 passed nas duas; par `test_headless` + `test_oasis` encadeado também verde.
Conclusão: o desvio é correto e minimamente invasivo (não toca testes antigos, não enfraquece asserts). O flaky de `test_oasis_expires_when_ttl_reaches_zero` é pré-existente e segue latente — ver melhorias.

## ERROS BLOQUEANTES
Nenhum.

## Conferências de aderência à spec (todas OK)
- `backend/simulation/runner.py` — `SIM_DT = 1/30.0`, `populate(engine, count=10)`, `HeadlessRunner(initial_creatures=10, seed=None)`, `run(ticks, snapshot_interval=300, on_snapshot=None) -> list[dict]`. Seed aplicado no topo do `__init__`, antes do import tardio de `SimulationEngine` e de `populate()` — toda aleatoriedade de construção fica sob o seed. Snapshot no tick 0, a cada intervalo e no final; a condição única `t % interval == 0 or t == ticks` faz um único `append` mesmo quando o final coincide com o intervalo (sem duplicata — coberto por `test_runner_snapshot_interval`: 300/100 → exatamente 4 snapshots).
- Loop 100% síncrono: `for` puro, sem `sleep`/asyncio.
- `backend/cli.py` — todas as flags da spec (`--ticks/--creatures/--snapshot-interval/--seed/--output`), formato JSON `{"metadata", "snapshots"}` conforme contrato.
- `backend/main.py:44,134-135` — `startup_event` usa `populate(engine, 10)`; única outra mudança é a troca do import morto de `Creature` por `populate` (desvio menor justificável — higiene da mesma mudança). Nenhuma outra alteração no servidor.
- Testes — os 4 da spec + `test_runner_on_snapshot_callback` (extra útil: cobre o contrato usado pelo CLI). Não são tautológicos: importam `SIM_DT` em vez de hardcodar, validam `time` esperado por snapshot, contrato de métricas via `METRICS_KEYS`, e o determinismo compara as SÉRIES COMPLETAS de dois runners (`snapshots_a == snapshots_b`), como pedido.
- Regressões — `engine.py`, `creature.py`, `metrics.py`, frontend e `test_oasis.py` intocados (verificado via `git diff 229d709`/`git status`). 180 = 175 do baseline + 5 novos.
- Docs — seção "Modo headless (BIT-28)" em `docs/desenvolvimento.md` (comando, tabela de flags, formato JSON, API programática); linha `runner.py` no mapa de módulos de `docs/arquitetura.md` e dívida atualizada para "Não há Docker nem CI".

## OPORTUNIDADES DE MELHORIA (não bloqueiam)
1. `backend/simulation/runner.py:38` — `snapshot_interval <= 0` causa `ZeroDivisionError` em `t % snapshot_interval` (o CLI aceita `--snapshot-interval 0` e quebraria com traceback cru). Sugestão: validar no CLI (`parser.error`) ou clampar/levantar `ValueError` com mensagem clara no `run()`.
2. `backend/tests/test_oasis.py::test_oasis_expires_when_ttl_reaches_zero` — segue intrinsecamente flaky (depende do stream global do `random`; qualquer mudança futura na ordem de consumo do RNG antes dele pode expô-lo de novo). Endurecer com `monkeypatch` de `OASIS_SPAWN_CHANCE_PER_FRAME = 0.0` (como `test_food_only_spawns_inside_active_oasis` já faz). Já registrado pelo implementer como fora de escopo — recomendo virar tarefa curta de higiene.

## Resumo
Implementação fiel à spec em contratos, CLI, bootstrap unificado e testes; determinismo confirmado fim-a-fim (testes + dois runs reais do CLI comparados) e o desvio da fixture de RNG é correto, isolado e estável em execuções repetidas. Pode fechar a task.
