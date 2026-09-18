# SUMO experimental observations

Travel-time and ETA statistics exclude failures and teleports. No superiority claim is implied.

| Scenario | Profile | Strategy | Runs | Successes | Teleports | Mean travel s | Median travel s | SD s | Mean ETA error s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S05 | normal | dynamic | 10 | 10 | 0 | 34.00 | 34.00 | 0.00 | 8.47 |
| S05 | normal | static | 10 | 7 | 3 | 34.00 | 34.00 | 0.00 | 8.47 |

Normal traffic metrics include completed and unfinished background vehicles over the same 900-second window.

| Scenario | Profile | Strategy | Mean waiting s | Mean time loss s | Mean throughput veh/h | Mean route changes | Mean planner computation ms |
|---|---|---|---:|---:|---:|---:|---:|
| S05 | normal | dynamic | 7.912 | 12.646 | 1341.200 | 0.300 | 0.748 |
| S05 | normal | static | 7.911 | 12.646 | 1341.200 | 0.000 | 0.045 |

95% Wilson intervals describe binomial success uncertainty; they are not superiority tests.

| Scenario | Profile | Strategy | Success rate | 95% Wilson interval |
|---|---|---|---:|---|
| S05 | normal | dynamic | 100.0% | 72.2%–100.0% |
| S05 | normal | static | 70.0% | 39.7%–89.2% |

All completion outcomes:

- S05 / normal / dynamic: {'SUCCESS': 10}
- S05 / normal / static: {'SUCCESS': 7, 'TELEPORTED': 3}
