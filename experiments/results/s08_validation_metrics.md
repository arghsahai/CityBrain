# SUMO experimental observations

Travel-time and ETA statistics exclude failures and teleports. No superiority claim is implied. ERROR rows retain their outcome but have no traffic measurements.

| Scenario | Profile | Strategy | Runs | Successes | Teleports | Mean travel s | Median travel s | SD s | Mean ETA error s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S08 | heavy | dynamic | 10 | 10 | 0 | 123.50 | 123.50 | 0.53 | 98.008 |
| S08 | heavy | static | 10 | 0 | 10 | NA | NA | NA | NA |
| S08 | normal | dynamic | 10 | 10 | 0 | 123.50 | 123.50 | 0.53 | 98.236 |
| S08 | normal | static | 10 | 0 | 10 | NA | NA | NA | NA |
| S08 | peak | dynamic | 10 | 10 | 0 | 123.50 | 123.50 | 0.53 | 98.004 |
| S08 | peak | static | 10 | 0 | 10 | NA | NA | NA | NA |

| Scenario | Profile | Strategy | Failure rate | Teleport rate | Travel min s | Travel max s |
|---|---|---|---:|---:|---:|---:|
| S08 | heavy | dynamic | 0.0 | 0.0 | 123.0 | 124.0 |
| S08 | heavy | static | 1.0 | 1.0 | NA | NA |
| S08 | normal | dynamic | 0.0 | 0.0 | 123.0 | 124.0 |
| S08 | normal | static | 1.0 | 1.0 | NA | NA |
| S08 | peak | dynamic | 0.0 | 0.0 | 123.0 | 124.0 |
| S08 | peak | static | 1.0 | 1.0 | NA | NA |

Normal traffic metrics include completed and unfinished background trips in a common 900-second window.

| Scenario | Profile | Strategy | Mean waiting s | Mean time loss s | Throughput veh/h | Route changes | Planner computation ms | Replan checks |
|---|---|---|---:|---:|---:|---:|---:|---:|
| S08 | heavy | dynamic | 8.271 | 13.153 | 2011.200 | 1.800 | 2.312 | 114.300 |
| S08 | heavy | static | 8.246 | 13.130 | 2011.200 | 0.000 | 0.045 | 0.000 |
| S08 | normal | dynamic | 8.003 | 12.711 | 1340.400 | 1.400 | 2.543 | 114.200 |
| S08 | normal | static | 8.008 | 12.714 | 1340.800 | 0.000 | 0.047 | 0.000 |
| S08 | peak | dynamic | 10.457 | 15.563 | 2618.800 | 1.800 | 2.314 | 114.300 |
| S08 | peak | static | 10.448 | 15.536 | 2616.400 | 0.000 | 0.048 | 0.000 |

95% Wilson intervals describe binomial success uncertainty; they are not superiority tests.

| Scenario | Profile | Strategy | Success rate | 95% Wilson interval |
|---|---|---|---:|---|
| S08 | heavy | dynamic | 100.0% | 72.2%–100.0% |
| S08 | heavy | static | 0.0% | 0.0%–27.8% |
| S08 | normal | dynamic | 100.0% | 72.2%–100.0% |
| S08 | normal | static | 0.0% | 0.0%–27.8% |
| S08 | peak | dynamic | 100.0% | 72.2%–100.0% |
| S08 | peak | static | 0.0% | 0.0%–27.8% |

Paired travel differences (static minus dynamic, seconds) use only seeds where BOTH arrived. Read alongside all-run failure rates.

| Scenario | Profile | Successful pairs | Mean difference s | Median difference s | SD s | Min s | Max s |
|---|---|---:|---:|---:|---:|---:|---:|

All completion outcomes:

- S08 / heavy / dynamic: {'SUCCESS': 10}
- S08 / heavy / static: {'TELEPORTED': 10}
- S08 / normal / dynamic: {'SUCCESS': 10}
- S08 / normal / static: {'TELEPORTED': 10}
- S08 / peak / dynamic: {'SUCCESS': 10}
- S08 / peak / static: {'TELEPORTED': 10}
