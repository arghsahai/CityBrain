# CITYBRAIN V2.2 — FINAL IMPLEMENTATION REPORT

**Subsequent correctness hotfix:** three issues found after this implementation
checkpoint are corrected and revalidated in [CHENNAI_V22_HOTFIX.md](CHENNAI_V22_HOTFIX.md).
The results below remain the original V2.2 implementation record.

1. **Branch/base/final HEAD.** `feature/chennai-traffic-providers`, based on
   `4ed30b79b1ae1c8f1063fa4cd9d924762fc5cc0c`. Fetched origin/main is already an
   ancestor. Exact final HEAD and local commit IDs are provided in the delivery
   message; obtain them with `git log -3 --oneline` / `git rev-parse HEAD`.
2. **Changed files.** Every repository file and its classification/purpose is in
   [files-changed.md](chennai/v22/files-changed.md). No dependency, SUMO network,
   shared planner/Core, Chennai stability guard or official experiment changes.
3. **HERE — IMPLEMENTED BUT NOT LIVE-VERIFIED.** Documented v7 flow normalization,
   optional separate incidents, bounded area, credential/authorization gates,
   timeout, safe authentication/rate-limit/outage handling. Mock-tested only.
   Actual status: NOT_CONFIGURED. Real coverage: BLOCKED BY API CREDENTIALS.
4. **TomTom — IMPLEMENTED BUT NOT LIVE-VERIFIED.** Documented v4 point-flow query,
   speeds, travel times, closure and geometry normalization; same failure gates.
   Actual status: NOT_CONFIGURED. No source timestamp or established shape travel
   bearing is invented. Direction/time UNKNOWN prevents a verified SUMO match.
5. **Replay — IMPLEMENTED AND VERIFIED.** Bounded normalized JSON input, declared
   provenance, chronological emit-once records, invalid-row reporting, no live
   label. Bundled data is SYNTHETIC_SAMPLE on actual Chennai road geometry. Recorded
   provider data would be REPLAY. Final cache has one latest segment, one matched
   road, zero duplicate/out-of-order records, zero failed polls.
6. **Road matching — IMPLEMENTED AND VERIFIED within tested scope.** Spatial index,
   <=10 m sampling, <=15 m proximity, <=35° local heading, monotonic progress,
   actual directed connectivity and 3 m ambiguity margin. Connectivity resolves
   ties only near an end/start transition; connected parallel roads remain ambiguous
   mid-edge. Actual sample edge `-1192027270` matches; synthetic opposite directions,
   close parallel roads, cross streets, missing geometry, multi-edge paths and
   disconnected fragments pass. Confidence is geometric, not a calibrated probability.
7. **Dashboard — IMPLEMENTED AND VERIFIED.** Existing Cesium extended with advisory
   provider status/count/age/error panel, road selection, separately labeled SUMO
   and external speed/free-flow/congestion/time, purple/grey flow lines and gold
   incidents. No redesign or replacement telemetry system. Real-time API snapshots
   age after terminal outcome; recorded live-provider values become REPLAY in the
   viewer. Missing timestamps remain UNKNOWN. SVG fallback supports observations.
8. **Chennai simulation — IMPLEMENTED AND VERIFIED.** Fresh clean-base seed-17
   baseline and both advisory replay runs: SUCCESS, dispatch 51 s, arrival 704 s,
   travel 653 s, zero accepted replans. Final run has zero telemetry, dashboard or
   evidence failures and no pending guard. Actual hospital-road arrival is audited;
   medical admission/clinical capacity is not established. See
   [final-replay-validation.json](chennai/v22/final-replay-validation.json) and
   [final-replay-summary.json](chennai/v22/final-replay-summary.json).
9. **Planner isolation and stability — IMPLEMENTED AND VERIFIED.** INTERNAL STABILITY
   GATE PASSED; 36 focused guard/SUMO tests, reviewed A–J criteria and preserved
   hard-bypass/read-back/arrival/NO_ROUTE behavior. This is internal technical review,
   not independent human review. External service imports no planner/Core/TraCI;
   no external data enters scoring or replan triggers. Accepted plans match baseline
   exactly. Shared control files and the 20-second guard are unchanged. No performance
   improvement is claimed. See [stability-gate.md](chennai/v22/stability-gate.md).
10. **Tests — IMPLEMENTED AND VERIFIED.** Final full suite: **375 passed in 35.27 s**;
    60 provider/pipeline cases including parameterized scenarios. All ten original
    compatibility scripts exit zero. Python compilation, JavaScript syntax and
    diff whitespace checks pass. HTTP responses are mocked; no mock establishes
    Chennai coverage. See [pytest.txt](chennai/v22/pytest.txt),
    [compatibility.json](chennai/v22/compatibility.json) and `tests/test_chennai_traffic.py`.
