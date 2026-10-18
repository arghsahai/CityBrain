# V2.6 controlled experiment methodology

## Existing reproducible experiment interfaces

The repository's established research runner uses matched SUMO inputs/seeds for
static versus dynamic policies and records failures, arrival, teleportation,
traffic effects and replanning latency. Its S05/S07 matrix and S08 results are
historical research records. The official 180 trials and their outputs are
preserved and were not regenerated for this V3 baseline.

For a new run, always use a new output directory. The standard Chennai runtime
also writes input hashes, seed, profile, software revision, traffic source and
terminal status. A local, fast demonstration (not the formal research runner) is:

```sh
./tools/run_chennai.sh --mode simulation --seed 17 --seconds-per-step 0 \
  --no-server --no-browser --exit-on-complete --output /tmp/v3-sim-seed17
./tools/run_chennai.sh --mode replay-assisted --seed 17 --seconds-per-step 0 \
  --no-server --no-browser --exit-on-complete --output /tmp/v3-replay-seed17
```

## V3.2 comparison protocol

The optional traffic evaluator must be tested on paired scenario seeds with
identical SUMO network, demand and incident inputs. Report separate arms for
static baseline, existing dynamic CityBrain, evaluator disabled and evaluator
enabled. Keep all arm outputs under a new versioned directory and include every
trial, including NO_ROUTE, timeout, teleport and execution failure. The evaluator
is currently an offline sidecar and is **not wired into route commitment**; results
from its ranking alone are not traffic-assisted routing or response-time evidence.

Pre-register the seeds, policy caps, matching/freshness thresholds and metrics.
Report denominators, paired differences, confidence intervals, route churn,
provider-match coverage, age distribution and failed observations. Simulation
time and wall time must remain separate. A SUMO teleport or missing vehicle is
never an arrival. Do not compare outputs with different demand or scenario inputs
as a causal experiment. No V3 formal matrix was run in this implementation stage.

## Historical integrity

The frozen 2,172-entry manifest is checked read-only by
`venv/bin/python -m citybrain.chennai.validate --historical`. This command must
pass before and after future trials. Never point a new experiment at the archived
official result directory.

The fresh seed-1 S05/S06/S08 static/dynamic smoke summary, machine-readable rows,
manifest and success-rate plot are in [`docs/chennai/v3-baseline-smoke/`](chennai/v3-baseline-smoke/).
