# Previous verified replanning timeline

A: recorded corridor through `30424374#0`; B: recorded corridor through `-1309011039#19`.
These labels are for this evidence table only. All executions/read-backs were VERIFIED.

| Time | Current route | Candidate | Trigger / reason | Current score | Alternative score | Policy | Execution |
|---:|---|---|---|---:|---:|---|---|
| 51 | Seed route | A | Initial valid candidate | UNAVAILABLE | 448.561 | PLAN_CREATED | VERIFIED |
| 61 | A | B | material_improvement_and_timing_satisfied | 557.325 | 548.400 | REPLAN | VERIFIED |
| 71 | B | A | material_improvement_and_timing_satisfied | 517.729 | 418.864 | REPLAN | VERIFIED |
| 91 | A | B | invalid_active_route_override:unreachable_edge | Infinity | 515.750 | REPLAN | VERIFIED |
| 97 | B | A | invalid_active_route_override:unreachable_edge | Infinity | 461.019 | REPLAN | VERIFIED |
| 125 | A | B | material_improvement_and_timing_satisfied | 682.231 | 560.173 | REPLAN | VERIFIED |
| 145 | B | A | material_improvement_and_timing_satisfied | 484.938 | 465.834 | REPLAN | VERIFIED |
| 167 | A | B | material_improvement_and_timing_satisfied | 688.958 | 460.549 | REPLAN | VERIFIED |
| 588 | existing hospital access | alternate hospital access | material_improvement_and_timing_satisfied | 167.868 | 146.176 | REPLAN | VERIFIED |

The complete route IDs, event trigger types, scores and execution-order checks are retained in `before-replans.json`.
At 91 and 97 s, the invalidating observation was one stopped vehicle with no explicit blockage flag; the second override followed acceptance by only six seconds.
Finite-score improvements were real inputs to the configured policy; unnecessary travel-time loss has not been proved.