11. **Browser — IMPLEMENTED AND VERIFIED.** Chrome 155 headless WebGL, zero page
    errors; actual moving vehicle/ambulance positions, hospitals, accepted route
    geometry, guarded KEEP, both signals, terminal SUCCESS, 800 px layout, SVG
    fallback, separate external flow/incident entities and exact external geometry.
    Selected-road comparison and synthetic/replay labels pass. Explicit synthetic
    presentation cases also check UNKNOWN missing time and EXPIRED labels; these
    are UI tests, not real provider observations. Final evidence:
    [browser-check.json](chennai/v22/browser-final/browser-check.json),
    [traffic screenshot](chennai/v22/browser-final/traffic.png).
12. **Historical integrity — IMPLEMENTED AND VERIFIED.** All **2,172 / 2,172** expected
    entries match size and SHA-256, zero missing/extra/changed. No official 180-trial
    regeneration. Full raw pilot evidence stays under ignored `data/output/chennai/`.
13. **Exact launch commands.** Existing launcher is unchanged. Default remains
    simulation-only; optional commands below. Missing credentials or absent explicit
    authorization show advisory unavailability while SUMO continues.
14. **Git commits.** Three logical local commits: `338927e` provider/runtime integration;
    `d2dae32` dashboard integration; final regression tests/documentation/evidence
    commit hash in delivery. No push, merge, reset, rebase or main change.
15. **Working tree.** Verified clean after the final local documentation commit;
    final delivery reports the observed status. Pilot processes created for this
    verification are stopped after browser review.
16. **Remaining limits.** LIVE COVERAGE NOT VERIFIED — CREDENTIALS REQUIRED. No paid
    provider requests made. Provider account terms/retention rights, coverage,
    timestamp latency and accuracy are unverified. TomTom OpenLR directional decoding
    and separate incident-detail querying are NOT IMPLEMENTED. TomTom defaults to
    one study-area query point. HERE split links favor safe independent observations;
    live mapping accuracy still needs a measured study. Replay uses a simulation
    clock. Thresholds are pilot defaults. Idle roads can show unavailable simulated
    speed because existing telemetry emits occupied/blocked roads. Last-valid stale
    data stays visibly historical. Cache is bounded to 256 records; a daemon worker
    performs no overlapping network calls, respects retry delays and does not wait
    on requests during cleanup. The historical legacy point replay API remains only
    for compatibility; the new launcher never uses its weaker matching contract.
17. **Next milestone.** Independent review, then separately authorized small live
    coverage/matching validation and calibration. V2.3 is not started. Future matched,
    fresh observations could enter a separately validated calibration boundary;
    external-data-assisted routing is NOT IMPLEMENTED or activated here.

```sh
./tools/run_chennai.sh --traffic-source simulation
./tools/run_chennai.sh --traffic-source replay
./tools/run_chennai.sh --traffic-source here
./tools/run_chennai.sh --traffic-source tomtom
# Repeatable offline validation; choose a fresh output directory:
./tools/run_chennai.sh --traffic-source replay --seconds-per-step 0 --no-server --no-browser \
  --output data/output/chennai/my-new-v22-run
venv/bin/python -m pytest -q
venv/bin/python -m citybrain.chennai.validate --historical --run data/output/chennai/my-new-v22-run
# View existing final evidence (Ctrl-C stops the local server):
./tools/run_chennai.sh --mode replay --events data/output/chennai/v22-final-replay --no-browser --port 8773
venv/bin/python tools/check_chennai_browser.py --url http://127.0.0.1:8773 \
  --traffic --keep-at 61 --output /tmp/my-v22-browser
```

Authorization, official provider contracts, architecture, data schema, freshness,
licensing considerations and setup: [CHENNAI_LIVE_TRAFFIC.md](CHENNAI_LIVE_TRAFFIC.md).
The explicit `--authorize-traffic-requests` flag is required for potentially billable
queries even if a key is present; it was not used in this work.

All simulations truthfully retain implementation-time Git provenance. The final
replay includes uncommitted implementation changes and precedes the final narrow
connected-parallel matching rejection, which is verified by the final full suite.
Saved runs are not relabeled as clean-release runs. Research conclusions are unchanged.

CITYBRAIN V2.2 COMPLETE — READY FOR INDEPENDENT REVIEW
