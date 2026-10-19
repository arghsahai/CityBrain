# V4.2 — HERE traffic to live recommendations

## Status and preservation

**IMPLEMENTED_OFFLINE. Engineering path READY_FOR_AUTHORIZED_PROVIDER_TEST, subject to the external gates below. Actual authentic access: BLOCKED_BY_LICENSING_OR_CREDENTIALS. NOT LIVE_VERIFIED.** No genuine HERE request was made. The safe status check currently reports NOT_CONFIGURED. Mocked/recorded responses are always REPLAY even if a key exists.

Branch `feature/citybrain-v42-here-traffic` starts from verified PR #12 head `d6592ace82e0ca9bec97ef8f2c221d4fb2bb5130`. Its Draft PR targets `feature/citybrain-v4-live-operations`, preserving PR #12 and avoiding a duplicate main-target diff. No main, PR merge, force push, teammate agent, validated SUMO control path, network/scenario or official research result changes.

## Architecture

```text
HERE v7 flow + incidents [DISABLED unless every gate is explicitly satisfied]
        or declared local HERE-format fixture / injected mock [REPLAY]
 → bounded session with independent flow/incident attempt counts
 → existing HTTP timeout / response-size / redirection / sanitized-error boundary
 → existing HERE normalizer (SI units, WGS84, sourceUpdated, individual shape links)
 → existing directed RoadMatcher + FreshnessPolicy + bounded last-valid cache
 → bidirectional longitudinal coverage check against actual pilot edges
 → eligible edge costs / closures, otherwise separate estimated fallback
 → existing TrafficAgent assessments + RouteScorer / PlanValidator + legal graph search
 → current-position reassessment and stability gates
 → operator review → recommendation ONLY
 → existing Cesium/SVG map with source, budget, speed, coverage and cost explanation
```

The backend worker polls and reassesses without requiring a browser. Snapshot reads never initiate HERE I/O; an outage or failed callback cannot block the simulation or become a dispatch action. The callback failure count is exposed without exception text. Session stop discards late ingestion and interrupts waits. Existing V3 Core → planner → RouteExecutor → physical SUMO read-back remains separate.

## Official interface and choices

