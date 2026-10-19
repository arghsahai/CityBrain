# V4 feature status and verification

**20 October follow-up:** PR #11 is merged. The existing slice was preserved and freshly revalidated: 480 pytest tests, ten compatibility scripts, historical integrity, Chennai SUCCESS 704 s, and repeatable offline SVG/Cesium checks. See [current synchronization report](V4_SYNCHRONIZATION_20261020.md). The text below records the original milestone; its Draft PR and browser gap statements describe that earlier checkpoint.

**Working local test recommendation prototype; not a completed operational emergency-response platform.** No production-readiness or real traffic coverage claim. Draft PR [#11](https://github.com/arghsahai/CityBrain/pull/11), branch `feature/citybrain-v4-live-operations`. PR #10 was already merged before this task; V4 started from that identical-tree merge on main. No PR was merged by this task.

| Milestone | Actual status |
|---|---|
| 0 audit/baseline | COMPLETE: actual Core/agents/planner/executor/providers/dashboard inspected; 447 baseline tests passed (33.95 s). |
| 1 independent modes/state | IMPLEMENTED and backend/CLI tested; live starts no simulator child. V3 path preserved. |
| 2 public test report / operator verification | IMPLEMENTED; validation, duplicate prevention, limits, RBAC, retention tested; manual Chrome submission and verification observed. |
| 3 dynamic ambulance / snap | IMPLEMENTED; real graph, finite partial-edge positions, off-road/outside/ambiguous directions tested; manual Chrome 0.0 m snap observed. AUTHORIZED_GPS reserved/rejected. |
| 4 hospital directory/status | IMPLEMENTED local prototype: four genuine retained OSM locations; source links, unknown services/addresses/verification times; facility token scope, positive reported capacity and 15-minute expiry tested. Not partner-verified institutional identities. |
| 5 traffic interface | IMPLEMENTED OFFLINE ONLY: SYNTHETIC_TEST, declared RECORDED_PROVIDER_REPLAY, UNAVAILABLE. Existing matching/freshness/cache replay reused. LIVE_PROVIDER activation is NOT_IMPLEMENTED/NOT_AUTHORIZED. |
| 6 geographic route recommendations | IMPLEMENTED and tested: legal directed paths, clipped geometry/ETA, road-unobserved free-flow estimates, eligible offline costs and closures. Scorer/validator reused. No physical execution. |
| 7 live-state reassessment | IMPLEMENTED offline: position/status/traffic/freshness changes, closure invalidation, conservative soft-change gate, exact-ID approval and current-cost revalidation; bounded deduplicated history. Not field-validated. |
| 8 coverage | Pilot routing: 781 passenger-access imported edges within [80.132,12.823,80.174,12.863]. Chennai-wide display controls/optional OSM imagery implemented in Cesium and SVG; citywide routing NOT_IMPLEMENTED. Full browser coverage matrix still incomplete. |
| 9 signal priority | GATED: both programs inventoried; missing movement/clearance/restoration contracts. ADVISORY_ONLY; controller/intervention/restoration comparisons NOT_IMPLEMENTED/NOT_RUN. |
| 10 hardening | Focused backend/security/isolation/cache tests and V3 regressions pass. Native browser first-slice checks observed, but final repeatable 3D/mobile/overlay matrix incomplete; not release-approved. |
| 11 documentation | Architecture, setup, feature status, provider comparison, demo, security/privacy and signal gate documented; see evidence below. |

## Automated and execution evidence

- Baseline: 447 pytest tests passed in 33.95 s.
- First-slice full suite: 466 passed in 36.34 s.
- Traffic milestone full suite: 473 passed in 38.12 s.
- Final focused V4: **31 passed in 2.78 s**. Final full suite: **478 passed in 36.15 s** (31 V4 tests plus 447 preserved baseline tests).
- All ten legacy compatibility scripts passed.
- Fresh V3 simulation and replay-assisted smokes both reached SUCCESS at **704 s**: dispatch 51 s, travel 653 s, zero route changes. Each passed the existing execution/geography audit, including changing signal telemetry, exact route-readback evidence and maximum road-centreline offset **1.7814 m**.
- All **2,172 historical manifest entries** matched, no missing/extra/hash/size differences. All **426 V3.1 study files** matched an independent pre-task SHA-256 snapshot. No official experiment was regenerated.
- Local CLI live boot served assets and geography, ran the scripted offline workflow, had **no simulator child**, and shut down with exit code 0 after SIGINT.
- Actual current-build HTTP demo: seeded 70-edge estimated route, closure → reopening → closure counts **1 → 0 → 1**, future quarantine count 1, valid flow recovery, synthetic outage contained. Demo edge `-828326390#4`; all source labels SYNTHETIC_TEST, never live.
- Tests reproduce partial coverage rejection, real directed paths and ambiguity, partial edge costs, hospital exclusion/expiry/recovery, out-of-order/missing time/direction, future clock recovery, zero/implausible speed, 256-record cache / 64-record quarantine bounds, stale approval rejection, provider exception isolation and history bounds. AST boundary test forbids live imports of Core/TraCI/runtime; signal audit denies actuation.

## Browser evidence — deliberately narrower than automated results

**Newly observed native Chrome UI at the first-slice milestone:** public disposable TEST report submitted → PENDING_VERIFICATION; authenticated local operator verified it; USER_SELECTED ambulance snapped 0.0 m on `1254851247#0`; assessment to incident road `384801126#5` returned PENDING_OPERATOR_REVIEW / RECOMMENDATION_ONLY / 70 estimated edges / 0 observed edges / approximately 6.8-minute unvalidated estimate. SVG road geometry and markers were visible. A hidden SVG attribute defect was found and corrected. JavaScript syntax checks passed after subsequent changes.

Chrome's Cesium attempt reported **WebGL context initialization failure**. This is a handled capability failure; it is not a successful 3D rendering test or a zero-console-error claim. The app now preflights WebGL and retains fallback. Console inspection also showed unrelated browser-extension warnings. A separate Safari native page did initialize a Cesium map (Use 2D fallback remained available), but an isolated final Safari interaction matrix was not completed. Do not generalize that startup observation into verified route/overlay alignment.

**NOT_TESTED as a complete final-build browser matrix:** 3D route/vehicle alignment, closure overlay removal/reappearance by visual assertion, future-clock UI recovery, exact 390/800 px viewport tests, final optional citywide OSM tile loading, device-location permission flow, hospital portal UI round trip and final logout/in-flight response behavior. Backend/API equivalents are tested where described above. Initial narrow developer-pane inspection motivated responsive hardening, but exact final mobile dimensions were not validated. Native browser surfaces were available; isolated DOM automation was unavailable and active browser changes interrupted repeatable checks. No browser test success is invented.

## Remaining gates

1. Complete repeatable final-build browser QA on an isolated WebGL-capable browser; verify 3D/SVG route alignment, map picking, labels, closure 1→0→1 and mobile layouts. Keep PR draft pending that and independent review.
2. Explicit provider/account/credential/licensing/budget authorization, genuine bounded responses and accuracy/coverage study before implementing LIVE_PROVIDER / LIVE_VERIFIED.
3. Verified participating fleet GPS, institution-scoped identity, genuine facility service/capacity workflow and field route/access/ETA validation before any operational use.
4. Reviewed movement/clearance/restoration safety contract before SUMO priority; no real signal integration.
5. Reviewed citywide directed graph import before extending routing beyond the bounded pilot.

Signals, demand and capacity in preserved V3 runs are simulated. Offline V4 fixtures are synthetic or declared replay. Hospital routing arrives at a road, not a validated entrance/admission. No production emergency-response readiness is established.
