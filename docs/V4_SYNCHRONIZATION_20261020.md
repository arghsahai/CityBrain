# CityBrain V4 synchronization and fresh validation — 20 October 2026

## Recovered checkpoint

The supplied older-checkpoint description was superseded by the actual repository. Initial branch `feature/citybrain-v4-live-operations` was clean at `92031e6d1f23b3423d4e233f6bc40ca557dd8abb`, equal to its remote. It had no unpushed or uncommitted work. V4 already existed; no branch was recreated and no implementation was overwritten.

Fetching advanced origin/main from `aa3a57fc1edd35f1a7cf257a8a9eeec3ad1dbf06` to `4b74028b4712c4f33379b8c54afa80ae37e40ebb`. GitHub metadata confirms PR #10 and PR #11 are merged; PR #11 merged on 19 October. The existing V4 branch and new main have identical tree `77407d563050e098357ac5a2a1e29050b15b648f`. A safe fast-forward brought the V4 branch to main; no local main mutation, new merge commit, reset, force update or automatic PR merge occurred.

Ancestry counts after fetch:

| Comparison | Unique older-side commits | Unique newer-side commits |
|---|---:|---:|
| dashboard → V3 roadmap | 0 | 37 |
| dashboard → origin/main | 0 | 47 |
| V3 roadmap → origin/main | 0 | 10 |
| original V4 head → origin/main | 0 | 1 |

Changes after V3 completion: PR #10's identical-tree merge, eight existing V4 commits (directed graph, authenticated incidents, dual-mode map, offline traffic reassessment, source-time/safety hardening and documentation), then PR #11's identical-tree merge. Those substantive V4 changes were audited, not discarded as irrelevant.

## Actual implementation audit

- `simulation/chennai/network/chennai.net.xml` and metadata retain OSM-derived geometry; scenario demand/vehicles/roadworks/signals remain simulated. The pilot graph exposes 781 eligible directed passenger edges.
- `citybrain/core` owns canonical CityState/RoadState/VehicleState and TraCI perception. `citybrain/main.py`, the planner, validator, policy and RouteExecutor retain execution/read-back-before-acceptance and terminal outcome rules. Fresh simulation audit confirms legal routes, hospital endpoint, exact suffix read-back, arrival evidence and changing signal observations.
- Five existing agents remain unchanged. V4 reuses structured agent interfaces, RouteScorer and PlanValidator where compatible; geographic search and independent live state do not pretend to be EmergencyPlanner/SUMO execution. HospitalAgent's explicit suitability contract is preserved.
- `citybrain/chennai/traffic` contains HERE/TomTom adapters, normalization, directed matching, timestamps, quarantine and bounded cache. V3 consumes these as advisory observations. `citybrain/live/traffic.py` permits only offline injection/recordings; no provider activation exists in V4.
- `citybrain/live/{graph,store,service,server,__main__}.py` already implements all A–G requirements from the requested first slice: mode isolation; public map-pin TEST submission; authenticated verification; USER_SELECTED ambulance; directed matching/connectivity; explainable estimated route rendered in Cesium/SVG.
- `dashboard/live` shares real WGS84 geometry across map paths. Loopback roles, tokens, retention, duplicate/rate/body limits and operator-only incident visibility are enforced server-side. V3 telemetry and V4 state remain separate.

## Requested V4 capability classification

| Planned feature | Classification | Verified boundary |
|---|---|---|
| Live-data mode alongside simulation | IMPLEMENTED_AND_VERIFIED | Independent offline prototype; simulation delegates to preserved launcher |
| User-reported accident locations | IMPLEMENTED_AND_VERIFIED | Confirmed TEST pins and validated local submission, not actual emergency intake |
| Authorized operator verification | IMPLEMENTED_AND_VERIFIED | Local high-entropy test role; public/facility roles cannot verify |
| Arbitrary ambulance starting positions | PARTIALLY_IMPLEMENTED | User-selected pins within pilot, 25 m matching and explicit ambiguous direction; no fleet GPS |
| Real Chennai hospital locations | PARTIALLY_IMPLEMENTED | Four retained OSM locations; entrances, institutional identities and clinical suitability unverified |
| Hospital staff/operator availability | PARTIALLY_IMPLEMENTED | Facility-scoped local STAFF_REPORTED test status, positive beds and 15-minute expiry |
| Authorized HERE/TomTom observations | BLOCKED_BY_EXTERNAL_ACCESS | Adapters exist; no request authorized, no genuine current response or V4 activation |
| Traffic-aware recommendation | PARTIALLY_IMPLEMENTED | Connected graph with estimates or eligible offline observations; no field ETA validation |
| Dynamic reassessment | PARTIALLY_IMPLEMENTED | Offline conditions, current-cost revalidation, exact-ID approval and stability gates; no operational vehicle tracking |
| Chennai-wide map support | PARTIALLY_IMPLEMENTED | City overview/display controls; routing restricted to retained pilot; online tiles not exercised |
| Simulation-only signal priority | ADVISORY_ONLY | Signal inventory denies actuation without movement/clearance/restoration contracts |

