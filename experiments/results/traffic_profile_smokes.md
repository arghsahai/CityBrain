# SUMO experimental observations

Travel-time and ETA statistics exclude failures and teleports. No superiority claim is implied.

| Scenario | Profile | Strategy | Runs | Successes | Teleports | Mean travel s | Median travel s | SD s | Mean ETA error s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S05 | congested | dynamic | 1 | 1 | 0 | 34.00 | 34.00 | NA | 8.59 |
| S05 | congested | static | 1 | 1 | 0 | 34.00 | 34.00 | NA | 8.59 |
| S05 | heavy | dynamic | 1 | 1 | 0 | 34.00 | 34.00 | NA | 8.32 |
| S05 | heavy | static | 1 | 0 | 1 | NA | NA | NA | NA |
| S05 | peak | dynamic | 1 | 1 | 0 | 34.00 | 34.00 | NA | 8.01 |
| S05 | peak | static | 1 | 1 | 0 | 34.00 | 34.00 | NA | 8.01 |

Normal traffic metrics include completed and unfinished background vehicles over the same 900-second window.

| Scenario | Profile | Strategy | Mean waiting s | Mean time loss s | Mean throughput veh/h | Mean route changes | Mean planner computation ms |
|---|---|---|---:|---:|---:|---:|---:|
| S05 | congested | dynamic | 10.469 | 18.836 | 3400.000 | 0.000 | 1.216 |
| S05 | congested | static | 10.469 | 18.836 | 3400.000 | 0.000 | 0.067 |
| S05 | heavy | dynamic | 8.399 | 13.400 | 2008.000 | 1.000 | 0.998 |
| S05 | heavy | static | 8.331 | 13.251 | 2008.000 | 0.000 | 0.074 |
| S05 | peak | dynamic | 10.510 | 15.662 | 2624.000 | 0.000 | 1.052 |
| S05 | peak | static | 10.510 | 15.662 | 2624.000 | 0.000 | 0.054 |

95% Wilson intervals describe binomial success uncertainty; they are not superiority tests.

| Scenario | Profile | Strategy | Success rate | 95% Wilson interval |
|---|---|---|---:|---|
| S05 | congested | dynamic | 100.0% | 20.7%–100.0% |
| S05 | congested | static | 100.0% | 20.7%–100.0% |
| S05 | heavy | dynamic | 100.0% | 20.7%–100.0% |
| S05 | heavy | static | 0.0% | 0.0%–79.3% |
| S05 | peak | dynamic | 100.0% | 20.7%–100.0% |
| S05 | peak | static | 100.0% | 20.7%–100.0% |

All completion outcomes:

- S05 / congested / dynamic: {'SUCCESS': 1}
- S05 / congested / static: {'SUCCESS': 1}
- S05 / heavy / dynamic: {'SUCCESS': 1}
- S05 / heavy / static: {'TELEPORTED': 1}
- S05 / peak / dynamic: {'SUCCESS': 1}
- S05 / peak / static: {'SUCCESS': 1}
