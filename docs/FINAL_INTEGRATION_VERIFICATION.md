# Final integration verification

Verified 2026-10-07 using Python 3.13.5 and Eclipse SUMO 1.27.1.
Implementation and smoke-generating commit: `c811ae4761de5374e11bff04e973620c01f7e4d9`.
All six final runs recorded a clean working tree and execution source SHA-256
`c7b224e3eea782bcba634025fd5aec78aff26d6c1e181e0fcfda048ac1d9d544`.
Base/latest fetched origin/main: `3e85415071fd23d68c65b68bf341c2ced25de3db`.
Local main remains `e660ecd6abbf5fff391c4e09d51f645198df18ae`; it was not modified.

## Regression

Complete pytest: **227 passed** (baseline 181), including existing ScoreRecorder compatibility.
Command used in this environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/citybrain-readiness-pytest-deps venv/bin/python -m pytest -q -p no:cacheprovider
```

All ten standalone legacy scripts exited zero: test_ambulance_agent.py,
test_emergency_planner.py, test_hospital_agent.py, test_models.py,
test_plan_validator.py, test_police_agent.py, test_replanner.py,
test_route_scorer.py, test_signal_agent.py, test_traffic_agent.py.
They were run individually using `venv/bin/python` with bytecode disabled.
No existing assertions were removed; executor mocks now supply physical topology/position.

## Real SUMO smokes

All use normal demand, seed 1, default runtime policy, and existing scenario generation.
These are integration demonstrations, not statistical research results.

| Candidate source | Scenario | Terminal | Accepted revisions | Terminal time (s) | Verified travel time (s) |
|---|---|---|---|---:|---:|
| Topology | S05 | SUCCESS | P0, P1 | 335 | 34 |
| Topology | S06 | NO_ROUTE | P0, P1 | 316 | unavailable |
| Topology | S08 | SUCCESS | P0, P1 | 352 | 51 |
| Existing catalogue + topology fallback | S05 | SUCCESS | P0, P1 | 335 | 34 |
| Existing catalogue + topology fallback | S06 | NO_ROUTE | P0, P1 | 316 | unavailable |
| Existing catalogue + topology fallback | S08 | SUCCESS | P0, P1, P2 | 425 | 124 |

The catalogue S08 execution was:

| Plan | Acceptance time (s) | Verified physical remaining route |
|---|---:|---|
| P0 | 301 | E13, E5, E7, E23 |
| P1 | 311 | E5, E19, E11 |
| P2 | 316 | E5, E19, E27, E33, E30 |

P2 was discovered from live SUMO topology after catalogue routes became unusable;
no scenario route or timestamp was added to runtime code. The default topology mode
legitimately starts with another route and requires only one replan. We do not force
an unnecessary second replan or claim the two configurations are equivalent trials.

The saved-evidence verifier passed for both directories. It checked exact route-index
suffix read-back before each logical acceptance, consecutive revisions, actual arrival
events, final physical edge, no teleport for successful runs, advisory-only signals,
terminal event finality, input hashes and metric consistency. The smoke driver asserted
cleared runtime/replanner active plans, cleared registered routes and released reservations.
S06 establishes no path under the currently observed blocked topology; it does not establish
that the destination remains unreachable after future incident clearance.

## Evidence and reproduction

Follow [FINAL_INTEGRATION.md](FINAL_INTEGRATION.md) for commands and contracts.
Final raw outputs remain under `data/output/integration/final-topology-v1` and
`data/output/integration/final-catalog-v1`, separate from experiments.
[final-integration-evidence.tar.gz](final-integration-evidence.tar.gz) contains both final
output directories, structured decisions/executions/lifecycle records, input files,
verification results, pytest/legacy logs and the pre-change historical hash manifest.
Archive SHA-256: `1651c211117c5fc3a4c2cfa3ad7df47affe43dc9922ab7ccd9b604181d85d96e`.

Archive input provenance preserves original absolute paths. The verifier's input-hash
checks require those original paths; on another machine, reproduce into new directories
using the documented smoke commands, or compare archived input bytes to their recorded
hashes and the unchanged repository network XML. Do not edit the original evidence to
make it appear to have been generated on another machine.

Earlier development smokes were preserved in `/tmp/citybrain-final-integration-smoke-v1`
and `/tmp/citybrain-final-integration-catalog-v1`. They are exploratory outputs from
uncommitted code and are not the final evidence above.

## Ownership and historical integrity

All **2,172 files** recursively under experiments/results, including ignored archives,
match their pre-change sizes and SHA-256 hashes. No files were added or removed there.
The official 180 trials were not regenerated. No diff in planner, agents, models,
perception, simulation, experiments, or the ten root legacy scripts.

## Remaining limits

Single emergency; static hospital availability; bounded candidate search; cached static
lane permissions; conservative one-second-step arrival evidence; full evidence retained
in memory. This is a headless software/SUMO validation, not a new GUI acceptance test,
citywide calibration, multi-seed benchmark, physical signal controller or hardware demo.
Physical signal priority and hardware remain future work. Independent review remains
required; the PR is intentionally left unmerged.
