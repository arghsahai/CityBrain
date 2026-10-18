# CityBrain — final project status

Date: 18 October 2026. Verdict: **READY_WITH_DOCUMENTED_LIMITATIONS** for an academic software demonstration. This is not emergency dispatch infrastructure. Working branch: `feature/citybrain-v3-roadmap`; PR #10 remains open and Draft, targeting `main`. Current PR metadata is linked on [GitHub](https://github.com/arghsahai/CityBrain/pull/10); dated historical PR statements are not current instructions.

## Verified scope and feature matrix

| Feature | Current implementation | Evidence / test coverage | Issue and action | Final status |
|---|---|---|---|---|
| Chennai digital twin | OSM-derived roads, SUMO demand/vehicles/signals | `tests/test_chennai.py`, fresh run/geography audit | No blocker reproduced | IMPLEMENTED_AND_VERIFIED |
| Emergency event | Configured simulated incident and ambulance event, not camera detection | Source `scenario.py`, `run.py`; dispatch at 51 s | Label simulated | IMPLEMENTED_AND_VERIFIED |
| Shared state and coordination | Core/CityState and planner agent assessments | `test_final_runtime.py`; all ten compatibility scripts | Teammate implementations preserved | IMPLEMENTED_AND_VERIFIED |
| Agent roles | Traffic assessment; available ambulance; explicitly suitable configured hospital | Agent source and tests | Police is logical advisory; no physical police vehicle | IMPLEMENTED_AND_VERIFIED |
| Route scoring and validation | Existing scorer, validator, current-position suffixes and topology checks | Planner, executor and runtime tests | No algorithm rewrite required | IMPLEMENTED_AND_VERIFIED |
| Execution / arrival / cleanup | Exact SUMO route read-back before acceptance; arrival-road check; immutable terminal states | Fresh audit; failure/recovery/teleport tests | Success excludes teleport/disappearance | IMPLEMENTED_AND_VERIFIED |
| Replanning | Guarded Chennai reassessment; saved S08 P0/P1/P2 execution evidence | Guard tests; browser KEEP at 61 s; saved-demo verifier | Two distinct demos, not one spliced run | IMPLEMENTED_AND_VERIFIED |
| Cesium and SVG | Observed positions/routes, signals, hospitals, incidents and replay | Chrome 155: zero page errors; 800/390 px checks | Branding, terminal note, travel-time label and replay button corrected | IMPLEMENTED_AND_VERIFIED |
| Traffic normalization/matching/cache | Directed geometry/coverage, timestamp quarantine, stable stream identity and bounds | Traffic/clock/coverage/streams tests; browser closure 1→0→1 | Unknown data is not promoted to authoritative measurement | IMPLEMENTED_AND_VERIFIED |
| HERE/TomTom adapters | Explicit authorization, timeouts, bounded responses, sanitized errors and rate-limit backoff | Mocked provider tests; direct source audit | No authentic responses or live coverage/accuracy verification | IMPLEMENTED_BUT_UNVERIFIED |
| Traffic advisor | Default-off; isolated candidate comparison, cannot invoke planner/executor | Runtime advisor tests and mocked browser display | No traffic-assisted route commitment | ADVISORY_ONLY |
| Signals | SUMO phase/link/timing observations and recommendations | Changing telemetry, browser and advisory tests | No reviewed phase movement/clearance/restoration contract | ADVISORY_ONLY |
| Browser location | Consented tab-local marker, Stop cleanup; no upload/routing | Browser emulation of consent, stale/out-of-order/jump cases | Real device location not collected in QA | IMPLEMENTED_AND_VERIFIED |
| Research results | Separate V3.1 60-cell study; original 180 trials preserved | CSV/JSON count and paired-result audit; 2,172-entry historical manifest | No trials regenerated | IMPLEMENTED_AND_VERIFIED |
| Academic package | 12-slide PPTX, DOCX/PDF, current screenshots and handouts | File/import/render/text/overflow checks | Native exam-laptop rehearsal still required | IMPLEMENTED_AND_VERIFIED |
| Real camera detection, physical signal control, runtime phone GPS, clinical capacity | Absent; no fabricated feeds or control path | Source audit | Deliberately outside current prototype | OUT_OF_SCOPE |
| Production dispatch, multi-emergency allocation and safety certification | Absent | Scope and source audit | Requires separate design and external validation | NOT_IMPLEMENTED |

## Issues and minimal fixes

No P0 core-workflow/result-invalidating defect or P1 demonstration blocker was reproduced. P2 corrections: replaced stale dashboard V3.0 branding; explained terminal vehicle absence without retaining a false current position; relabeled the travel-time metric; synchronized replay button state; removed the favicon 404; reconciled README/status drift; and exposed a portable saved-S08 verification command. No Core, agent, planner, executor or Chennai stability implementation changed.

