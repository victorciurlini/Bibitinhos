"""Runner headless (BIT-28): python cli.py --ticks 9000 --output run.json

Executa a simulacao sem servidor/frontend, em velocidade maxima, e salva
snapshots periodicos de metricas em JSON. Rodar de dentro de backend/
(mesma convencao de imports do main.py e do pytest).
"""
import argparse
import json

from simulation.runner import HeadlessRunner


def main():
    parser = argparse.ArgumentParser(description="Bibitinhos headless")
    parser.add_argument("--ticks", type=int, default=9000,
                        help="steps de 1/30s (9000 = 5 min simulados)")
    parser.add_argument("--creatures", type=int, default=10)
    parser.add_argument("--snapshot-interval", type=int, default=300,
                        help="ticks entre snapshots (300 = 10s)")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", type=str, default=None,
                        help="arquivo JSON de saida")
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
