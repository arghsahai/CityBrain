# SUMO experimental observations

Travel-time and ETA statistics exclude failures and teleports. No superiority claim is implied.

| Scenario | Profile | Strategy | Runs | Successes | Teleports | Mean travel s | Median travel s | SD s | Mean ETA error s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S01 | normal | dynamic | 1 | 0 | 0 | NA | NA | NA | NA |
| S01 | normal | static | 1 | 0 | 0 | NA | NA | NA | NA |
| S02 | normal | dynamic | 1 | 1 | 0 | 32.00 | 32.00 | NA | 6.22 |
| S02 | normal | static | 1 | 1 | 0 | 32.00 | 32.00 | NA | 6.22 |
| S03 | normal | dynamic | 1 | 1 | 0 | 32.00 | 32.00 | NA | 6.32 |
| S03 | normal | static | 1 | 1 | 0 | 32.00 | 32.00 | NA | 6.32 |
| S04 | normal | dynamic | 1 | 1 | 0 | 34.00 | 34.00 | NA | 8.66 |
| S04 | normal | static | 1 | 1 | 0 | 34.00 | 34.00 | NA | 8.66 |
| S05 | normal | dynamic | 1 | 1 | 0 | 34.00 | 34.00 | NA | 8.22 |
| S05 | normal | static | 1 | 0 | 1 | NA | NA | NA | NA |
| S06 | normal | dynamic | 1 | 0 | 1 | NA | NA | NA | NA |
| S06 | normal | static | 1 | 0 | 1 | NA | NA | NA | NA |
| S07 | normal | dynamic | 1 | 1 | 0 | 34.00 | 34.00 | NA | 8.22 |
| S07 | normal | static | 1 | 1 | 0 | 96.00 | 96.00 | NA | 70.22 |

Normal traffic metrics include completed and unfinished background vehicles over the same 900-second window.

| Scenario | Profile | Strategy | Mean waiting s | Mean time loss s | Mean throughput veh/h | Mean route changes | Mean planner computation ms |
|---|---|---|---:|---:|---:|---:|---:|
| S01 | normal | dynamic | 8.117 | 12.903 | 1340.000 | 0.000 | 0.000 |
| S01 | normal | static | 8.117 | 12.903 | 1340.000 | 0.000 | 0.000 |
| S02 | normal | dynamic | 8.140 | 12.911 | 1340.000 | 0.000 | 0.215 |
| S02 | normal | static | 8.140 | 12.911 | 1340.000 | 0.000 | 0.063 |
| S03 | normal | dynamic | 8.105 | 13.025 | 2012.000 | 0.000 | 1.171 |
| S03 | normal | static | 8.105 | 13.025 | 2012.000 | 0.000 | 0.068 |
| S04 | normal | dynamic | 8.034 | 12.843 | 1344.000 | 0.000 | 0.962 |
| S04 | normal | static | 8.034 | 12.843 | 1344.000 | 0.000 | 0.063 |
| S05 | normal | dynamic | 8.014 | 12.816 | 1344.000 | 1.000 | 0.605 |
| S05 | normal | static | 8.014 | 12.815 | 1344.000 | 0.000 | 0.049 |
| S06 | normal | dynamic | 8.162 | 12.927 | 1340.000 | 1.000 | 7.393 |
| S06 | normal | static | 8.160 | 12.926 | 1340.000 | 0.000 | 0.047 |
| S07 | normal | dynamic | 13.362 | 23.336 | 1540.000 | 1.000 | 0.663 |
| S07 | normal | static | 13.288 | 23.271 | 1540.000 | 0.000 | 0.042 |

95% Wilson intervals describe binomial success uncertainty; they are not superiority tests.

| Scenario | Profile | Strategy | Success rate | 95% Wilson interval |
|---|---|---|---:|---|
| S02 | normal | dynamic | 100.0% | 20.7%–100.0% |
| S02 | normal | static | 100.0% | 20.7%–100.0% |
| S03 | normal | dynamic | 100.0% | 20.7%–100.0% |
| S03 | normal | static | 100.0% | 20.7%–100.0% |
| S04 | normal | dynamic | 100.0% | 20.7%–100.0% |
| S04 | normal | static | 100.0% | 20.7%–100.0% |
| S05 | normal | dynamic | 100.0% | 20.7%–100.0% |
| S05 | normal | static | 0.0% | 0.0%–79.3% |
| S06 | normal | dynamic | 0.0% | 0.0%–79.3% |
| S06 | normal | static | 0.0% | 0.0%–79.3% |
| S07 | normal | dynamic | 100.0% | 20.7%–100.0% |
| S07 | normal | static | 100.0% | 20.7%–100.0% |

All completion outcomes:

- S01 / normal / dynamic: {'NOT_APPLICABLE': 1}
- S01 / normal / static: {'NOT_APPLICABLE': 1}
- S02 / normal / dynamic: {'SUCCESS': 1}
- S02 / normal / static: {'SUCCESS': 1}
- S03 / normal / dynamic: {'SUCCESS': 1}
- S03 / normal / static: {'SUCCESS': 1}
- S04 / normal / dynamic: {'SUCCESS': 1}
- S04 / normal / static: {'SUCCESS': 1}
- S05 / normal / dynamic: {'SUCCESS': 1}
- S05 / normal / static: {'TELEPORTED': 1}
- S06 / normal / dynamic: {'TELEPORTED': 1}
- S06 / normal / static: {'TELEPORTED': 1}
- S07 / normal / dynamic: {'SUCCESS': 1}
- S07 / normal / static: {'SUCCESS': 1}
