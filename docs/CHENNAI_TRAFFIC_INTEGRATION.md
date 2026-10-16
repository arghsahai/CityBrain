# Chennai traffic integration — V2.1 Phase A gate

**Update:** the subsequent [Chennai stability hotfix](CHENNAI_STABILITY_FIX.md) is
implemented and ready for independent review. The blocked-stage findings below
describe the pre-fix baseline and are retained as audit history. No HERE/TomTom
integration has been started; provider work still awaits independent stability sign-off.

**Status: BLOCKED by baseline route-selection instability.** No live-provider
implementation, network request, API charge, planner change or SUMO control change
was introduced in this stage. The existing demonstration still executes and arrives
successfully. Passing arrival/execution checks does not establish route stability.

## Architecture and scope

Existing architecture remains OSM → SUMO → Core → agents/planner/replanner → verified
route execution, with file-only telemetry → GET-only server → Cesium. The current
`traffic_providers.py` contains an offline replay adapter and HERE/TomTom placeholders.
They remain unchanged. External observations stay outside authoritative SUMO costs.

The requested next architecture is a normalized, read-only provider boundary with
geometry/direction matching, freshness and separate dashboard overlays. It must wait
until Phase A's stability requirement is resolved and independently validated.

## Blocking evidence

The saved seed-17 run contains nine accepted plans. Every acceptance has a preceding
successful physical execution/read-back. Eight replans are real. However, seven
replans at 61, 71, 91, 97, 125, 145 and 167 simulation seconds alternate between two
future corridors while sharing the path through edge `-1309011039#20`.
Six acceptances return to a previously selected suffix. These are distinct routes,
not identical-route no-op calls. The recorded finite improvements vary, so this
audit does **not** assert equal scores or prove a counterfactual travel-time loss.

Two overrides explain a concrete stability risk:

| Time | Invalidated edge | Vehicle count | Mean speed | Explicit blockage | Time since acceptance |
|---:|---|---:|---:|---|---:|
| 91 s | `30424374#14` | 1 | 0 m/s | No flag | 20 s |
| 97 s | `-1309011039#14` | 1 | 0 m/s | No flag | 6 s |

Core's existing contract maps stopped traffic to infinite travel time
(`core/traffic_perception.py:115`). Plan validation calls this `unreachable_edge`.
The configured invalid-route override then permits immediate replanning and bypasses
timing gates (`planner/replanning_policy.py:88`). At 97 s, the actual six-second
interval is below the runtime's ten-second minimum commitment. The decision's timing
booleans are true because the override explicitly bypasses the gates; they are not
proof that ten seconds elapsed. No persistent closure or physical disconnection is
recorded for either invalidated edge. The scenario's 90-s speed restriction targets
a different edge, `30424374#0`.

The oscillation audit reports `OSCILLATION_REVIEW_REQUIRED`. This is a failed
stability sign-off for V2.1, not a claim that SUMO arrival or route read-back failed.
The prior count of eight genuine replans alone was insufficient to validate stability.

## Smallest compatible correction to investigate

Keep the canonical measurements, teammate scoring/policy and research scenarios
unchanged. Add an **opt-in Chennai runtime acceptance guard** that distinguishes
temporary measurement-driven cost changes from explicit blockage, broken topology,
permission loss or execution inconsistency. Require a consistent proposed future
corridor and persistent improvement across a configurable observation window for
soft-cost changes. Record observations, deferrals, duration and acceptance reasons.

Genuine hard failures must still bypass the soft stability guard. Keep verified
execution before acceptance, read-back reconciliation, NO_ROUTE semantics, arrival,
teleportation and cleanup. Do not solve the issue by hiding revision history,
changing stopped readings to invented finite costs, or disabling safety overrides
globally. Increasing the commitment interval alone cannot address an override that
bypasses it. Timing/persistence thresholds need calibration rather than an assertion
that an arbitrary new threshold fixes all traffic conditions.

This correction is proposed, **NOT IMPLEMENTED**. Its validation should cover
alternating near-equivalent costs, transient stopped readings, lasting congestion,
explicit blockage, legal physical diversions, NO_ROUTE and terminal cleanup. Repeat
the same seeded Chennai demonstration and compare decisions before starting providers.

## HERE / TomTom setup, environment and costs

The existing placeholders do not implement HTTP requests and do not consume
`HERE_API_KEY` or `TOMTOM_API_KEY`. No setup/coverage success is claimed. Environment
credentials were not inspected or used during this blocked stage. Future adapters
must return NOT_CONFIGURED for absent keys and must not log credential-bearing URLs.
Live requests, usage plans, cost authorization, quotas and coverage remain unverified.
No billable requests were initiated. Official endpoint/field implementation work is
deferred by the user's Phase A gate.

## Replay, road matching and freshness

The existing synthetic traffic fixture is labeled REPLAY and existing GPS data is
GPS_REPLAY. The current traffic replay adapter checks an explicit segment-to-edge
table and a 30-m point-to-road distance, and labels age/freshness. It has **no**
direction-aware, full-segment, ambiguity-rejecting matcher and does not meet the new
Phase F requirements. It also does not implement the requested four-state freshness
classification or a normalized live/replay schema with retrieval timestamps.
These limitations must not be described as implemented V2.1 functionality.

The existing dashboard distinguishes SUMO_SIMULATED observations, REPLAY fixtures
and UNAVAILABLE data. Its LIVE_OBSERVATION mode denotes watching current SUMO files;
it does not establish live Chennai traffic coverage. The requested REAL-WORLD
TRAFFIC DATA panel and separate live/replay road layers have not been added.

## Reproduction commands

```sh
# Existing baseline, no external API requests:
./tools/run_chennai.sh

# Fresh baseline verification, separate from official research results:
./tools/run_chennai.sh --seconds-per-step 0 --no-server --no-browser \
  --output data/output/chennai/a-new-phase-a-run

# Independent execution/geography/signal/historical audit:
venv/bin/python -m citybrain.chennai.validate --historical \
  --run data/output/chennai/a-new-phase-a-run

# Future-suffix oscillation and execution-order audit:
venv/bin/python tools/audit_chennai_replans.py \
  data/output/chennai/a-new-phase-a-run/runtime/events.jsonl \
  --output /tmp/chennai-replan-audit.json

venv/bin/python -m pytest -q

# Existing recorded replay and browser verification:
./tools/run_chennai.sh --mode replay --no-browser --port 8772 \
  --events data/output/chennai/final-paced
venv/bin/python tools/check_chennai_browser.py \
  --url http://127.0.0.1:8772 --output /tmp/chennai-browser-audit
```

Use a fresh output directory for each simulation; these commands do not regenerate
official experiments. Stop the replay server with Ctrl-C.

## Future advisory planning boundary

Once stability passes, implement and mock-test HERE/TomTom normalization, bounded
timeouts, rate-limit/error handling, retrieval/source timestamps and missing-data
states. Validate segment geometry and direction, reject ambiguous matches, classify
freshness, and display source-specific observations separately. Only a genuine,
authorized provider response inspected for this study area can establish coverage.
Any later assimilation policy must specify units, matching quality, freshness,
calibration, conflicting observations, provenance and a SUMO fallback. V2.1 external
observations must remain advisory; traffic-assisted planning needs separate validation.

Detailed audit report: [CHENNAI_V21_REPORT.md](CHENNAI_V21_REPORT.md).
