# Recorded metrics and five presentation figures

Sources: `experiments/runners/compare.py`, `experiments/outcomes.py`, `experiments/runners/s08_audit.py`, the two official aggregate CSVs and their saved events. Units and populations below follow code, not label assumptions.

## Complete aggregate field dictionary

| Field(s) | Definition / measurement | Importance | Invalid or unavailable |
|---|---|---|---|
| scenario, profile, seed, strategy | Trial identity and treatment; profiles normal/heavy/peak, seeds 1–10, static/dynamic | Pair matching and coverage | Missing identity invalidates audit |
| accident_time | Configured 300 s reference | Shared incident-time baseline | Not a sensed crash timestamp |
| blockage_time | Configured 307 s for S05/S06/S08; blank otherwise | Stimulus schedule | Not actual fully stopped detection |
| initial_route, final_route | Applied initial route and most recently applied route/suffix | Show route evolution | Empty when no dispatch/application |
| initial_eta | Planner's dispatch route travel estimate, seconds | Prediction baseline | No plan; not measured arrival time |
| replanned_eta | ETA of most recent applied change, seconds | Estimate after reassessment | No applied replan |
| blockage_detection_time | First observed stopped E7 blocker in historical runner | Separate observation from stimulus | E7 never classified stopped; S07 lacks that blocker |
| replanning_trigger_time | First meaningful eligible candidate time for first applied change | Latency reference | No applied change |
| replanning_completion_time | First successful route application time | End of initial replan delay | No applied change |
| ambulance_dispatch_time | Simulation time of initial plan application | Travel-time origin | No dispatch |
| ambulance_arrival_time | Simulation time of accepted successful arrival classification | Completion timestamp | Teleported, failed, timeout or no route |
| actual_travel_time | Arrival minus dispatch, simulation seconds | Emergency journey duration | All non-success outcomes; never substitute zero |
| response_time | Arrival minus configured 300 s incident time | Incident-to-arrival proxy | All non-success outcomes; not time to patient pickup |
| eta_error | Absolute difference between actual travel and initial ETA, seconds | Exposes prediction error | Non-success or no valid initial estimate |
| number_of_replans, successful_route_changes | Increment together after a successful route-change application; exclude P0 | Intervention frequency | Zero legitimately means none; ERROR interpretation requires log |
| route_changed | Whether at least one change applied | Simple change indicator | Not proof of repeated replanning |
| replanning_latency | First application's time minus first eligible candidate time, simulation seconds | Decision/application delay | No application; not wall-clock computation time |
| planner_computation_ms | Accumulated wall-clock time around initial planning and actual replan calls | Computational overhead | Environment-dependent; not simulation delay |
| replan_checks | Actual post-dispatch Replanner call count | Reassessment frequency | Static correctly zero |
| runtime_seconds | Trial wall-clock elapsed execution time | Execution/reproduction cost | Not emergency travel time; machine/GUI dependent |
| error | Exception text on ERROR | Retains failures for audit | Empty for normal execution |
| completion_status | SUCCESS, TELEPORTED, TIMEOUT, FAILED_BLOCKED, NO_ROUTE, ERROR; S01 NOT_APPLICABLE | Correct denominator/outcome | Official 180 observed only SUCCESS/TELEPORTED |
| teleported | Terminal teleport flag | Distinguishes SUMO recovery from valid journey | Boolean, not count of all network teleports |
| completed | SUCCESS flag | Arrival denominator | False for failures; disappearance alone insufficient |
| normal_traffic_waiting_time | Mean tripinfo waitingTime for car/slowCar, including unfinished trips in the 900 s window | Background stopped-delay impact | ERROR has unavailable traffic metrics; empty population guard returns 0 |
| normal_traffic_time_loss | Mean tripinfo timeLoss over same background population | Delay relative to ideal movement | Same conditions as waiting metric |
| normal_traffic_arrivals | Count of background trips with nonnegative arrival | Completed background volume | Includes neither ambulance nor blockers |
| network_throughput_vehicles_per_hour | Background arrivals × 3600 / horizon (900 s) | Common-window throughput | Not all-vehicle throughput; ERROR unavailable |
| average_vehicle_speed | Mean of per-step mean background speed over steps with cars | Traffic movement descriptor, m/s | Not distance/time network speed or vehicle-weighted trip mean |
| candidate_evaluations | S08 recorded actual candidate scorer evaluations during replanning | Algorithm activity | Separate from initial dispatch and audit-only calls |
| first_environment_change_time, second_environment_change_time | S08 meaningful observed deterioration markers from audit | Establish changing state | Not fixed departure or fully blocked timestamps |
| first_applied_replan_time, second_applied_replan_time | S08 ordinal application times | Verify successive changes | Blank if that ordinal never applied |
| first_applied_replan_latency, second_applied_replan_latency | Ordinal time minus its eligible-candidate trigger | Per-application responsiveness | Blank where no application |

