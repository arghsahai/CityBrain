# CityBrain V3.1 baseline audit

Audit date: 2026-10-18  
Repository: `arghsahai/CityBrain`  
Branch: `feature/citybrain-v3-roadmap`  
Starting revision: `368a83c041e171f664b8bb156b785aeedd4f9d65`

## Git and delivery state

The working tree was clean before this audit. Local `HEAD` matched
`origin/feature/citybrain-v3-roadmap`; `origin/main` was an ancestor of the
branch at `671568e0bddd12ad43ffd8d255aa936d662ecb22`. GitHub PR #10 is open,
Draft, targets `main`, and contains the four V3 foundation commits. No teammate
changes or unpublished local commits were present.

## Architecture observed in code

The existing default runtime is `citybrain.main.CityBrainRuntime`: Core owns the
TraCI connection and observed `CityState`; the existing agents, planner,
validator, replanner and `RouteExecutor` produce and verify physical route
changes. Chennai-specific orchestration in `citybrain/chennai/run.py` builds a
separate SUMO input/output run, wraps the runtime with the 20-second soft-change
guard in `citybrain/chennai/stability.py`, starts optional telemetry/dashboard
services, and shuts down the traffic service, TraCI and HTTP server in `finally`.
External observations flow through provider adapters, normalization,
`RoadMatcher`, freshness classification and `TrafficService`; the service reports
`applied_to_sumo=False`. The dashboard consumes persisted telemetry and is not
part of the planning control path. The browser uses Cesium when available and a
static SVG/dashboard fallback otherwise.

## Implemented and verified at baseline

- HERE and TomTom adapters, normalized traffic models, replay provider,
  freshness policy, stream/cache ordering, quarantine and directed geographic
  matching are present. Provider adapters are not configured in this checkout.
- `citybrain/chennai/traffic/evaluation.py` is a separate, default-disabled
  evidence/cost sidecar. It checks provenance, source/retrieval time, direction,
  matching status, confidence and coverage, and caps edge/route adjustments. It
  does not call the planner/executor or mutate shared measurements. It does not
  yet provide the complete candidate-decision protections requested for V3.1.
- SUMO phase/link telemetry is observed; dashboard recommendations are marked
  advisory. There is no validated emergency movement/phase-transition policy,
  minimum-green contract or restoration controller.
- Browser location is opt-in and tab-local, stops on user action, and never enters
  routing. There is no local GPS runtime endpoint or persisted location feed.
- Chennai OSM-derived SUMO network, hospital access-road targets, moving vehicles,
  route/read-back evidence, simulated signals, replay and dashboard telemetry are
  available. Hospital availability and driveway access are not clinically or
  physically verified.
- Provider credentials are readiness-checked without network requests. A
  separate manual verification command requires explicit authorization; no
  provider request was made during this audit.
- Existing historic research data is protected by the read-only validator.

## Not verified or not implemented at baseline

No genuine HERE/TomTom response, corridor coverage, accuracy, pricing or
operational outage behavior has been established. Traffic-assisted route
execution is not implemented. Signal recommendations remain advisory and no
signal writes occur. The browser GPS marker is not a runtime vehicle feed. The
committed S05/S06/S08 seed-1 smoke is evidence for those exact runs only; it is
not a multi-seed performance result. The experimental evaluator is not a
candidate route execution strategy and must not be counted as one in an outcome
comparison. Production emergency-response readiness is outside the evidence.

## Baseline validation

- Full pytest suite: **437 passed** (`venv/bin/python -m pytest -q`).
- Ten top-level legacy compatibility scripts: **10/10 exit zero**.
- Frozen historical manifest: **2,172 / 2,172** entries, no missing/extra/hash/
  size mismatches (`venv/bin/python -m citybrain.chennai.validate --historical`).
- Fresh baseline SUMO run: recorded separately in the V3.1 completion report
  after the run exits; this audit does not infer success from process startup.

## Files and evidence owners

Primary code paths are `citybrain/chennai/run.py`, `stability.py`,
`traffic/{provider,here_provider,tomtom_provider,replay_provider,normalization,
matching,freshness,service,evaluation}.py`, `citybrain/core/`,
`citybrain/planner/`, `citybrain/integration/`, and `dashboard/cesium/`. Existing
V3 documentation and tests are preserved. New V3.1 experiments must use a fresh
`data/output/v3-experiments/<protocol-id>/` path and must not touch
`experiments/results/` or the 2,172-entry evidence manifest.
