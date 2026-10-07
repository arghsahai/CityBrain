"""Small runtime smokes, isolated from all historical experiment results."""
import argparse
import json
from pathlib import Path

from citybrain.main import run, RuntimeConfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenarios', nargs='+', choices=['S05', 'S06', 'S08'], default=['S05', 'S06', 'S08'])
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--candidate-source', choices=['topology', 'legacy-catalog'], default='topology')
    args = parser.parse_args()
    protected = Path(__file__).resolve().parents[2] / 'experiments/results'
    if args.output.resolve().is_relative_to(protected):
        parser.error('Choose an integration output outside experimental results')
    args.output.mkdir(parents=True, exist_ok=False)
    # Reuse the existing scenario generator; only writes to this fresh directory.
    from experiments.runners.compare import prepare_config
    routes = None
    if args.candidate_source == 'legacy-catalog':
        from citybrain.integration.state_adapter import CANDIDATE_ROUTES
        routes = CANDIDATE_ROUTES
    results = []
    failures = []
    for scenario in args.scenarios:
        config = prepare_config(args.output/scenario/'inputs', scenario, 'normal')
        runtime = run(config, output=args.output/scenario/'runtime', seed=args.seed, routes=routes,
            config=RuntimeConfig(topology_fallback=args.candidate_source == 'legacy-catalog'))
        finalized = (runtime.active_plan is None and runtime.replanner.active_plan is None and
                     not runtime.core._active_routes and not runtime.core.reserved_ambulances)
        row = {'finalized': finalized, 'scenario': scenario, 'seed': args.seed, 'candidate_source': args.candidate_source, **runtime.summary()}
        results.append(row)
        expected = 'NO_ROUTE' if scenario == 'S06' else 'SUCCESS'
        if row['terminal_outcome'] != expected or not finalized or row['evidence_failures']:
            failures.append(f"{scenario}: expected {expected} with finalized state and complete evidence")
        if scenario == 'S08' and args.candidate_source == 'legacy-catalog':
            if len(row['accepted_plans']) < 3:
                failures.append('S08: repeated-replan smoke did not exercise P2')
        print('SMOKE', scenario, row['terminal_outcome'], 'replans', row['route_changes'], flush=True)
    (args.output/'smokes.json').write_text(json.dumps(results, indent=2, allow_nan=False)+'\n')
    if failures:
        raise SystemExit('; '.join(failures))


if __name__ == '__main__':
    main()
