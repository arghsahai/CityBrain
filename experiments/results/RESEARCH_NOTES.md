# Validation observations — 19 September 2026

Software + SUMO only. These are controlled synthetic experiments, not proof of performance in real cities.

Ten paired seeds (1–10), normal demand, 900-second common observation windows:

| Scenario | Static success | Dynamic success | Static successful travel mean | Dynamic successful travel mean |
|---|---:|---:|---:|---:|
| S05 downstream stopped blocker | 7/10 | 10/10 | 34 s | 34 s |
| S07 moving congestion | 10/10 | 10/10 | 53 s | 34 s |

S05 static trials 1, 3 and 10 teleported; no arrival or travel time was assigned to them. The other seeds initially selected an E7-avoiding route. Thus the equal successful-trip means should be read alongside failure rates. Dynamic planning applied one route change in each affected seed.

S07 static travel times were 96, 34, 100, 34, 34, 34, 34, 34, 34 and 96 seconds; all dynamic travel times were 34 seconds. Seven seeds already used the alternative route at dispatch. S07 retained nonzero moving traffic on E7 rather than marking it blocked. Dynamic decisions used a 10-second commitment and 5-second/15% predicted-benefit gates. This shows congestion-based evaluation in the tested setup without establishing a general superiority claim.

The saved Markdown summaries include ETA error, travel-time mean/median/SD, normal-traffic effects, route-change counts, computation times and Wilson success intervals. Computation measurements vary with machine load and are summed across calls; they are distinct from simulation-time route-application delay. The profile checks use one seed each and are smoke tests only, not statistical comparisons.

All seven scenario variants were smoke-tested with seed 1. S06 exhausts the existing reachable candidate routes after E7 and E11 become blocked: both strategies teleport. Dynamic logs preserve evaluation and unavailable-candidate evidence. Broader route enumeration and simultaneous emergency allocation need teammate integration; they were not fabricated in the simulation harness.

The actual per-trial generated configs, SUMO trip information and event logs are retained in ignored validation directories under `experiments/results/`; compact CSVs, summaries and charts are tracked. S05 validation preceded the addition of edge sampling and manifest logging; S07 validation includes those extra artifacts. Both used the same one-second evaluation policy and stability gates. Rerun the README commands for a complete fresh artifact set.

The full 560-run scenario × profile × seed × strategy suite is automated but has not been executed in this validation. Ten-seed comparisons were completed for S05 and S07; other scenario/profile checks are explicitly limited to smoke coverage.

The two legacy `s05_dynamic_replanning.csv` and `s05_static_baseline.csv` files predate the outcome fix. They are historical artifacts and not evidence for this evaluation.
