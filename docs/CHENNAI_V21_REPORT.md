# CITYBRAIN V2.1 — LIVE TRAFFIC INTEGRATION REPORT

**Phase A stability sign-off is BLOCKED.** The requested stop-before-live-traffic
gate was honored. Production modules, provider placeholders, dashboard, network,
planner, Core and historical results were not changed. Additions are read-only
audit tooling, its tests and review evidence/documentation.

1. **Base commit:** `c1d2c379f651dd4c66dcf68159de98e27a1f803f`. Initial tree was
   clean; the previously reported branch/HEAD and two implementation commits exist.
2. **Final HEAD:** the local audit commit is reported in the delivery message;
   `git rev-parse HEAD` provides its exact hash. No push or merge was performed.
3. **Branch:** `feature/chennai-live-traffic`, created from the verified base.
4. **Phase A audit results:** A–F and H–J verified from code, fresh tests and
   evidence; G is blocked by repeated future-corridor switching. Source/network
   hashes match committed provenance. Saved geographical round-trip error is
   1.42e-14 degrees; maximum vehicle/edge-centerline offset is 1.773 m. Both
   simulated signals have multiple actual TraCI phase states. Hospital-road
   arrival and all eight route executions pass the independent audit. The source
   is actual OSM; clinical capacity, traffic demand, signal programs and incidents
   remain explicitly simulated. No live Chennai API observations are claimed.
5. **Oscillation audit:** P1–P7 alternate between two future corridors before
   divergence at `-1309011039#20`; six acceptances return to an earlier suffix.
   Two single stopped-vehicle readings yield infinite costs and invalid-route
   overrides. At 97 s the route changes six seconds after acceptance despite the
   ten-second commitment setting. These are valid executions of distinct routes
   with changing recorded scores. The audit does not prove equal scores or a
   counterfactual delay; it prevents falsely certifying stability. Detailed raw
   observations, scores, prefixes and source hashes are preserved in
   `chennai/v21/saved-replan-audit.json` and the fresh-run audit.
6. **Provider implementation:** BLOCKED by Phase A. No V2.1 provider code added.
7. **HERE status:** NOT IMPLEMENTED as a live HTTP adapter; existing UNAVAILABLE
   placeholder unchanged. No credential/coverage test or request performed.
8. **TomTom status:** NOT IMPLEMENTED as a live HTTP adapter; existing UNAVAILABLE
   placeholder unchanged. No credential/coverage test or request performed.
9. **Replay:** existing V2 synthetic replay is IMPLEMENTED AND VERIFIED by the
   baseline tests. Requested common V2.1 live/replay normalization is NOT IMPLEMENTED.
10. **Road matching:** existing explicit-ID/point-distance replay matcher is
    IMPLEMENTED AND VERIFIED within its old contract. Direction-aware segment
    matching, ambiguity rejection and confidence classification are NOT IMPLEMENTED.
11. **Freshness:** existing replay age/boolean freshness is IMPLEMENTED AND VERIFIED.
    Requested source/retrieval timestamps and FRESH/STALE/EXPIRED/UNKNOWN interface
    are NOT IMPLEMENTED.
12. **Dashboard integration:** existing Cesium, source labeling and read-only
    evidence viewer are IMPLEMENTED AND VERIFIED. New external-traffic panel,
    connection counters and separately rendered live/replay layers are NOT IMPLEMENTED.
13. **Planner isolation:** IMPLEMENTED AND VERIFIED for the existing system. The
    viewer imports no planner/controller and exposes only GET handlers; external
    records are emitted to telemetry and do not enter routing-cost state. This
    change introduces no production-code modification or external request.
14. **Files changed:** new `tools/audit_chennai_replans.py`,
    `tests/test_chennai_replan_audit.py`, `docs/CHENNAI_TRAFFIC_INTEGRATION.md`,
    this report, and evidence/screenshots under `docs/chennai/v21/`. Exact inventory:
    `git diff --name-status c1d2c37..HEAD`.
15. **Tests:** fresh original suite **278 passed in 12.75 s**; suite with four
    audit regression tests **282 passed in 14.51 s**. Tests verify A→B→A detection,
    suffix-aware comparison, new-diversion handling and rejection of unverified
    acceptance. Passing tests do not waive the observed stability issue.
16. **Browser:** existing Chrome QA rerun against saved evidence: WebGL, moving
    observed ambulance, vehicles, two signals, route geometry, replay filtering,
    terminal SUCCESS, SVG fallback and 800-px layout pass with zero page errors.
    Artifacts: `chennai/v21/browser/`. No live API coverage is implied.
17. **Chennai smoke:** a fresh, unmodified baseline run under
    `data/output/chennai/v21-phase-a-smoke/` reached **SUCCESS at 759 s**, dispatch
    51 s, travel 708 s, eight verified replans, in 176.75 wall seconds. It had zero
    telemetry, dashboard-write or runtime-evidence failures. It also reproduced
    all six future-suffix returns. Its final independent execution and
    oscillation audits are in `chennai/v21/fresh-*.json`; summary/timing are in
    `chennai/v21/phase-a-summary.json`. Prior saved SUCCESS at 759 s, dispatch 51 s,
    travel 708 s and eight replans was independently verified from raw evidence.
18. **Historical integrity:** all **2,172** expected entries match SHA-256 and
    size; zero missing, extra or changed entries. Verified against the existing
    archive manifest. No official trials were regenerated.
19. **Exact commands:** see `CHENNAI_TRAFFIC_INTEGRATION.md` for baseline launch,
    replay, fresh smoke, execution audit, oscillation audit, browser check and pytest.
    No V2.1 live-provider launch command is advertised as implemented.
20. **Limitations and smallest safe fix:** add an opt-in Chennai acceptance
    stability guard for persistent soft-cost improvements, while retaining immediate
    hard-block/topology/permission/execution safety handling. Keep Core readings,
    teammate scoring/policy, route read-back, logical acceptance order and research
    timings unchanged. This guard and its thresholds are proposed, NOT IMPLEMENTED.
    Raising minimum commitment alone does not fix the invalid-route bypass.
21. **Next milestone:** implement/test that narrowly scoped Chennai stability
    correction, repeat transient-stop and lasting-disruption scenarios, then obtain
    independent Phase A sign-off before starting normalized advisory providers.

The 255.39-s duration is independently traced to the preserved paced-run health
record, not remeasured as a new paced presentation in this stage. A fresh unpaced
simulation checks reproducibility without spending another four minutes pacing.
No actual traffic provider coverage, API quota or paid-plan suitability is verified.

CITYBRAIN V2.1 BLOCKED — CORRECTNESS ISSUES REQUIRE FIXES
