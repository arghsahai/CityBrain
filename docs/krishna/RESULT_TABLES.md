# Final research result tables

Derived without rerunning trials. Sources: `experiments/results/validation_matrix.csv`, `s08_validation.csv`, and audited S08 V2 per-trial events. Successful-only timing is conditional on arrival; failure denominators always include all trials. SD is sample SD (n−1). No static S08 travel comparison is possible.

## 1. Trial-count audit

| Dataset | Scenarios | Profiles | Seeds | Modes | Trials | Matched pairs |
|---|---|---|---|---|---|---|
| PR #3 baseline | S05 + S07 | 3 | 10 | 2 | 120 | 60 |
| PR #4 official V2 | S08 | 3 | 10 | 2 | 60 | 30 |
| Inventory total (not pooled effect) | 3 scenario families | 3 | 10 | 2 | 180 | 90 |

## 2. Success rates

| Scenario | Profile | Mode | Success/all trials | Rate |
|---|---|---|---|---|
| S05 | normal | static | 7/10 | 70.0% |
| S05 | normal | dynamic | 10/10 | 100.0% |
| S05 | heavy | static | 3/10 | 30.0% |
| S05 | heavy | dynamic | 10/10 | 100.0% |
| S05 | peak | static | 2/10 | 20.0% |
| S05 | peak | dynamic | 10/10 | 100.0% |
| S07 | normal | static | 10/10 | 100.0% |
| S07 | normal | dynamic | 10/10 | 100.0% |
| S07 | heavy | static | 10/10 | 100.0% |
| S07 | heavy | dynamic | 10/10 | 100.0% |
| S07 | peak | static | 10/10 | 100.0% |
| S07 | peak | dynamic | 10/10 | 100.0% |
| S08 | normal | static | 0/10 | 0.0% |
| S08 | normal | dynamic | 10/10 | 100.0% |
| S08 | heavy | static | 0/10 | 0.0% |
| S08 | heavy | dynamic | 10/10 | 100.0% |
| S08 | peak | static | 0/10 | 0.0% |
| S08 | peak | dynamic | 10/10 | 100.0% |

## 3. Successful emergency travel time (seconds)

| Scenario | Profile | Mode | Successful/all | Mean | Median | Sample SD | Min | Max |
|---|---|---|---|---|---|---|---|---|
| S05 | normal | static | 7/10 | 34.00 | 34.00 | 0.00 | 34.00 | 34.00 |
| S05 | normal | dynamic | 10/10 | 34.00 | 34.00 | 0.00 | 34.00 | 34.00 |
| S05 | heavy | static | 3/10 | 34.00 | 34.00 | 0.00 | 34.00 | 34.00 |
| S05 | heavy | dynamic | 10/10 | 34.00 | 34.00 | 0.00 | 34.00 | 34.00 |
| S05 | peak | static | 2/10 | 34.00 | 34.00 | 0.00 | 34.00 | 34.00 |
| S05 | peak | dynamic | 10/10 | 34.00 | 34.00 | 0.00 | 34.00 | 34.00 |
| S07 | normal | static | 10/10 | 53.00 | 34.00 | 30.61 | 34.00 | 100.00 |
| S07 | normal | dynamic | 10/10 | 34.00 | 34.00 | 0.00 | 34.00 | 34.00 |
| S07 | heavy | static | 10/10 | 78.60 | 97.00 | 30.79 | 34.00 | 100.00 |
| S07 | heavy | dynamic | 10/10 | 34.00 | 34.00 | 0.00 | 34.00 | 34.00 |
| S07 | peak | static | 10/10 | 85.10 | 97.00 | 26.96 | 34.00 | 100.00 |
| S07 | peak | dynamic | 10/10 | 34.00 | 34.00 | 0.00 | 34.00 | 34.00 |
| S08 | normal | static | 0/10 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| S08 | normal | dynamic | 10/10 | 123.50 | 123.50 | 0.53 | 123.00 | 124.00 |
| S08 | heavy | static | 0/10 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| S08 | heavy | dynamic | 10/10 | 123.50 | 123.50 | 0.53 | 123.00 | 124.00 |
| S08 | peak | static | 0/10 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| S08 | peak | dynamic | 10/10 | 123.50 | 123.50 | 0.53 | 123.00 | 124.00 |

