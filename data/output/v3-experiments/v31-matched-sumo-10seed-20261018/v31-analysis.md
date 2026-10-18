# V3.1 matched SUMO experiment analysis

Protocol: [`V31_EXPERIMENT_PROTOCOL.md`](../../../../docs/V31_EXPERIMENT_PROTOCOL.md).
Provenance: SUMO simulation only; no provider response, GPS runtime input, signal actuation or traffic-advisor selection.
Matrix: 60 trials (3 scenarios × 10 seeds × 2 implemented arms); every recorded terminal outcome is included.

| Scenario | Policy | n | SUCCESS | TELEPORTED | Other statuses | Success Wilson 95% | Successful response time mean (n) |
|---|---|---:|---:|---:|---|---|---:|
| S05 | static | 10 | 7 | 3 | none | 39.7%–89.2% | 35.00 (7) s |
| S05 | dynamic | 10 | 10 | 0 | none | 72.2%–100.0% | 35.00 (10) s |
| S06 | static | 10 | 0 | 10 | none | 0.0%–27.8% | NA s |
| S06 | dynamic | 10 | 0 | 10 | none | 0.0%–27.8% | NA s |
| S08 | static | 10 | 0 | 10 | none | 0.0%–27.8% | NA s |
| S08 | dynamic | 10 | 10 | 0 | none | 72.2%–100.0% | 124.50 (10) s |

## Matched successful response-time differences

Differences are static minus dynamic and include only seeds where both policies succeeded. Failed pairs remain represented above; they do not receive invented travel times.

| Scenario | Successful pairs | Mean difference (s) | Median (s) | Bootstrap 95% interval (s) |
|---|---:|---:|---:|---|
| S05 | 7 | 0.0 | 0.0 | [0.0, 0.0] |
| S06 | 0 | Unavailable | Unavailable | Unavailable: no matched successes |
| S08 | 0 | Unavailable | Unavailable | Unavailable: no matched successes |

## Interpretation and limits

- 10 matched seeds per scenario; one normal-demand profile and fixed synthetic inputs.
- Results do not test live traffic, the experimental traffic advisor, signal priority or GPS.
- Successful response-time summaries condition on SUCCESS; failures remain in completion denominators.
- N=10 intervals are broad; these scenario results do not establish general superiority or real-world performance.

Replanning latency, route changes and planner computation are retained in `results.csv`; traffic freshness, geometry coverage and physical route read-back are not measured by this legacy static/dynamic harness. The dynamic arm has better observed completion in S05 and S08 in this sample, while S06 teleports in both arms. These outcomes are exploratory observations, not a general performance or operational claim.
