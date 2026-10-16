# CITYBRAIN V2 — CHENNAI DIGITAL TWIN IMPLEMENTATION REPORT

Owner: Krishna Verma. Local Chennai pilot implementation, 16 October 2026.

| Feature | Status | Evidence / limits |
|---|---|---|
| Actual OSM geography and SUMO import | IMPLEMENTED AND VERIFIED | 795 corridor edges; preserved projection; startup and actual route execution |
| Hospital destinations | IMPLEMENTED AND VERIFIED | Four OSM POIs, reachable edges and measured access offsets; clinical capabilities unverified |
| Synthetic traffic profiles | IMPLEMENTED AND VERIFIED | NORMAL full run; HEAVY/PEAK route validation and SUMO startup; long higher-demand outcomes unverified |
| Existing Core/planner integration | IMPLEMENTED AND VERIFIED | Existing runtime, agents, planner, policy and verified executor retained |
| Emergency planning, replanning, arrival | IMPLEMENTED AND VERIFIED | SUCCESS at 759 s; eight actual replans; separate actual SUMO NO_ROUTE cleanup test |
| Cesium and local 2D fallback | IMPLEMENTED AND VERIFIED | Chrome WebGL, vehicle movement, route, signals, replay, fallback and tablet checks |
| SUMO vehicle/road/signal telemetry | IMPLEMENTED AND VERIFIED | Actual measurements, source/time labels; all observed vehicles aligned within 1.78 m of edge centerlines |
| Offline traffic replay and explicit edge matching | IMPLEMENTED AND VERIFIED | Bundled synthetic fixture; 30 m match threshold; freshness; no SUMO overwrite |
| GPS replay | IMPLEMENTED AND VERIFIED | Synthetic consent/session-gated feed, recorded clock and 120-s expiration; separate map markers |
| HERE/TomTom live observations | BLOCKED | No credentials; live HTTP adapters NOT IMPLEMENTED; coverage and licensing unverified |
| Optional OSM raster basemap | IMPLEMENTED BUT UNVERIFIED | Toggle and attribution implemented; baseline works without requesting tiles |
| Paid terrain/photogrammetry assets | NOT IMPLEMENTED | Local ellipsoid and labeled estimated OSM building extrusions provide the baseline |
| Actual mobile GPS tracking | NOT IMPLEMENTED | No ingestion endpoint or real location collection |
| Live pause/control and signal-priority controller | NOT IMPLEMENTED | Viewer remains read-only; signal programs execute normally in SUMO |

1. **Current Git branch:** `feature/chennai-3d-digital-twin`.
2. **Base commit:** `f95fdee1ef70171b8a33ecdfce11b7496d3f11ee`, the actual
   `feature/krishna-watchable-demo` HEAD. Its ancestry includes the dashboard
   `4bf0f48d8acfac078fb2a2f9e8f5dc21851a70f1` and fetched `origin/main`
   `fe471a863858489229c6bb956498405c77a2558e`. The working tree was initially clean.
3. **Final HEAD:** the final documentation/verification commit is reported in the
   delivery message (`git rev-parse HEAD`). Implementation commit:
   `120427009f5c198574eb3793e8926020070d6d2b`. A tracked report cannot contain its own
   commit hash. No push or merge occurred.
4. **Existing system audit:** Python/SUMO 1.27.1, Core-owned TraCI, shared state,
   structured agents/planner/policy, execution verification, evidence writer,
   GET-only dashboard and separate local Three.js S08 view were already present.
   Reused their runtime/evidence contracts. Existing experimental evidence contains
   120 + 60 official trials and the frozen 2,172-file integrity manifest. Existing
   branches were inspected and fetched. Local `main` remains the unrelated
   `e660ecd6abbf5fff391c4e09d51f645198df18ae`; it was not reset or modified.
   Remote: `git@github.com:arghsahai/CityBrain.git`.
5. **Starter audit:** no Chennai starter ZIP was found in the repository or
   Downloads. Implemented the missing pilot directly; no dependency on that ZIP.
6. **Implemented components:** import/build pipeline, real geographical network,
   Chennai route catalogue, synthetic demand, reversible roadworks, existing
   CityBrain runtime integration, telemetry, replay, Cesium operations interface,
   external-provider boundary, GPS replay, launcher and independent audit tools.