The original README is retained as [historical experiment documentation](HISTORICAL_EXPERIMENT_README.md). V3.0/V3.1 documents now identify superseded milestone statements. Old evidence is not relabeled as fresh simulation.

## Evidence and tests

- Current full pytest: **447 passed in 38.38 s**, zero failures. Baseline audit also passed 447 tests in 33.95 s.
- All ten top-level compatibility scripts: **10/10 exit zero**.
- Fresh normal and replay-assisted advisor runs: **SUCCESS at 704 s**, dispatch 51 s, travel 653 s, zero route changes; zero telemetry/dashboard write failures. Their provenance records clean runtime source revision `199be416`.
- Read-only execution/geography audit: exact route read-back before acceptance, legal route connectivity, configured hospital road arrival, changing signal states; maximum centreline offset approximately **1.7814 m** and coordinate round-trip error **1.42e-14 degrees**.
- Chrome 155: route geometry agreement, moving ambulance/vehicles, signals, guarded KEEP, synthetic source/freshness labels, closure removal and future-clock recovery, consented location emulation/Stop cleanup, SVG fallback, terminal vehicle absence and 800/390 px layouts; **zero page errors and zero failed local HTTP responses**.
- Saved S08 archive: SHA-256 `c7d53a707541f39baee33ee2258038c854adf34ceb14c72f680177a39980e834`; 748 records; matching execution before P0/P1/P2 at 301/311/316 s; arrival 425 s. Its geometry matches the retained S08 network. Source revision `f2fb49f0`; not a new Chennai run. Original generated input files are absent from the compact archive, so their recorded hashes are not independently recomputed.
- Historical validator: **2,172/2,172**, zero missing/extra/hash/size mismatches. The V3.1 study's **426 files** match the baseline hash snapshot; all 60 identities and published outcome/paired counts agree.

Compact audit outputs: [validation](final-qa-evidence/validation.json), [simulation](final-qa-evidence/simulation-validation.json), [replay](final-qa-evidence/replay-validation.json), [Chrome](final-qa-evidence/chennai-browser.json), [saved demo](final-qa-evidence/saved-replan-audit.json), [saved-demo browser](final-qa-evidence/saved-replan-browser.json), [research](final-qa-evidence/research-audit.json). Large new runtime logs remain in the temporary directory recorded by the validation JSON and are not committed as research data.

Known local warning: SUMO emitted `Cannot find proj.db` three times in each fresh run. These were non-fatal; both outcomes and the independent pyproj coordinate/centreline audit passed. The interactive launcher served its terminal SUCCESS, Ctrl-C exited zero, all test ports were released, and a second replay launch on the same port responded. This does not establish a clean installation on another laptop.

## Two reproducible demonstrations

**Demo A — Chennai normal response:** `./tools/run_chennai.sh --mode simulation --seed 17`. Optional synthetic sidecar: `--mode replay-assisted --experimental-traffic-evaluation`. Zero accepted route changes in seed 17; do not claim this run demonstrates an applied replan.

**Demo B — saved synthetic S08 grid replanning:** run `venv/bin/python tools/verify_saved_replan.py`, then follow the safe extraction and viewer commands in the [README](../README.md#demo-b--verified-dynamic-replanning-separate-saved-s08-grid-run). Seek 301 → 311 → 316 → 425. It is not a test of the Chennai guard or live traffic benefit.

See the [five-minute walkthrough and two-minute fallback](../deliverables/final-academic-submission/FINAL_DEMO_CHECKLIST.md) and [demo readiness matrix](FINAL_DEMO_READINESS.md).

## Research interpretation

| Scenario | Static success | Dynamic success | Valid paired response-time result |
|---|---:|---:|---|
| S05 | 7/10 | 10/10 | Seven successful pairs; mean/median delta 0 s |
| S06 | 0/10 | 0/10 | None; all runs TELEPORTED |
| S08 | 0/10 | 10/10 | None; no successful static pairs |

Failures remain in denominators. The sample is small, synthetic and scenario-specific. It does not establish universal superiority, real-world emergency benefit, traffic-provider benefit or advisor performance.

## Remaining limitations and human actions

Live Chennai provider coverage/accuracy and billing remain unverified. There is no physical signal controller, real-camera accident detector, clinical capacity feed, citywide calibration or production safety certification. Browser GPS is display-only. Clinical admission and final driveway access are not tested. The project handles one configured emergency, not general multi-emergency operations.

The team must rehearse on the examination laptop and review native PowerPoint/Word rendering. Add institutional/guide/registration fields only if the submission form requires them and the details are supplied. Human review is required before any decision to merge PR #10; this task does not mark it ready or merge it.