Real geometry is not a live traffic measurement. Synthetic tests and declared recordings remain distinct from genuine provider observations. USER_SELECTED and STAFF_REPORTED are manually supplied test data. Live recommendations never invoke RouteExecutor, imply actual movement, or infer arrival from ETA.

## Fresh results in this continuation

- Initial unchanged full suite: **478 passed in 36.52 s**.
- After the asset fix and its two regressions: **480 passed in 39.10 s**.
- All ten legacy root scripts: **10/10 passed** using `venv/bin/python test_NAME.py`.
- Historical integrity: **2,172 expected / 2,172 actual**, zero missing, extra, hash or size mismatches; official trials not regenerated.
- New seed-17 Chennai simulation: **SUCCESS 704 s**, dispatch 51 s, travel 653 s, zero route changes, zero telemetry or dashboard write failures. Independent audit passed exact physical execution ordering, legal connectivity, hospital access-road arrival and signal changes; maximum road-centreline offset **1.7814081507793178 m**, coordinate round-trip error **1.4210854715202004e-14 degrees**.
- Warning: `Cannot find proj.db` occurred three times. Nonfatal here; geographic/physical audits passed. A first attempted smoke used an already-created output directory and was rejected by the existing safeguard; the successful fresh run used an unused child path. No implementation change was needed for that command correction.
- Repeatable isolated Chrome check: public map click/submission → operator verification → user-selected ambulance → 70-edge connected estimated recommendation with zero observed edges. SVG route geometry count agreed with the recommendation. Synthetic closure overlays 1→0→1, future quarantine/recovery, facility portal round trip, logout private-state/storage clearing and 800/390 px no-horizontal-overflow checks passed.
- Cesium initialized under Chrome software WebGL; road and route geographic coordinates matched backend evidence within 1e-7 degrees. Screenshots reviewed. Zero page errors, failed HTTP responses or external browser requests. This is software-rendered browser QA, not validation on a physical exam laptop.

## New changes and reasons

| File | Reason |
|---|---|
| `citybrain/live/server.py` | Serve pre-encoded JSON asset bytes without API-object serialization; fixes Cesium terrain/astronomy JSON HTTP 500 |
| `dashboard/live/app.js` | Small display-only line heights keep roads/routes/traffic above ellipsoid chords; no geographic or routing changes |
| `tests/test_live_http.py` | Two actual Cesium JSON asset regressions with exact bytes and parsed JSON |
| `tools/check_live_browser.py` | Optional self-contained browser workflow with disposable loopback service, ephemeral tokens and blocked external requests |
| `docs/V4_SYNCHRONIZATION_20261020.md` | Current branch/merge audit, feature classification, fresh results and limitations |
| `docs/v4/revalidation-20261020.json` | Compact fresh evidence, output paths and hashes |
| `docs/V4_FEATURE_STATUS.md` | Dated pointer to fresh follow-up; preserves historical evidence |
| `docs/V4_LIVE_DATA_SETUP.md` | Repeatable optional browser QA command |
| `README.md` | Reconcile merged PR #11 and link fresh revalidation |

No existing Core, agent, planner, executor, SUMO network/scenario or research dataset was changed. The first V4 slice already existed; this continuation verifies it and fixes the two reproduced display defects rather than duplicating it.

## Reproduce

```sh
venv/bin/python -m pytest -q
venv/bin/python -m citybrain.chennai.validate --historical
V4_QA_ROOT="$(mktemp -d /tmp/citybrain-v4-qa.XXXXXX)"
./tools/run_chennai.sh --mode simulation --seed 17 --seconds-per-step 0 --no-server --no-browser --exit-on-complete --output "$V4_QA_ROOT/run"
venv/bin/python -m citybrain.chennai.validate --run "$V4_QA_ROOT/run"
# Optional browser QA requires playwright plus an installed Chrome channel:
venv/bin/python -m pip install playwright
venv/bin/python tools/check_live_browser.py --output "$V4_QA_ROOT/browser"
```

For an interactive offline demo, use the temporary credential/database commands in [V4 setup](V4_LIVE_DATA_SETUP.md), open http://127.0.0.1:8784/?fallback=1, then follow [the TEST incident workflow](V4_DEMO_SCRIPT.md). `venv/bin/python -m citybrain.live.demo --scenario seed` exercises the same local service when the server's operator token is in the environment. No HERE/TomTom/Google requests, paid services, actual dispatch or physical signal operations are enabled.

## Remaining work

V4 is not complete. Remaining gates include 3D map picking and overlay lifecycle visual checks across browsers/hardware, emulated geolocation and logout in-flight race QA, optional citywide tile loading, citywide directed routing, authorized provider licensing/budget/coverage/calibration, participating fleet/GPS and hospital identity/workflows, field ETA/access validation and reviewed SUMO signal intervention/restoration. No production emergency-response readiness is established. This follow-up is submitted as a new Draft PR against main; merged PR #11 is historical and is not reopened or re-merged.
