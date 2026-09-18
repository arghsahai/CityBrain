# SUMO experimental observations

Travel-time and ETA statistics exclude failures and teleports. No superiority claim is implied.

| Scenario | Profile | Strategy | Runs | Successes | Teleports | Mean travel s | Median travel s | SD s | Mean ETA error s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S07 | normal | dynamic | 10 | 10 | 0 | 34.00 | 34.00 | 0.00 | 8.47 |
| S07 | normal | static | 10 | 10 | 0 | 53.00 | 34.00 | 30.61 | 27.47 |

Normal traffic metrics include completed and unfinished background vehicles over the same 900-second window.

| Scenario | Profile | Strategy | Mean waiting s | Mean time loss s | Mean throughput veh/h | Mean route changes | Mean planner computation ms |
|---|---|---|---:|---:|---:|---:|---:|
| S07 | normal | dynamic | 13.218 | 23.247 | 1537.600 | 0.300 | 0.876 |
| S07 | normal | static | 13.217 | 23.251 | 1537.200 | 0.000 | 0.046 |

95% Wilson intervals describe binomial success uncertainty; they are not superiority tests.

| Scenario | Profile | Strategy | Success rate | 95% Wilson interval |
|---|---|---|---:|---|
| S07 | normal | dynamic | 100.0% | 72.2%–100.0% |
| S07 | normal | static | 100.0% | 72.2%–100.0% |

All completion outcomes:

- S07 / normal / dynamic: {'SUCCESS': 10}
- S07 / normal / static: {'SUCCESS': 10}
