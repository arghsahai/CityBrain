# SUMO experimental observations

Travel-time and ETA statistics exclude failures and teleports. No superiority claim is implied. ERROR rows retain their outcome but have no traffic measurements.

| Scenario | Profile | Strategy | Runs | Successes | Teleports | Mean travel s | Median travel s | SD s | Mean ETA error s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S05 | normal | dynamic | 10 | 10 | 0 | 34.00 | 34.00 | 0.00 | 8.466 |
| S05 | normal | static | 10 | 7 | 3 | 34.00 | 34.00 | 0.00 | 8.473 |
| S06 | normal | dynamic | 10 | 0 | 10 | NA | NA | NA | NA |
| S06 | normal | static | 10 | 0 | 10 | NA | NA | NA | NA |
| S08 | normal | dynamic | 10 | 10 | 0 | 123.50 | 123.50 | 0.53 | 98.236 |
| S08 | normal | static | 10 | 0 | 10 | NA | NA | NA | NA |

| Scenario | Profile | Strategy | Failure rate | Teleport rate | Travel min s | Travel max s |
|---|---|---|---:|---:|---:|---:|
| S05 | normal | dynamic | 0.0 | 0.0 | 34.0 | 34.0 |
| S05 | normal | static | 0.3 | 0.3 | 34.0 | 34.0 |
| S06 | normal | dynamic | 1.0 | 1.0 | NA | NA |
| S06 | normal | static | 1.0 | 1.0 | NA | NA |
| S08 | normal | dynamic | 0.0 | 0.0 | 123.0 | 124.0 |
| S08 | normal | static | 1.0 | 1.0 | NA | NA |

Normal traffic metrics include completed and unfinished background trips in a common 900-second window.

| Scenario | Profile | Strategy | Mean waiting s | Mean time loss s | Throughput veh/h | Route changes | Planner computation ms | Replan checks |
|---|---|---|---:|---:|---:|---:|---:|---:|
| S05 | normal | dynamic | 7.912 | 12.646 | 1341.200 | 0.300 | 6.935 | 27.900 |
| S05 | normal | static | 7.911 | 12.646 | 1341.200 | 0.000 | 0.303 | 0.000 |
| S06 | normal | dynamic | 8.035 | 12.748 | 1340.400 | 1.700 | 64.964 | 325.600 |
| S06 | normal | static | 8.022 | 12.735 | 1340.400 | 0.000 | 0.259 | 0.000 |
| S08 | normal | dynamic | 8.003 | 12.711 | 1340.400 | 1.400 | 33.583 | 114.200 |
| S08 | normal | static | 8.008 | 12.714 | 1340.800 | 0.000 | 0.353 | 0.000 |

95% Wilson intervals describe binomial success uncertainty; they are not superiority tests.

| Scenario | Profile | Strategy | Success rate | 95% Wilson interval |
|---|---|---|---:|---|
| S05 | normal | dynamic | 100.0% | 72.2%–100.0% |
| S05 | normal | static | 70.0% | 39.7%–89.2% |
| S06 | normal | dynamic | 0.0% | 0.0%–27.8% |
| S06 | normal | static | 0.0% | 0.0%–27.8% |
| S08 | normal | dynamic | 100.0% | 72.2%–100.0% |
| S08 | normal | static | 0.0% | 0.0%–27.8% |

Paired travel differences (static minus dynamic, seconds) use only seeds where BOTH arrived. Read alongside all-run failure rates.

| Scenario | Profile | Successful pairs | Mean difference s | Median difference s | SD s | Min s | Max s |
|---|---|---:|---:|---:|---:|---:|---:|
| S05 | normal | 7 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

All completion outcomes:

- S05 / normal / dynamic: {'SUCCESS': 10}
- S05 / normal / static: {'SUCCESS': 7, 'TELEPORTED': 3}
- S06 / normal / dynamic: {'TELEPORTED': 10}
- S06 / normal / static: {'TELEPORTED': 10}
- S08 / normal / dynamic: {'SUCCESS': 10}
- S08 / normal / static: {'TELEPORTED': 10}