7. **Files created:** `citybrain/chennai/{network,build,scenario,run,telemetry,
   traffic_providers,gps,server,validate}.py`, package entrypoints;
   `simulation/chennai/network/` source/network/provenance/geography/metadata and
   pinned SUMO typemap; `simulation/chennai/scenarios/` replay fixtures;
   `dashboard/cesium/{index.html,app.js,styles.css}` and local Cesium distribution;
   `tests/test_chennai.py`, `tests/test_chennai_sumo.py`; `requirements-chennai.txt`;
   `tools/run_chennai.sh`, `tools/check_chennai_browser.py`; Chennai documentation,
   machine-readable verification results and screenshots. Vendor inventory and
   SHA-256s are in `dashboard/cesium/vendor/manifest.json`. Exact change inventory:
   `git diff --name-status f95fdee..HEAD`.
8. **Existing files modified:** `.gitignore` allows the separate Chennai network;
   `citybrain/core/traci_interface.py` adds geographical observations and explicit
   simulation-only lane-speed scenario actions. No other pre-existing application,
   planner, agent, experiment or dashboard implementation was changed.
9. **Map coverage:** VIT Chennai reference 12.8408 N, 80.1540 E, checked against
   OSM campus way 336095563. Approximately 4.6 × 4.4 km corridor envelope with full
   selected edge geometries; main roads, hospital access and useful diversions.
   Most residential cul-de-sacs are omitted. No Chennai road geometry was invented.
10. **Network validation:** real XML import, geographic round-trip, emergency
    permissions, legal turn connections, startup and complete route execution
    checked. Twelve distinct loop-free ambulance routes span 7.45–8.79 km because
    legal access/turns lengthen travel. OSM directionality/classification is imported.
    The source's one no-right-turn relation lies outside the retained corridor;
    no surveyed restriction dataset is claimed. Import warnings are retained.
11. **Hospitals:** Tagore Medical College Hospital (selected), Sri Meenachi
    Hospital, Sugam Hospital and Kathir Memorial Hospital. Coordinates, OSM links,
    reachable edges and road-access offsets are in `metadata.json` and the technical
    guide. Availability is simulated; emergency/ICU services and final driveways
    are unverified.
12. **Traffic generation:** 90 seeded, valid background routes. NORMAL/HEAVY/PEAK
    demand rates: 0.7/1.4/2.2 vehicles per simulation second. These are synthetic,
    not calibrated Chennai counts. Actual queues/speeds come from SUMO.
13. **Emergency scenario:** seeded ambulance departure at 40 s, actual dispatch
    at 51 s; roadworks at 90 and 587 s in the verified seed-17 runs. The second
    event waited for an eligible future edge with a surviving diversion. Both
    restrictions last 85 simulation seconds. No decision sequence was fabricated.
14. **Core integration:** one Core-owned connection. Existing observe → plan →
    execute → read back → accept sequence, reservations, terminal cleanup,
    exception safety and teleportation semantics remain intact. The pilot bounds
    its optional RAM evidence cache; full evidence persists to disk.
15. **Planner integration:** Chennai-specific route catalogue derived from real
    legal topology. Existing suffix normalization, validation, scoring, agent
    selection and replanning policy are reused. Neither teammate's planner nor
    Core orchestration was rewritten.
16. **Replanning results:** nine accepted plans (P0–P8), eight physical route
    changes, each verified before acceptance. Actual acceptance times and routes
    are in `docs/chennai/validation.json`. Revision count is an observation of this
    run, not a promise for every seed/demand/network version.
17. **Cesium 3D:** pinned local CesiumJS 1.121.0, actual geographical roads,
    OSM buildings, enlarged 3D vehicle glyphs, distinct ambulance, hospital/incident
    markers, route and congestion overlays, camera/follow controls. Baseline needs
    no ion account, token or internet. Vehicle glyphs are simple boxes/markers,
    not detailed car models. Terrain is the WGS84 ellipsoid, not surveyed elevation.
18. **Vehicle telemetry:** every active vehicle supplies ID, category, lon/lat,
    heading, speed, current edge, simulation timestamp and source. Ambulance route,
    accepted plan, hospital and plan-time ETA come from runtime evidence. Missing
    data is shown as UNAVAILABLE; no independent browser simulator exists.
19. **Traffic-light telemetry:** actual TraCI phases/states at two synthetic
    programs on actual road junctions; multiple phases verified for both. These
    are not asserted physical light locations. No signal-priority writes occur.
