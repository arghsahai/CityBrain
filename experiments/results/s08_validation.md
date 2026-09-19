# S08 continuous-replanning validation

Generating commit: `d380cb9216bff8d27bf72b3728220036cdb60a32`.

**Evidence classification: REPEATED MULTI-REPLAN EVIDENCE.**

This classification follows the predeclared rule. One fixed synthetic network and incident schedule cannot establish robustness to timing/topology changes or real emergency traffic.

| Profile | Strategy | n | Success | Teleport | Other failure | Mean successful travel s | Median s | SD s | 0 replans | 1 replan | 2+ replans |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| heavy | dynamic | 10 | 10 | 0 | 0 | 123.50 | 123.50 | 0.53 | 0 | 2 | 8 |
| heavy | static | 10 | 0 | 10 | 0 | NA | NA | NA | 10 | 0 | 0 |
| normal | dynamic | 10 | 10 | 0 | 0 | 123.50 | 123.50 | 0.53 | 0 | 6 | 4 |
| normal | static | 10 | 0 | 10 | 0 | NA | NA | NA | 10 | 0 | 0 |
| peak | dynamic | 10 | 10 | 0 | 0 | 123.50 | 123.50 | 0.53 | 0 | 2 | 8 |
| peak | static | 10 | 0 | 10 | 0 | NA | NA | NA | 10 | 0 | 0 |

Dynamic distribution (denominator: all 10 dynamic trials per profile):

- heavy: 0 = 0 (0%); 1 = 2 (20%); 2+ = 8 (80%); unknown = 0.
- normal: 0 = 0 (0%); 1 = 6 (60%); 2+ = 4 (40%); unknown = 0.
- peak: 0 = 0 (0%); 1 = 2 (20%); 2+ = 8 (80%); unknown = 0.

50 physically applied replans passed evidence checks; 20 dynamic trials had at least two applied replans.

Successful-trip means condition on survival and must be read beside failure rates. See [detailed metrics](s08_validation_metrics.md) for matched-success paired differences and full outcome counts. Static trials make zero Replanner calls and apply zero post-dispatch CityBrain route changes.

The observed-change timestamps label E7/E11 deterioration relative to dispatch; they are not incident insertion times, and are separate from the first gate-eligible candidate and its application. A positive physical distance establishes post-dispatch motion; the instantaneous speed may be zero at a signal.

The prior S05/S07 120-trial baseline is unchanged. S06 remains the unreachable-destination case. The optional 560-trial suite was not executed. Hardware remains future work.
