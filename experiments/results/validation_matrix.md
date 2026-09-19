# SUMO experimental observations

Travel-time and ETA statistics exclude failures and teleports. No superiority claim is implied. ERROR rows retain their outcome but have no traffic measurements.

| Scenario | Profile | Strategy | Runs | Successes | Teleports | Mean travel s | Median travel s | SD s | Mean ETA error s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S05 | heavy | dynamic | 10 | 10 | 0 | 34.00 | 34.00 | 0.00 | 8.191 |
| S05 | heavy | static | 10 | 3 | 7 | 34.00 | 34.00 | 0.00 | 7.729 |
| S05 | normal | dynamic | 10 | 10 | 0 | 34.00 | 34.00 | 0.00 | 8.466 |
| S05 | normal | static | 10 | 7 | 3 | 34.00 | 34.00 | 0.00 | 8.473 |
| S05 | peak | dynamic | 10 | 10 | 0 | 34.00 | 34.00 | 0.00 | 8.345 |
| S05 | peak | static | 10 | 2 | 8 | 34.00 | 34.00 | 0.00 | 8.040 |
| S07 | heavy | dynamic | 10 | 10 | 0 | 34.00 | 34.00 | 0.00 | 8.191 |
| S07 | heavy | static | 10 | 10 | 0 | 78.60 | 97.00 | 30.79 | 52.791 |
| S07 | normal | dynamic | 10 | 10 | 0 | 34.00 | 34.00 | 0.00 | 8.466 |
| S07 | normal | static | 10 | 10 | 0 | 53.00 | 34.00 | 30.61 | 27.466 |
| S07 | peak | dynamic | 10 | 10 | 0 | 34.00 | 34.00 | 0.00 | 8.345 |
| S07 | peak | static | 10 | 10 | 0 | 85.10 | 97.00 | 26.96 | 59.445 |

| Scenario | Profile | Strategy | Failure rate | Teleport rate | Travel min s | Travel max s |
|---|---|---|---:|---:|---:|---:|
| S05 | heavy | dynamic | 0.0 | 0.0 | 34.0 | 34.0 |
| S05 | heavy | static | 0.7 | 0.7 | 34.0 | 34.0 |
| S05 | normal | dynamic | 0.0 | 0.0 | 34.0 | 34.0 |
| S05 | normal | static | 0.3 | 0.3 | 34.0 | 34.0 |
| S05 | peak | dynamic | 0.0 | 0.0 | 34.0 | 34.0 |
| S05 | peak | static | 0.8 | 0.8 | 34.0 | 34.0 |
| S07 | heavy | dynamic | 0.0 | 0.0 | 34.0 | 34.0 |
| S07 | heavy | static | 0.0 | 0.0 | 34.0 | 100.0 |
| S07 | normal | dynamic | 0.0 | 0.0 | 34.0 | 34.0 |
| S07 | normal | static | 0.0 | 0.0 | 34.0 | 100.0 |
| S07 | peak | dynamic | 0.0 | 0.0 | 34.0 | 34.0 |
| S07 | peak | static | 0.0 | 0.0 | 34.0 | 100.0 |

Normal traffic metrics include completed and unfinished background trips in a common 900-second window.

| Scenario | Profile | Strategy | Mean waiting s | Mean time loss s | Throughput veh/h | Route changes | Planner computation ms | Replan checks |
|---|---|---|---:|---:|---:|---:|---:|---:|
| S05 | heavy | dynamic | 8.311 | 13.256 | 2009.600 | 0.700 | 1.040 | 28.000 |
| S05 | heavy | static | 8.314 | 13.243 | 2009.600 | 0.000 | 0.048 | 0.000 |
| S05 | normal | dynamic | 7.912 | 12.646 | 1341.200 | 0.300 | 0.981 | 27.900 |
| S05 | normal | static | 7.911 | 12.646 | 1341.200 | 0.000 | 0.046 | 0.000 |
| S05 | peak | dynamic | 10.454 | 15.573 | 2620.000 | 0.800 | 1.132 | 28.000 |
| S05 | peak | static | 10.455 | 15.563 | 2618.800 | 0.000 | 0.047 | 0.000 |
| S07 | heavy | dynamic | 12.094 | 21.891 | 2206.400 | 0.700 | 0.968 | 28.100 |
| S07 | heavy | static | 12.052 | 21.800 | 2204.800 | 0.000 | 0.050 | 0.000 |
| S07 | normal | dynamic | 13.218 | 23.247 | 1537.600 | 0.300 | 1.077 | 27.900 |
| S07 | normal | static | 13.217 | 23.251 | 1537.200 | 0.000 | 0.045 | 0.000 |
| S07 | peak | dynamic | 15.640 | 26.308 | 2748.400 | 0.800 | 0.925 | 28.000 |
| S07 | peak | static | 15.737 | 26.347 | 2742.000 | 0.000 | 0.047 | 0.000 |

95% Wilson intervals describe binomial success uncertainty; they are not superiority tests.

| Scenario | Profile | Strategy | Success rate | 95% Wilson interval |
|---|---|---|---:|---|
| S05 | heavy | dynamic | 100.0% | 72.2%–100.0% |
| S05 | heavy | static | 30.0% | 10.8%–60.3% |
| S05 | normal | dynamic | 100.0% | 72.2%–100.0% |
| S05 | normal | static | 70.0% | 39.7%–89.2% |
| S05 | peak | dynamic | 100.0% | 72.2%–100.0% |
| S05 | peak | static | 20.0% | 5.7%–51.0% |
| S07 | heavy | dynamic | 100.0% | 72.2%–100.0% |
| S07 | heavy | static | 100.0% | 72.2%–100.0% |
| S07 | normal | dynamic | 100.0% | 72.2%–100.0% |
| S07 | normal | static | 100.0% | 72.2%–100.0% |
| S07 | peak | dynamic | 100.0% | 72.2%–100.0% |
| S07 | peak | static | 100.0% | 72.2%–100.0% |

Paired travel differences (static minus dynamic, seconds) use only seeds where BOTH arrived. Read alongside all-run failure rates.

| Scenario | Profile | Successful pairs | Mean difference s | Median difference s | SD s | Min s | Max s |
|---|---|---:|---:|---:|---:|---:|---:|
| S05 | heavy | 3 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| S05 | normal | 7 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| S05 | peak | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| S07 | heavy | 10 | 44.60 | 63.00 | 30.79 | 0.00 | 66.00 |
| S07 | normal | 10 | 19.00 | 0.00 | 30.61 | 0.00 | 66.00 |
| S07 | peak | 10 | 51.10 | 63.00 | 26.96 | 0.00 | 66.00 |

All completion outcomes:

- S05 / heavy / dynamic: {'SUCCESS': 10}
- S05 / heavy / static: {'SUCCESS': 3, 'TELEPORTED': 7}
- S05 / normal / dynamic: {'SUCCESS': 10}
- S05 / normal / static: {'SUCCESS': 7, 'TELEPORTED': 3}
- S05 / peak / dynamic: {'SUCCESS': 10}
- S05 / peak / static: {'SUCCESS': 2, 'TELEPORTED': 8}
- S07 / heavy / dynamic: {'SUCCESS': 10}
- S07 / heavy / static: {'SUCCESS': 10}
- S07 / normal / dynamic: {'SUCCESS': 10}
- S07 / normal / static: {'SUCCESS': 10}
- S07 / peak / dynamic: {'SUCCESS': 10}
- S07 / peak / static: {'SUCCESS': 10}
