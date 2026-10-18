# CityBrain V3.1 preregistered simulation protocol

Protocol ID: `v31-matched-sumo-10seed-20261018`  
Registered before execution: 2026-10-18  
Output: `data/output/v3-experiments/v31-matched-sumo-10seed-20261018/`

## Research question

Across three supported synthetic blockage scenarios, how do the existing
static-plan and dynamic CityBrain policies compare on completion status,
teleportation and successful-run response time under matched seeds and identical
normal-demand inputs?

This is a SUMO harness study. It does **not** test the V3 traffic evaluator as a
route-selection strategy: that evaluator is an advisory sidecar and has no
verified route-execution integration. It does not test genuine external traffic,
signal priority actuation or live GPS.

## Design and fixed inputs

- Scenarios: `S05`, `S06`, `S08` as implemented in
  `experiments/runners/compare.py`.
- Profile: `normal`.
- Matched seeds: integers 1 through 10 in every scenario and policy arm.
- Arms: `static` and `dynamic`, the two implemented policies in this runner.
- Network, demand, scenario construction, horizon and policy are the checked-in
  implementation at the recorded run revision. Static and dynamic arms are
  paired by scenario/profile/seed; generated input hashes are retained by the
  runner manifest.
- Observation provenance: synthetic SUMO simulation only. No provider API calls
  or replay observations feed this harness.
- Planned matrix: 3 × 10 × 2 = 60 trials. Every attempted arm remains in the
  denominator, including failures.

## Outcomes and analysis

Primary outcome is terminal completion status, with completion rate and
teleportation rate reported over all attempts. Secondary outcomes are response
time (only for SUCCESS), replanning latency, planner computation, route changes,
and recorded reasons/statuses. For paired response-time differences, include only
matched pairs where both arms succeeded and report the available-pair count;
otherwise state that a pairwise travel-time comparison is unavailable. Report
each scenario separately, not as independent pooled evidence. Give Wilson 95%
intervals for completion and teleportation proportions. For successful paired
differences give median, mean and bootstrap 95% interval with the seed as the
resampling unit. Preserve every terminal status including `SUCCESS`,
`TELEPORTED`, `NO_ROUTE`, `TIMEOUT`, and `ERROR`. No result supports a real-world
or general superiority claim.

## Exclusions and reproducibility

No post-hoc trial exclusion is permitted. Invalid or missing outputs are retained
as recorded failures and explained. Do not overwrite or resume a prior directory.
The official historical 120-trial and 60-trial datasets and all 2,172 historical
evidence entries are outside the output path and must remain unchanged.

Exact command:

```sh
./venv/bin/python -m experiments.runners.compare \
  --scenarios S05 S06 S08 --profiles normal \
  --seeds 1 2 3 4 5 6 7 8 9 10 \
  --output data/output/v3-experiments/v31-matched-sumo-10seed-20261018
```

After execution, write results and analysis into this same new output folder,
along with this protocol, the final Git revision, runner manifest, exact command,
per-trial logs and a machine-readable summary. Do not regenerate the official
research result folders.