## 4. Failure counts (all-trial denominators)

| Scenario | Profile | Mode | N | TELEPORTED | ERROR | TIMEOUT | NO_ROUTE | FAILED_BLOCKED |
|---|---|---|---|---|---|---|---|---|
| S05 | normal | static | 10 | 3 | 0 | 0 | 0 | 0 |
| S05 | normal | dynamic | 10 | 0 | 0 | 0 | 0 | 0 |
| S05 | heavy | static | 10 | 7 | 0 | 0 | 0 | 0 |
| S05 | heavy | dynamic | 10 | 0 | 0 | 0 | 0 | 0 |
| S05 | peak | static | 10 | 8 | 0 | 0 | 0 | 0 |
| S05 | peak | dynamic | 10 | 0 | 0 | 0 | 0 | 0 |
| S07 | normal | static | 10 | 0 | 0 | 0 | 0 | 0 |
| S07 | normal | dynamic | 10 | 0 | 0 | 0 | 0 | 0 |
| S07 | heavy | static | 10 | 0 | 0 | 0 | 0 | 0 |
| S07 | heavy | dynamic | 10 | 0 | 0 | 0 | 0 | 0 |
| S07 | peak | static | 10 | 0 | 0 | 0 | 0 | 0 |
| S07 | peak | dynamic | 10 | 0 | 0 | 0 | 0 | 0 |
| S08 | normal | static | 10 | 10 | 0 | 0 | 0 | 0 |
| S08 | normal | dynamic | 10 | 0 | 0 | 0 | 0 | 0 |
| S08 | heavy | static | 10 | 10 | 0 | 0 | 0 | 0 |
| S08 | heavy | dynamic | 10 | 0 | 0 | 0 | 0 | 0 |
| S08 | peak | static | 10 | 10 | 0 | 0 | 0 | 0 |
| S08 | peak | dynamic | 10 | 0 | 0 | 0 | 0 | 0 |

## 5. S08 replanning frequency (all trials)

| Profile | Mode | N | 0 changes | 1 change | 2+ changes |
|---|---|---|---|---|---|
| normal | static | 10 | 10 | 0 | 0 |
| normal | dynamic | 10 | 0 | 6 | 4 |
| heavy | static | 10 | 10 | 0 | 0 |
| heavy | dynamic | 10 | 0 | 2 | 8 |
| peak | static | 10 | 10 | 0 | 0 |
| peak | dynamic | 10 | 0 | 2 | 8 |

## 6. S08 applied latency (simulation seconds; denominator = applications)

| Profile | Mode | Applications | Mean | Median | Sample SD | Min | Max |
|---|---|---|---|---|---|---|---|
| normal | static | 0 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| normal | dynamic | 14 | 0.86 | 1.00 | 0.86 | 0.00 | 2.00 |
| heavy | static | 0 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| heavy | dynamic | 18 | 1.11 | 1.00 | 0.68 | 0.00 | 2.00 |
| peak | static | 0 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| peak | dynamic | 18 | 1.06 | 1.00 | 0.64 | 0.00 | 2.00 |

## S07 matched-success comparison

| Profile | Jointly successful pairs | Static mean s | Dynamic mean s | Mean difference s | Reduction in group mean |
|---|---|---|---|---|---|
| normal | 10/10 | 53.00 | 34.00 | 19.00 | 35.85% |
| heavy | 10/10 | 78.60 | 34.00 | 44.60 | 56.74% |
| peak | 10/10 | 85.10 | 34.00 | 51.10 | 60.05% |

Percentages are descriptive reductions in the group mean, not a significance test or a mean of per-seed percentages. S05 jointly successful pairs have zero travel-time difference; its gain is reliability. S08 has zero jointly successful pairs.
