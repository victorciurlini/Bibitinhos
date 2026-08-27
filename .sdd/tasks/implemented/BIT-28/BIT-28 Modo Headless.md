# Spec — BIT-28: Modo Headless

**Linear:** N/A
**Risco:** low
**Camada(s):** Backend (Simulação) + Infra

**Depende de:** BIT-26 (usa `compute_metrics()` de `backend/simulation/metrics.py` para os snapshots)

---

## Demanda

Rodar a simulação sem frontend e sem servidor: um CLI que executa N ticks em velocidade máxima (sem sleep, sem asyncio), salva snapshots periódicos de métricas em JSON e imprime um resumo — viabilizando experimentos longos, benchmarks e uso em CI.

## Abordagem técnica

O engine já é 100% independente do FastAPI (`step()`/`get_state()` puros; os testes provam isso) — o que falta é empacotar: um `HeadlessRunner` síncrono em `backend/simulation/runner.py` que faz bootstrap da população (função reutilizada pelo `startup_event` do main.py, eliminando a duplicação) e roda um loop `for` puro, mais um entry point `backend/cli.py` com argparse. Snapshots usam `compute_metrics()` do BIT-26 (agregados leves, não o estado completo). `--seed` opcional dá reprodutibilidade: toda a aleatoriedade da simulação vem do módulo `random` da stdlib (verificado por grep — creature/engine/oasis/rtneat_wrapper; pymunk é determinístico), então `random.seed(seed)` basta.

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/simulation/runner.py` | criar | `populate()` + `HeadlessRunner` |
| `backend/cli.py` | criar | entry point argparse |
| `backend/main.py` | modificar | `startup_event` passa a usar `populate(engine, 10)` |
| `backend/tests/test_headless.py` | criar | testes do runner e reprodutibilidade |
| `docs/desenvolvimento.md` | modificar | seção "Modo headless" |
| `docs/arquitetura.md` | modificar | mencionar runner/CLI no mapa de módulos |

## Passos de implementação

1. **`backend/simulation/runner.py`:**
   ```python
   import random

   from simulation.creature import Creature
   from simulation.metrics import compute_metrics

   SIM_DT = 1 / 30.0  # mesmo dt fixo do simulation_loop (BIT-24: dt nunca muda)


   def populate(engine, count=10):
       """Bootstrap da populacao inicial (Gen 0)."""
       for _ in range(count):
           engine.add_creature(Creature(engine))


   class HeadlessRunner:
       """Roda o engine sem servidor: loop sincrono em velocidade maxima."""

       def __init__(self, initial_creatures=10, seed=None):
           if seed is not None:
               random.seed(seed)
           from simulation.engine import SimulationEngine
           self.engine = SimulationEngine()
           populate(self.engine, initial_creatures)

       def run(self, ticks, snapshot_interval=300, on_snapshot=None):
           """Executa `ticks` steps de SIM_DT; snapshot de metricas a cada
           `snapshot_interval` ticks (e um final). Retorna a lista de snapshots."""
           snapshots = [compute_metrics(self.engine)]  # tick 0
           for t in range(1, ticks + 1):
               self.engine.step(SIM_DT)
               if t % snapshot_interval == 0 or t == ticks:
                   snap = compute_metrics(self.engine)
                   snapshots.append(snap)
                   if on_snapshot:
                       on_snapshot(t, snap)
           return snapshots
   ```
   Import de `SimulationEngine` no `__init__` (após o seed) para o seed valer antes de qualquer aleatoriedade de construção. Se `t == ticks` coincidir com múltiplo do intervalo, não duplicar o snapshot final (usar `elif` ou checagem).
2. **`backend/cli.py`:**
   ```python
   """Runner headless: python cli.py --ticks 9000 --output run.json"""
   import argparse
   import json

   from simulation.runner import HeadlessRunner


   def main():
       parser = argparse.ArgumentParser(description="Bibitinhos headless")
       parser.add_argument("--ticks", type=int, default=9000, help="steps de 1/30s (9000 = 5 min simulados)")
       parser.add_argument("--creatures", type=int, default=10)
       parser.add_argument("--snapshot-interval", type=int, default=300, help="ticks entre snapshots (300 = 10s)")
       parser.add_argument("--seed", type=int, default=None)
       parser.add_argument("--output", type=str, default=None, help="arquivo JSON de saida")
       args = parser.parse_args()

       runner = HeadlessRunner(initial_creatures=args.creatures, seed=args.seed)

       def report(t, snap):
           print(f"tick {t}: pop={snap['population']} births={snap['births_total']} "
                 f"deaths={snap['deaths_total']} food={snap['food_count']}")

       snapshots = runner.run(args.ticks, args.snapshot_interval, on_snapshot=report)

       if args.output:
           payload = {
               "metadata": {"ticks": args.ticks, "initial_creatures": args.creatures,
                            "snapshot_interval": args.snapshot_interval, "seed": args.seed},
               "snapshots": snapshots,
           }
           with open(args.output, "w", encoding="utf-8") as f:
               json.dump(payload, f, indent=2)
           print(f"salvo: {args.output} ({len(snapshots)} snapshots)")


   if __name__ == "__main__":
       main()
   ```
   Executar de dentro de `backend/` (mesma convenção de imports do main.py/pytest): `venv\Scripts\python.exe cli.py --ticks 3000 --seed 42 --output run.json`.
3. **`main.py`:** substituir o loop de criação de criaturas no `startup_event` por `populate(engine, 10)` (import de `simulation.runner`). Nenhuma outra mudança no servidor.
4. **Testes (`test_headless.py`):**
   - `test_runner_basic`: `HeadlessRunner(seed=1).run(300)` termina, retorna ≥ 2 snapshots, campos do contrato de métricas presentes, `time` crescente.
   - `test_runner_snapshot_interval`: `run(300, snapshot_interval=100)` → 4 snapshots (tick 0, 100, 200, 300), sem duplicata no final.
   - `test_runner_deterministic`: dois runners com `seed=42`, `run(300)` cada → séries de snapshots idênticas (comparar listas).
   - `test_populate`: `populate(engine, 5)` adiciona 5 criaturas.
5. **CLI smoke (manual, no gate de qualidade):** `python cli.py --ticks 300 --seed 1 --output <scratch>\run.json` termina com exit 0 e JSON válido.
6. **Docs:** seção "Modo headless" em `desenvolvimento.md` (comando, flags, formato de saída); nota em `arquitetura.md`.

## Contratos técnicos

### Backend (Simulação)
- `populate(engine, count=10) -> None` e `HeadlessRunner(initial_creatures=10, seed=None)` com `run(ticks, snapshot_interval=300, on_snapshot=None) -> list[dict]` em `runner.py`.
- Snapshot = dict de `compute_metrics()` (contrato do BIT-26).
- Constante `SIM_DT = 1/30.0`.

### Infra
- Entry point: `backend/cli.py` (flags acima). Saída JSON: `{"metadata": {...}, "snapshots": [...]}`.

## Critérios de aceite

- [ ] `python cli.py --ticks 300 --seed 1 --output run.json` roda sem servidor/frontend, termina e gera JSON válido.
- [ ] Mesmo seed → snapshots idênticos (teste de determinismo verde).
- [ ] `startup_event` usa `populate()` e o servidor se comporta como antes (157 testes seguem verdes).
- [ ] Loop headless roda em velocidade máxima (sem `sleep`/asyncio).
- [ ] Testes novos verdes; `python -c "import main"` ok.

## Rollback

Reverter a branch BIT-28: deletar `runner.py`, `cli.py`, `test_headless.py`; restaurar `main.py` e docs.