Official references: [v7 overview](https://docs.here.com/traffic-api/docs/introduction-to-here-traffic-api-v7), [request setup](https://docs.here.com/traffic-api/docs/send-request-readme), [flow model](https://docs.here.com/traffic-api/docs/flow), [incident reference](https://docs.here.com/traffic-api/reference/traffic-api-v7-getincidents).

Fixed endpoints are `https://data.traffic.hereapi.com/v7/flow` and `/v7/incidents`. Queries use `in=bbox:west,south,east,north` and `locationReferencing=shape`. No HERE ID is treated as an OSM/SUMO edge ID. Each shape link remains separate; no synthetic lines bridge forks. Current and free-flow speed use the supplied metres-per-second values. Missing measurements remain null. Source update time is not represented as an individual sensor timestamp.

Flow confidence <=0.7 is historical/speed-limit-derived under HERE's model; this prototype conservatively excludes it and unknown confidence from observed flow costs. Supported closures and non-routable reversible flow can still invalidate an edge without inventing speed. Incident roadClosed/active roadClosure, explicit reopening/inactive state and source/update/end/start times are handled. Separate stream IDs preserve closure reopening; omission alone is not proof of reopening. Conflicting current closure streams remain conservatively blocked until explicitly cleared or expired.

**Deliberate limit:** heterogeneous `subSegments` are labelled unsupported for full-road costs instead of copying an aggregate speed onto each subsegment. Partial shape links covering less than 95% of an imported edge stay visible but cannot measure the entire edge. These conservative exclusions can leave most/all roads estimated on a genuine first response. Authentic coverage is an external verification gate, not assumed success.

## Cost and provenance policy

Only a fresh, directed, unambiguous MATCHED observation with >=95% coverage in both provider-to-network and edge-to-provider checks, inside the approved pilot area, may supply an edge cost. Freshness uses source time: FRESH through 120 s, STALE through 600 s, EXPIRED thereafter. More than 5 s future source time is quarantined before ordering. Last-valid observations survive outages with their original timestamps; fresh retained values may still inform costs, while stale/expired/unknown values cannot.

For an eligible speed, seconds = imported edge length / observed speed, scaled to the actual travelled fraction at route endpoints. No junction delay is invented. Speed 0 blocks that edge; values above 70 m/s are rejected as implausible prototype data. Explicit current closures block edges. Otherwise cost is imported length / imported speed limit, explicitly ESTIMATED_FREE_FLOW. This is an unvalidated decision-support cost model, not a field ETA or permission to exceed a legal speed. Provider/map disagreement requires field review.

Components retain source, observation ID/time, freshness, coverage and distance. `eta_provenance` reports observed/estimated metres and fractions, source timestamps, sources and field_validated=false. A route avoiding the only measured closure may have zero observed distance: the closure changed feasibility, but the alternative's timing is still entirely estimated. This is not relabelled as measured travel time.

The TrafficAgent receives supplied congestion categories (prototype thresholds 0.4/0.7), with original source times distinct from assessment time. Kept routes refresh their assessments and cost provenance rather than displaying old agent evidence. Reassessment re-scores the current route using current data, compares connected alternatives, and emits KEEP or RECOMMEND_ALTERNATIVE. Hard invalidation can bypass delay; soft alternatives retain the existing 60 s cooldown, >=30 s and >=10% improvement gate. New recommendations require operator review; approval uses the exact current ID and revalidation. Authenticated ambulance updates start the recommendation at the latest snapped position.

## Authorization, credentials and budget

Only server-side process environment `HERE_API_KEY` supplies a genuine credential. No key is sent to the browser, printed or committed. Readiness makes no network call:

```sh
venv/bin/python -m citybrain.live.here --status
```

A key alone never activates requests. Genuine network activation requires ALL of: explicit `--here` selection, `--authorize-here-requests`, `--here-license-confirmed`, explicit `--here-area WEST SOUTH EAST NORTH`, a positive `--here-max-requests`, and a configured key. These options are implemented for a separately authorized future test; **do not run them under this task's offline-only authorization**. There is no HTTP endpoint that can enable them.

The explicit bbox must remain within the retained pilot **[80.132,12.823,80.174,12.863]**. Total attempts are 0 by default, at most 100 per process; separate flow/incident caps may further restrict them. Every attempt is charged to the local counter BEFORE transport, including failed HTTP attempts. A flow+incidents poll can consume two transactions. No automatic HTTP retries, redirects, citywide fan-out or advanced paid feature requests are added. Polling is at least 60 seconds, session duration at most 900 seconds; 429/503 Retry-After is honoured. Budget/session exhaustion stops attempts. The counters are process-local safety caps, not a billing ledger; restarting is not authorization to spend another budget. Actual charge/quota rules depend on the user's HERE agreement.

Before the FIRST genuine request, obtain and record:

1. HERE account/product entitlement and explicit permission for this routing/tracking use, non-HERE map display and any permitted retention.
2. Applicable billing/quota/transaction definitions and approved monetary/request limits.
3. Separate explicit user authorization naming endpoints, exact bbox, expiry and maximum attempts. Suggested smallest check: **1 flow + 1 incident request, total 2**, no retries, only within the approved pilot; this is a proposal, not authorization.
4. A credential supplied privately through process environment or an approved secret store. Do not paste it into chat, source, URLs, commands or frontend code.
5. A bounded genuine-response validation plan for direction, source time, usable edge coverage, field plausibility and permitted evidence retention. Successful HTTP alone must not become LIVE_VERIFIED.

No HERE/TomTom/Google API or real emergency service was contacted here. Alternative adapters remain available for compatibility; HERE is primary for V4.2.

## Offline demonstration and dashboard

From the repository root, no API key needed:

```sh
V42_ROOT="$(mktemp -d /tmp/citybrain-v42.XXXXXX)"
venv/bin/python -m citybrain.live.here_demo --output "$V42_ROOT/demo"
```

The deterministic retained-network test uses actual pilot geometry and invented HERE-format conditions. Initial route: 70 edges, estimated 409.28802696573626 s. Closure of `-828326390#4` yields a legal 73-edge alternative, estimated 411.6587973041092 s and PENDING_OPERATOR_REVIEW. Reopening during cooldown yields KEEP. Source REPLAY / fixture provenance MOCKED_HERE; zero real flow/incident requests. A separate slow-flow test causes an alternative after the soft-change gate, not only through hard closure.

Serve the generated fixture in independent live-data mode (fresh test credentials/roles follow [V4 setup](V4_LIVE_DATA_SETUP.md)):

```sh
venv/bin/python -m citybrain.live --mode live --here-fixture "$V42_ROOT/demo/here-closed.json" --here-max-requests 2 --database "$V42_ROOT/state.sqlite" --port 8784
```

Open http://127.0.0.1:8784/?fallback=1 or `/` for Cesium. Configure a temporary operator token as in V4 setup, verify a TEST incident and place a USER_SELECTED ambulance. Provider label must be REPLAY, never HERE_LIVE. The file retains its original source time; old files legitimately become STALE/EXPIRED. Restarting does not refresh source timestamps. The fixture is a static captured test frame, not a continuously changing live provider.

Repeatable browser checks use disposable in-memory services and block external requests:

```sh
# Optional: venv/bin/python -m pip install playwright
venv/bin/python tools/check_here_browser.py --output "$V42_ROOT/here-browser"
venv/bin/python tools/check_live_browser.py --output "$V42_ROOT/v4-browser"
```

The HERE-specific check displays actual speeds/free-flow/congestion, matching/coverage/validation, provider accounting, route estimates/provenance/cost comparison, and closure overlays 1→0→1. SVG and Cesium retain their shared geometry and incident/closure markers. Estimated road costs never become verified measurements. This milestone does not collect genuine ambulance positions.

## Verification and limitations

Automated results and compact evidence are recorded in `docs/v4/v42-verification.json`. Full suite **499 passed in 38.81 s** (zero failures), **19 new HERE tests**, ten legacy scripts, historical integrity, fresh Chennai smoke, original V4 browser QA, HERE-specific browser QA and actual local CLI disabled/fixture boot were run. CLI boot produced no SUMO child and shut down cleanly. Simulation/live mode isolation is enforced. The original 180 trials and later V3 research trials were not regenerated.

Remaining: authentic credentials/licensing/authorization and Chennai coverage/accuracy tests; heterogeneous subsegment mapping; field-calibrated speed/access/ETA and hospital entrance validation; wider directed graph coverage; partner-authorized fleet tracking and clinical status. All operator roles are local prototype roles. No real dispatch, signal actuation or production readiness is claimed.


## Exact modified files

- `citybrain/live/here.py`: gated HERE session, accounting and adapter.
- `citybrain/live/here_demo.py`: local HERE-format route-change demonstration.
- `citybrain/live/__main__.py`: explicit CLI selection/authorization and background update wiring.
- `citybrain/live/traffic.py`: reuse eligibility/cost builder with source labels and validated flow closures.
- `citybrain/live/graph.py`: component and distance-based ETA provenance.
- `citybrain/live/service.py`: current-cost comparison, fresh TrafficAgent evidence and explicit decisions.
- `dashboard/live/app.js` and `dashboard/live/index.html`: provider/coverage/cost/status details and honest source labels.
- `tests/test_here_live.py`: nineteen HERE-specific offline regressions.
- `tools/check_here_browser.py`: provider-to-map offline smoke.
- `tools/check_live_browser.py`: follow the neutral closure-count wording in the preserved V4 check.
- `README.md`, this guide and `docs/v4/v42-verification.json`: setup, boundaries and fresh evidence.
