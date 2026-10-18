# Final demo readiness

18 October 2026. Verdict: **READY_WITH_DOCUMENTED_LIMITATIONS**.

| Check | Result | Evidence / boundary |
|---|---|---|
| Existing local dependency environment | PASS | Python 3.13.5, SUMO 1.27.1, Chrome 155 on macOS |
| Installation on a new examination laptop | NOT_TESTED | Existing environment used; team must install/rehearse there |
| No mandatory paid services or secrets | PASS | Local simulation and synthetic replay; zero provider requests |
| Core emergency/dispatch/route execution | PASS | Fresh normal SUCCESS 704 s, exact read-back and arrival-road audit |
| Replanning demonstrated separately | PASS | Preserved S08 archive, verified P0/P1/P2 and Chrome replay |
| Teleport/no-route/failure classification | PASS | Runtime/guard/executor regression suite |
| 20-second guard and hard failure handling | PASS | Existing tests plus observed guarded KEEP at 61 s |
| Cesium movement, geometry and signals | PASS | Browser/backend comparison and changing telemetry |
| SVG fallback and 800/390 px layout | PASS | Real Chrome headless screenshots and no horizontal overflow |
| Terminal display agrees with SUMO | PASS | SUCCESS note, inactive vehicle absent, no fabricated current fix |
| Traffic labels and provider isolation | PASS | Synthetic replay labels, missing/expired source cases, advisor tests |
| Closure lifecycle / future-clock recovery | PASS | Browser/backend 1→0→1 markers, quarantine and valid reopening |
| Browser GPS privacy | PASS | Consent/Stop and error cases emulated; no actual user location read |
| Replay works without a running SUMO process | PASS | Saved S08 viewer and completed Chennai output |
| Interactive launcher URL and completed-server shutdown | PASS | Actual SUMO run served SUCCESS at 704 s; Ctrl-C exit zero and port released |
| Replay shutdown and same-port second launch | PASS | Ctrl-C exit zero, second 8799 server returned state, closed again |
| Full tests and compatibility | PASS | 447 pytest; ten scripts exit zero |
| Historical evidence and V3.1 study preservation | PASS | 2,172 entries and 426 study files unchanged |
| PPTX/DOCX/PDF renders and screenshots | PASS | 12 slides; report sections/render verification; genuine replay images |
| Native Office / presentation on examination laptop | USER_ACTION_REQUIRED | File/import/render checks do not replace that laptop's rehearsal |
| Real provider traffic, clinical capacity, physical signals | NOT_TESTED | Explicitly outside the demonstrated research prototype |
| Human approval of PR #10 | USER_ACTION_REQUIRED | PR remains Draft and unmerged |

No unresolved core-workflow or demonstration blocker was reproduced. Do not describe NOT_TESTED capabilities as verified. The [final checklist](../deliverables/final-academic-submission/FINAL_DEMO_CHECKLIST.md) supplies exact commands and timing.
