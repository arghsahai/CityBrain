# V3 baseline smoke results

Fresh matched static/dynamic seed-1 runs on the existing SUMO harness. One seed per scenario is a smoke check only; it supports no response-improvement claim. The traffic-assisted evaluator is a sidecar and was not part of these route decisions. No provider request was made.

| Scenario | Static | Dynamic | Dynamic travel (s) | Dynamic route changes |
|---|---|---|---:|---:|
| S05 | TELEPORTED | SUCCESS | 34.0 | 1 |
| S06 | TELEPORTED | TELEPORTED | — | 1 |
| S08 | TELEPORTED | SUCCESS | 124.0 | 2 |

Input hash: `f52cdc9b170fefde0499bda1e94744c523ee4ad31c6b5fdaaf79319970bd9fed`. Run manifests identify SUMO version, scenario, seed, policy and horizon. Full compact trial metrics are in `results.csv`; raw simulator files remain in `/tmp/citybrain-v3-research-*`. Working tree had unrelated in-progress documentation/UI changes during execution; the runner input hash matches the recorded manifest.