20. **Dashboard:** read-only simulation status and demand label, vehicle counts,
    ambulance state, hospital, route/ETA, accepted plan history, candidate scores,
    validity/reasons, agent detail, execution read-back, road speeds/queues,
    signal states, source/freshness, live timeline, terminal metrics and replay
    controls. Uses the existing evidence reducer instead of duplicating its logic.
21. **Live traffic:** official HERE/TomTom API documentation investigated; no
    credentials in the named environment variables. Adapters report UNAVAILABLE.
    Replay is implemented with explicit segment mapping, geometric validation,
    freshness/source labels and no automatic overwrite of SUMO road state.
22. **GPS:** synthetic recorded feed and consent/session/accuracy/time validation,
    separate markers and 120-s expiration implemented/tested. No real tracking,
    mobile authentication or public location-history endpoint exists.
23. **Full pytest:** **278 passed**; final result recorded in `validation-summary.json`.
    All ten teammate/legacy root scripts also exited zero. New tests include real
    SUMO startup for higher demand and actual dispatched-ambulance NO_ROUTE cleanup.
24. **End-to-end simulation:** two complete unpaced NORMAL runs reached SUCCESS
    at 759 s, dispatch 51 s, travel 708 s, eight replans, no evidence/telemetry
    failures; wall times 183.41 and 184.88 s. The final integrated paced launcher
    also reached SUCCESS at 759 s in **255.39 wall seconds** (4 min 15 s), with
    zero telemetry/dashboard/evidence failures, 759 explicitly matched traffic
    replay frames and 121 GPS replay frames. Its independent audit is
    recorded in `docs/chennai/validation-final-paced.json` and `validation-summary.json`.
25. **Browser verification:** Chrome WebGL rendering, moving observed ambulance,
    vehicles, both signals, accepted route, replay filtering, SUCCESS, local SVG
    fallback and 800-px layout passed with zero page errors. A separate LIVE check
    observed simulation advancement and a validated traffic-replay edge match;
    browser closure left runtime active. See browser-check JSON files.
26. **Historical integrity:** expected/actual **2,172 / 2,172**; missing, extra,
    SHA-256 mismatches and size mismatches all zero against the existing frozen
    archive manifest. No official trials were regenerated or historical files edited.
27. **Launch commands:** `./tools/run_chennai.sh` for simulation;
    `./tools/run_chennai.sh --mode live-assisted` for simulation with unavailable
    live-provider boundary; `./tools/run_chennai.sh --mode replay-assisted` for
    labeled traffic/GPS fixtures; `./tools/run_chennai.sh --mode replay --events
    data/output/chennai/final-paced` for recorded replay. Setup, pacing, profiles,
    shutdown and verification commands are in `CHENNAI_DEMO.md`.
28. **Screenshots:** `docs/chennai/desktop.png`, `fallback.png`, `tablet.png`,
    `live.png`. Browser QA is reproducible with `tools/check_chennai_browser.py`
    and optional Playwright + Chrome. Screenshots were visually inspected.
29. **Known limitations:** no real traffic coverage test, clinical service/capacity
    verification, surveyed hospital entrance, real signal survey, measured demand
    calibration, detailed vehicle models, accurate terrain or photogrammetry.
    Higher-demand full completion is unverified. A host's computation time can
    exceed requested pacing. The viewer is local-only and has no live pause endpoint.
    The macOS SUMO library emits `proj.db` warnings; actual geographic conversion
    and alignment nevertheless pass independent numerical checks.
30. **Remaining tasks:** validate real entrances/turn rules/signal inventory;
    calibrate demand; run long HEAVY/PEAK trials separately from research evidence;
    implement/test a credentialed provider and direction-aware map matching;
    build authenticated opt-in GPS ingestion only when a real prototype is requested;
    refine 3D vehicle models and optional terrain.
31. **Next milestone:** survey/validate the pilot's road access and signal inventory,
    then test one credentialed traffic provider's VIT coverage and timestamp/segment
    matching before allowing external observations to influence simulated planning.
32. **Commit status:** logical local implementation commit plus final verification
    documentation commit. No push, force push, reset, merge or branch deletion.
    Upstream `main`, unrelated local `main` and teammates' branches are preserved.
33. **Working-tree status:** checked at delivery; final exact HEAD/status are given
    in the accompanying response. Runtime data stays in ignored `data/output/`.

Technical design: [CHENNAI_DIGITAL_TWIN.md](CHENNAI_DIGITAL_TWIN.md).
Launch and faculty demonstration: [CHENNAI_DEMO.md](CHENNAI_DEMO.md).
