# Integration validation

Historical results remain on feature/krishna-simulation at 8d42c5f. They are not measurements of this main-based integration. Fresh validation is recorded below.

## Initial main-based integration checkpoint

All seven scenarios were executed as paired static/dynamic seed-1 trials. S01 is not an emergency experiment. S02/S03/S04 arrived under both strategies. S05 static teleported; dynamic arrived in 34 s. S06 both teleported due to exhausted candidate routes. S07 static arrived in 96 s and dynamic in 34 s. Heavy, peak and congested S05 profiles were also checked with seed 1. These are smoke observations, not ten-seed integration claims.

Five assertion-based tests passed; ten unchanged teammate top-level scripts executed successfully. All nine regression signals were read, changed and restored using TraCI. Full matrix remains unexecuted at this checkpoint.

## Completed validation checkpoint — 19 September 2026

The 120-run controlled matrix is complete: S05/S07 × normal/heavy/peak × seeds 1–10 × static/dynamic. The recovery audit found all runs already complete and reran none. All 60 pairs have byte-identical generated demand XML, identical initial routes/ETAs and matching execution/input fingerprints. All 18 teleports remain in the data; there are 102 SUCCESS outcomes and no ERROR outcomes.

| Scenario / metric | Normal | Heavy | Peak |
|---|---:|---:|---:|
| S05 static success | 7/10 | 3/10 | 2/10 |
| S05 dynamic success | 10/10 | 10/10 | 10/10 |
| S07 static mean successful travel (s) | 53.0 | 78.6 | 85.1 |
| S07 dynamic mean successful travel (s) | 34.0 | 34.0 | 34.0 |

All S07 runs succeeded. S05 successful trips took 34 s under both strategies; static failures must not be hidden by that conditional average. These are synthetic, scenario-specific observations. Statistics include all outcome rates, successful-trip spread and paired differences; no significance or general superiority is claimed.

Tracked artifacts: validation_matrix.csv, validation_matrix_statistics.csv, validation_matrix.md, validation_manifest.json and three PNG charts. Original per-run manifests, configs, trip XML, decision logs and checkpoints remain in the ignored matrix-normal/matrix-heavy/matrix-peak directories. Runtime summed across all trials was 485.86 s under concurrent execution; raw matrix output occupies approximately 30.7 MB. The recorded Git commit identifies the integration base at launch; input_sha256 identifies the exact execution code and inputs, including then-uncommitted changes subsequently committed in 193cff6/df36103. The recovery audit verified that fingerprint against the current tree.

Resume was exercised on all 40 completed normal-profile runs: all were loaded from checkpoints, with zero SUMO launches. Unit tests also verify input mismatch rejection and retention of ERROR rows with blank unavailable metrics.

S06 remains a deliberate disconnected-network regression: E3/E7/E11 cut all eastbound access to J9. S08 adds a separate 3×4 research network with a northern bypass. Its seed-1 dynamic demo applied P1 at 311 s and P2 at 321 s, arriving at 425 s (124 s after dispatch). The larger network changes signal behavior and is not directly comparable with S05 travel times. Main's planner code is unchanged.

The actual sumo-gui S05 command completed successfully, with P0 dispatch at 301 s, one physical route change at 311 s and arrival at 335 s. XQuartz required startup retries and emitted font warnings, but the simulation completed and wrote valid metrics. Headless S08 also completed with two physical route changes. demo_validation.json preserves both outcomes and selected actual event records. GUI visual inspection through the computer-use tool timed out; completion is verified from the GUI process's TraCI execution and saved outputs.

Final checks: 12 assertion-based tests pass; all 10 unchanged teammate scripts execute successfully. The original five tests remain covered. Argh's outstanding branch was not merged or copied; Subhashini's agents/planner/models and main's original network sources remain unchanged.

The optional full 560-run suite was considered but is not part of this completed 120-run validation checkpoint. At the observed average, 560 trials would total approximately 38 minutes of trial wall time before concurrency effects; scenario/demand differences make that only a rough estimate. Its additional scenarios have smoke coverage, not ten-seed validation. No full-suite result is claimed. Future execution should preserve/reuse valid matching checkpoints rather than repeat the 120 completed trials.

Software + SUMO only. Hardware, real sensing, physical signal control, simultaneous emergency allocation and a team-defined signal-priority execution contract remain future work.
