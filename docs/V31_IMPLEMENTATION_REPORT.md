# CityBrain V3.1 implementation report

Date: 2026-10-18. This report describes a software research prototype, not an
emergency-response service.

## Architecture and feature state

| Capability | State in this branch | Can affect route execution? |
|---|---|---|
| OSM-derived Chennai road network and SUMO demand | Implemented; simulation verified | SUMO is the simulated physical truth |
| Existing CityBrain planner and verified RouteExecutor | Preserved; Core/planner code unchanged by V3.1 | Yes, through the existing runtime path |
| 20-second Chennai soft-change confirmation guard | Preserved | Gates soft replans; hard invalidations retain handling |
| HERE/TomTom/replay ingestion and normalization | Adapters and replay implemented; live credentials/responses absent | No |
| External-traffic evaluator and connected-candidate advisor | Opt-in; default off; freshness, match, direction, confidence, coverage, bounds, improvement, commitment, cooldown and route-history gates | No; display-only suggestion |
| SUMO signals | Phase/link telemetry and advisory suggestions | No signal-phase writes; priority controller disabled |
| Browser location | User-consented tab-local marker | No |
| Local GPS runtime feed | Not added; browser marker is sufficient for this demonstration | No |
| Cesium and SVG dashboard | Implemented; browser checks passed | Isolated from simulator correctness |
| Formal comparison study | 60 matched synthetic SUMO trials across S05/S06/S08, static/dynamic | Legacy planner arms only; not traffic-assisted |

The core control path is `CityBrainRuntime` → planner validation → verified
`RouteExecutor` → SUMO route read-back → logical plan acceptance. The data view
and experimental advisor are sidecars. Provider observations remain separate
from canonical `CityState` and planner costs.

```mermaid
flowchart LR
  OSM[OSM-derived Chennai network] --> SUMO[SUMO simulated vehicles and signals]
  SUMO --> CORE[CityBrain Core state]
  CORE --> PLAN[Existing planner and validation]
  PLAN --> EXEC[Verified RouteExecutor]
  EXEC -->|physical route read-back| SUMO
  SUMO --> TELE[Failure-isolated telemetry]
  TELE --> DASH[Cesium or SVG dashboard]
  HERE[HERE adapter] --> MATCH[Normalize, freshness, directed road match]
  TOMTOM[TomTom adapter] --> MATCH
  REPLAY[Synthetic/offline replay] --> MATCH
  MATCH --> SIDE[Opt-in traffic evaluator and route advisor]
  SIDE -->|advisory only| DASH
  SIDE -. no planner call or route commit .-> PLAN
  GPS[Consented browser location] -->|tab-local display only| DASH
```

## Validation evidence

