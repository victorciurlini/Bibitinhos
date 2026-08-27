# Relatório de implementação — BIT-28 Modo Headless

## Status
CONCLUÍDO

## Passos executados
1. Leitura da spec e do estado atual de `main.py`, `metrics.py` e `engine.py` (via codegraph).
2. Verificação de fontes de aleatoriedade fora da stdlib em `backend/simulation/` (grep por `uuid|np.random|time.time|os.urandom`): nenhuma — confirma a premissa da spec de que `random.seed()` basta para reprodutibilidade.
3. Criação de `runner.py` (populate + HeadlessRunner), `cli.py` (argparse) e `test_headless.py`.
4. `main.py`: `startup_event` passou a usar `populate(engine, 10)`; import de `Creature` (que ficou morto) trocado por `from simulation.runner import populate`. Nenhuma outra mudança no servidor.
5. Docs: seção "Modo headless (BIT-28)" em `desenvolvimento.md`; linha do `runner.py`/`cli.py` no mapa de módulos de `arquitetura.md` + atualização da dívida "Não há modo headless, Docker nem CI" → "Não há Docker nem CI".
6. Gates: import, pytest completo, smoke do CLI com validação do JSON.

## Arquivos modificados
- `backend/simulation/runner.py` (novo) — `SIM_DT = 1/30.0`, `populate(engine, count=10)`, `HeadlessRunner(initial_creatures=10, seed=None)` com `run(ticks, snapshot_interval=300, on_snapshot=None) -> list[dict]`. Import de `SimulationEngine` dentro do `__init__`, após o seed, conforme a spec.
- `backend/cli.py` (novo) — entry point argparse com `--ticks/--creatures/--snapshot-interval/--seed/--output`; saída `{"metadata": {...}, "snapshots": [...]}`.
- `backend/main.py` — só o bootstrap: loop de 10 `add_creature(Creature(engine))` substituído por `populate(engine, 10)`; import ajustado.
- `backend/tests/test_headless.py` (novo) — 5 testes: `test_populate`, `test_runner_basic`, `test_runner_snapshot_interval`, `test_runner_deterministic`, `test_runner_on_snapshot_callback` (este último não estava listado na spec, mas cobre o contrato `on_snapshot` usado pelo CLI). Inclui fixture autouse `_preserva_random_global` (ver "Problemas encontrados").
- `docs/desenvolvimento.md` — nova seção "Modo headless (BIT-28)" (comando, tabela de flags, formato do JSON, API programática).
- `docs/arquitetura.md` — linha `runner.py` no mapa de módulos; dívida de "modo headless" removida da lista de limitações.

## Problemas encontrados
- **Flakiness pré-existente exposta em `test_oasis.py::test_oasis_expires_when_ttl_reaches_zero`.** Na primeira rodada completa da suíte esse teste antigo falhou (passou isolado). Causa raiz: o teste depende do stream do `random` GLOBAL — ele assume que nenhum oásis aleatório nasce (`OASIS_SPAWN_CHANCE_PER_FRAME`) durante 2 steps, o que é probabilístico. Como `HeadlessRunner(seed=...)` semeia o random global (design intencional da spec), os testes novos deslocavam o stream de forma determinística e o teste antigo passava a cair num spawn. Correção dentro do escopo (sem tocar testes antigos, sem enfraquecer nada): fixture autouse em `test_headless.py` que salva `random.getstate()` e restaura ao final de cada teste — o resto da suíte vê exatamente o stream que veria sem o BIT-28. **Ponto de atenção para o futuro:** o teste de oásis continua intrinsecamente flaky (qualquer mudança na ordem/quantidade de consumo do RNG em qualquer teste anterior pode expô-lo de novo); a correção definitiva seria monkeypatchar `OASIS_SPAWN_CHANCE_PER_FRAME = 0.0` nele, como `test_food_only_spawns_inside_active_oasis` já faz — fica como sugestão fora do escopo do BIT-28.
- **Determinismo confirmado**: nenhuma fonte de aleatoriedade fora do `random` da stdlib foi encontrada; `test_runner_deterministic` (dois runners com seed=42, séries de snapshots comparadas com `==`) passa. Não foi preciso relaxar o invariante.
- Desvio menor da spec: além de trocar o corpo do `startup_event`, removi o import agora morto de `Creature` em `main.py` (higiene da mesma mudança).

## Resultado dos gates
- `venv\Scripts\python.exe -c "import main"` → `OK - app importa`.
- `venv\Scripts\python.exe -m pytest tests/ -q` → **180 passed** (175 do baseline + 5 novos), 8 warnings (pré-existentes, de deps).
- Smoke do CLI: `cli.py --ticks 300 --seed 1 --output <scratch>\run-smoke.json` → exit 0, imprime `tick 300: pop=10 births=0 deaths=0 food=63`, JSON válido com `metadata` + 2 snapshots (tick 0 e tick 300), todos os campos do contrato de `compute_metrics()` presentes.

## Próximos passos
N/A (não bloqueado). Sugestão fora de escopo registrada acima (endurecer `test_oasis_expires_when_ttl_reaches_zero` com monkeypatch do spawn chance).
