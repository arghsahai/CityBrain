# CityBrain V3.0 implementation status

## Implemented in the current feature branch

- Isolated typed traffic evidence with default-off candidate cost comparison,
  strict freshness/match/direction/coverage gates, bounded penalties and conflict
  quarantine. This comparison sidecar never calls the planner or executor.
- Safe HERE/TomTom readiness reporting and an explicit single-request manual
  verification command. No key is printed and no live request was made.
- Browser-only, user-consented location marker with local road matching, accuracy
  display, stale/out-of-order/jump rejection and Stop cleanup. Coordinates remain
  in tab memory and are not uploaded or used for routing.
- SUMO signal phase, link-state and available phase timing display. Signal
  recommendations are visibly `ADVISORY_ONLY · NOT APPLIED`.
- Versioned architecture, setup, demo, privacy, signal, experiment and review docs;
  a fresh matched S05/S06/S08 one-seed smoke summary and chart.

## Verified modes and limits

| Evidence type | State |
|---|---|
| Mocks | Provider status and evaluation logic tested; mocks do not verify external services |
| Synthetic traffic replay | Fresh browser and simulation checks passed; all data remains synthetic/replay |
| SUMO simulation | Baseline and replay-assisted Chennai both reached SUCCESS at 704 simulation seconds |
| S05/S06/S08 research smoke | One matched seed each; retained failures, not a formal performance study |
| Genuine live HERE/TomTom | Not tested; no credentials or provider calls used |
| Traffic-assisted route commitment | Not implemented; evaluator is disabled-by-default offline sidecar |
| SUMO signal priority controller | Not implemented; current request lacks safe movement/clearance/restoration contract |
| GPS into CityBrain runtime | Not implemented; browser location is local visualization only |
| Production emergency dispatch | Not certified or claimed |

## Remaining work

Implement a safe phase-aware SUMO priority controller with verified controlled
movements, yellow/all-red transitions, minimum-green and restoration tests. If GPS
must become runtime input, design consent, authentication, retention, network
failure isolation and a separate matching interface. Integrate traffic evidence
only behind an experimental feature gate after calibration and controlled route
execution testing. Run a multi-seed, matched-arm experiment matrix with confidence
intervals and full failure denominators. Obtain authorized provider credentials
and inspect actual Chennai responses before claiming coverage. Validate real
hospital entrances, clinical availability, signal locations, demand and road rules
before any real-world deployment discussion.