Baseline revision was `368a83c041e171f664b8bb156b785aeedd4f9d65`; the branch was
clean, matched its origin ref and was based on `origin/main`. PR #10 is still
open and Draft, targeting `main`. Current branch: [`feature/citybrain-v3-roadmap`](https://github.com/arghsahai/CityBrain/tree/feature/citybrain-v3-roadmap).

| Milestone | Commit |
|---|---|
| Baseline audit | `37ebe9bc48f95608a641c9b03ff3fb73af63ae8f` |
| Preregistered experiment protocol | `08e5ac8b110dd22f28bb5af9225289f855f38623` |
| Opt-in advisory traffic route advisor | `07084687c093cdaabf2da4aa287167e30f9c9297` |
| Scenario-specific CSV aggregation fix and documented recovery | `9e1a9be610f3172c5185b61f4caad063c8309cb4` |
| Signal/GPS boundaries and browser checks | `46dd0ad96794c9b9306967e9c1dbc505ce7fe468` |
| Advisor oscillation history | `fa66b93ec8c439402edcda4148cad8b160e0783b` |
| Held-candidate label clarification | `1e73a600ce099cbcbefb654a3127b41df551b11a` |
| Results, per-trial logs and final documentation | `6cad0ff829a200da79d84ef7297a49901411d658` |

All listed commits were pushed and the checked remote branch head matched local
HEAD at verification. PR #10 remains available at
[`https://github.com/arghsahai/CityBrain/pull/10`](https://github.com/arghsahai/CityBrain/pull/10).
Its existing description still reflects V3.0: the Safari GitHub session was
signed out, and the GitHub connector was unavailable, so its body could not be
refreshed from this environment. The PR remains Draft and unmerged.

Final validation: **447 pytest tests passed**, all ten legacy compatibility
scripts passed, and `citybrain.chennai.validate --run` verified the fresh
runtime output. The read-only historical validator found **2,172 / 2,172**
entries with no missing, extra, hash or size mismatches. The preregistered
comparison contains all 60 planned trial cells after resuming preserved
per-trial checkpoints following an aggregation-only CSV schema fix. S05 static
was 7/10 SUCCESS versus dynamic 10/10; S06 was 0/10 in both arms (all
TELEPORTED); S08 static was 0/10 versus dynamic 10/10. Among seven S05 pairs
where both succeeded, response-time difference was 0 seconds. No successful
S06/S08 pairs existed. The 95% Wilson intervals are wide; do not interpret these
small synthetic results as proof of superiority. Outcomes and matched-success
uncertainty are in [`v31-analysis.md`](../data/output/v3-experiments/v31-matched-sumo-10seed-20261018/v31-analysis.md)
and its JSON companion. Per-trial result rows and losslessly compressed event
logs are retained beside them.

The checked-in seed-1 S05/S06/S08 baseline summary remains a smoke package, not a
formal effect estimate. Both a fresh seed-17 default simulation and a fresh
seed-17 opt-in replay-assisted advisor simulation reached SUCCESS at 704
simulated seconds (dispatch 51 s; 653 s travel), with zero telemetry/dashboard
write failures. In the opt-in run, 51 pre-plan evaluations returned NO_ROUTE and
653 post-plan evaluations kept the current route; all inputs were
`SYNTHETIC_SAMPLE`, no route was committed, and no evaluation failed. No eligible
sample measurement changed the candidate ranking in this run.

The browser replay review used Chrome 155 and recorded zero page errors. It
verified observed moving vehicles, route geometry, signal states, guarded KEEP,
synthetic traffic labels, external 3D/SVG overlays, selected-road comparison,
UNKNOWN/EXPIRED labels, closure markers `1 → 0 → 1`, future timestamp quarantine
and recovery, 800-pixel layout, and mocked advisor evidence rendered as
display-only against the fresh replay-assisted run. A separate replay check
observed the guarded KEEP and unchanged accepted P0. Mock fixtures do not
establish live provider behavior.

The network exposes two SUMO traffic lights and fixed programs with 4 and 14
controlled connection entries. Program phase `minDur`/`maxDur` values are unset;
there is no reviewed movement/phase compatibility, required all-red clearance,
or tested restoration contract. Priority remains advisory. The runtime GPS feed
was deliberately not added: the existing local consented marker suffices and
does not add a coordinate receiver or transport.

No HERE or TomTom API was called. Adapters are present but not live-verified;
coverage, accuracy, cost and account limits for a real VIT Chennai corridor are
unverified. Live traffic, clinical hospital capacity, real signal timing and
production safety remain external blockers.

## Reproduction commands

```sh
# Opt-in replay-assisted dashboard; uses local replay and no provider requests.
./tools/run_chennai.sh --mode replay-assisted --experimental-traffic-evaluation

# Fast headless simulation smoke in a fresh path.
./tools/run_chennai.sh --mode simulation --seed 17 --seconds-per-step 0 \
  --no-server --no-browser --exit-on-complete --output /tmp/citybrain-v31-sim
venv/bin/python -m citybrain.chennai.validate --run /tmp/citybrain-v31-sim

# Read-only historical integrity check.
venv/bin/python -m citybrain.chennai.validate --historical

# Preregistered ten-seed paired SUMO study (never run into experiments/results).
venv/bin/python -m experiments.runners.compare --scenarios S05 S06 S08 \
  --profiles normal --seeds 1 2 3 4 5 6 7 8 9 10 \
  --output data/output/v3-experiments/v31-matched-sumo-10seed-20261018
venv/bin/python tools/analyze_v31_experiment.py
```

The faculty presentation timing and offline fallback instructions are in
[`V31_DEMO_SCRIPT.md`](V31_DEMO_SCRIPT.md). Remaining viva questions are in
[`V31_VIVA_QA.md`](V31_VIVA_QA.md). Provider setup requires genuine credentials
and separate explicit authorization before any network request.