The complete CSV columns above are supported by artifacts. A fleet-wide teleport count, medical survival outcome, fuel/emissions impact, real GPS accuracy and accident-detector precision/recall are not recorded research outcomes here.

Per-trial `edges.csv` also samples time, edge, vehicle_count, mean_speed, occupancy_percent, queue_length_vehicles and travel_time every 10 simulation seconds for E3/E5/E7/E19/E11. The travel_time there comes from TraCI's edge estimate; it is distinct from the planner's length/current-speed cost. Final Core evidence occupancy is a fraction, whereas the historical TraCI edge CSV reports percentage. Do not plot them on an unlabeled shared scale.

S08 event logs additionally retain physical speed/distance, current edge, candidates, actual score calls, current cost, gate/reason, command and full/suffix read-back. Integration JSONL retains structured decisions, accepted revisions, terminal lifecycle, provenance and evidence diagnostics. Final-runtime latency remains simulation-time eligibility-to-acceptance, not CPU duration.

## Figure inventory

| Figure / supplied PNG | Type | X-axis | Y-axis | Series / exact source | Caption and takeaway |
|---|---|---|---|---|---|
| [1. Success](figures/01_success.png) | Grouped bars | Scenario × profile | Success % | Static/dynamic, both official CSVs; numerator/all-trial denominator shown | Dynamic completed all tested trials; static reliability depends strongly on scenario. Ten runs per cell, not proof of universal reliability. |
| [2. Travel time](figures/02_travel.png) | Grouped bars | Scenario × profile | Mean successful travel seconds | SUCCESS rows only from both CSVs, n/10 labels | Conditional travel distributions must be read beside success rates. Static S08 has no mean, not a zero mean. |
| [3. Demand sensitivity](figures/03_profiles.png) | Two lines with markers | Normal/heavy/peak | Mean successful travel seconds | S07 static/dynamic from validation_matrix.csv | S07 observed static means increase while dynamic means remain 34 s; all cells 10/10 successful. This is scenario-specific. |
| [4. Replanning frequency](figures/04_replans.png) | Stacked counts | Profile | Trials out of 10 | S08 V2 dynamic successful_route_changes: 0/1/2 | Twenty of thirty dynamic trials make two changes; ten make one. Replanning is not forced on every seed. |
| [5. Integrated timeline](figures/05_timeline.png) | Event timeline | Simulation seconds | Event labels; no quantitative Y | Final hotfix S08 events.jsonl, PLAN_ACCEPTED/REPLAN_ACCEPTED/TERMINAL | P0 301 → P1 311 → P2 316 → SUCCESS 425, a separate integration smoke, not the 60-trial study. |

Use these five core figures rather than a large chart collection. Existing `validation_matrix_S05.png`, `validation_matrix_S07.png`, `validation_matrix_demand.png` and `s08_validation.png` can be reused as backup detail. Official images are untouched. The new PNGs are derived presentation artifacts generated by `python -m tools.build_krishna_package`; sample SD/median are supplied in RESULT_TABLES.md. Bars are descriptive means, not significance tests. No uncertainty bar is silently claimed.
