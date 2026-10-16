# Krishna Verma — simulation and research package

## Repository verification and attribution

Authoritative frozen implementation: `fe471a863858489229c6bb956498405c77a2558e`, the merge of PR #8. The working tree was clean before work. This package/dashboard branch is `feature/krishna-live-dashboard`, created directly from that origin/main. The unrelated local main was not reconciled. The work is additive and does not alter the validated implementation or official evidence.

The [per-file contribution map](CONTRIBUTION_MAP.md) is derived from unified Git history. Important Krishna-authored contributions are `1250aed` (regression network/scenario port), `874e0b1` (reproducible experiments connected to team planner), `193cff6` (paired validation and extended network), `df36103` (demo/charts), `480427f` (audited matrix), `b7842f4` (S08 protocol), `d380cb9` (evidence/resume correctness) and `614c790` (official V2 publication). Krishna also authored final integration `c811ae4` and exception safety `b880158`; do not attribute all later runtime changes solely to Argh.

Argh authored the initial SUMO simulation (`8a17c0c`) and canonical Core/executor foundation (`3f8c05d`, with compatibility fix `ceea6a9`). Subhashini authored agents/planning (`d803f7b`), input adapter (`ed6ba19`) and structured planner/policy completion (`caeea8b`). Directory ownership alone does not establish authorship. Describe your primary research ownership while crediting these foundations.

## SUMO digital twin

SUMO provides microscopic vehicle movement, car-following, junction signals and traffic interaction in a controlled synthetic road network. TraCI exposes current vehicle/edge state; CityBrain evaluates this evolving representation, applies routes, then observes the physical simulation response. This gives a simulation-based traffic digital twin for closed-loop experimentation.

**Viva answer:** “We use digital twin in the bounded sense of a stateful simulation-based representation connected to a controller through TraCI. It supports observe–decide–apply–measure feedback. It is not a live synchronized twin of Chennai or any deployed city, because we have no live traffic/GPS/hospital feeds or city calibration.” Simply drawing a map would not establish a live twin; the feedback coupling supports the experimental terminology, not a real-city claim.

## Network and vehicles

The [network inventory](NETWORK.md) contains every compiled external edge, junction coordinate, lane length, speed and traffic-light location. The regression network has nine junctions J1–J9, 24 directed single-lane edges E1–E24, 100 m node spacing and nine signal programs. All external edge speed limits are 13.9 m/s. Compiled lane lengths are shorter than node spacing where junction geometry consumes road length; use the table rather than assuming every lane is 100 m.

S08 uses a separate 12-junction, 34-edge network. J10–J12 form an additional row at y=300 m; E25–E34 provide additional connections. It creates an engineered alternative after disruptions on E7 and E11. The initial team network in `simulation/network/` remains distinct from the active regression/research compiled files; do not use its retained route/configuration as evidence of the research network.

`dynamic_blockage.rou.xml` defines car (accel 2.6, decel 4.5, sigma 0.5, length 5 m, minGap 2.5 m, maxSpeed 13.9 m/s), ambulance (3.0, 5.0, 0.2, 6 m, 2.5 m, 20 m/s) and accidentVehicle (2.6, 4.5, 0.5, 5 m, 2.5 m, 13.9 m/s). The runner assigns ambulance vClass emergency, but adds no blue-light bypass or physical signal priority. The ambulance's configured maximum is not its realized speed.

Ambulance0 is scheduled to depart at 300 s on E13→E5→E7→E23. The observed dispatch is 301 s. H1 is configured at destination J9, with static ICU availability; it is not a SUMO hospital facility or capacity feed. The historical experiment's Emergency object names J3 as incident location, while its transport starts at J1. This is not a complete patient-pickup simulation.

## Traffic generation and profiles

Source: `experiments/runners/compare.py:prepare_config` and `simulation/scenarios/S05_dynamic_blockage/dynamic_blockage.rou.xml`. Four background flows run from 0 to 900 s. These are scheduled rates, not guarantees of inserted or completed vehicles; interactions and insertion delays matter.

| Profile | E17→E19 | E21→E23 | E14→E1 | E20→E6 | Total scheduled veh/h | Purpose / expected characteristic |
|---|---:|---:|---:|---:|---:|---|
| NORMAL | 450 | 250 | 500 | 200 | 1,400 | Reference demand; local queues can still occur |
| HEAVY | 675 | 375 | 750 | 300 | 2,100 | 1.5× baseline; greater interaction/queue opportunity |
| PEAK | 900 | 500 | 1,000 | 400 | 2,800 | 2× baseline; stronger congestion pressure |

A fourth `congested` multiplier of 3 exists in the configurable suite but is not in the official 180 trials. S03 enforces at least 1.5× demand. S07 adds a separate, unscaled 1,800 veh/h slow-car flow on E7→E23 from 305–450 s, with maxSpeed 3 m/s and sigma 0.5. Demand multipliers do not directly prescribe realized congestion or outcomes.

## Complete scenario catalogue

The generator branches in `prepare_config` implement S01–S08. Definitions are experimental stimuli, not runtime policy hacks. The official study covers S05/S07 and S08 V2; individual legacy smokes are not a full validation matrix.

| Scenario | Purpose / initial conditions | Changes | Static expectation | Dynamic expectation | Evidence status / question |
|---|---|---|---|---|---|
| S01 | Background traffic only | Generator removes all vehicle elements, including ambulance/blockers | No emergency route | No emergency route | NOT_APPLICABLE in runner; background sanity case |
| S02 | Incident baseline, ambulance at 300 | E3 accident vehicle, no dynamic E7 blocker | Retain dispatch route | Reassess live conditions | Implemented; separate S02 XML retained. Is initial dispatch possible? |
| S03 | Higher-demand incident | S02-like vehicles; at least heavy multiplier | Fixed dispatch route | May find lower-cost route | Implemented smoke family, not official matrix. Sensitivity to demand |
| S04 | Pre-existing E7 obstruction stimulus | Dynamic blocker departs at 295 before ambulance | Initial selection may already avoid deterioration | Reassess thereafter | Implemented, no new outcome asserted. Pre-dispatch versus post-dispatch state |
| S05 | Dynamic route deterioration | E3 blocker departs 300; E7 blocker departs 307, drives to stop at 30 m for 600 s | Some seeds teleport on retained route | Reassess and reroute when justified | Official 60 trials plus integrated SUCCESS smoke. Reliability under deterioration |
| S06 | Unreachable destination boundary | S05 plus E11 blocker scheduled 310 on regression network | No reliable arrival expected under cut | Report no usable path | Final integrated NO_ROUTE at 316, not part of official 180. Safe failure |
| S07 | Congestion without dynamic E7 blocker | E3 accident retained; slow queue flow 305–450 on E7→E23 | Longer travel in affected seeds | Bypass may improve arrival time | Official 60 trials. Congestion benefit independent of total blockage |
| S08 | Repeated changes with a bypass | S05 plus E11 blocker scheduled 315; extended network | Frozen route can teleport | One or repeated changes depending on seed/state | Official V2 60 trials; distinct integrated P0/P1/P2 smoke. Continued reassessment |

Historical seed-1 normal exploratory results in `integration-smoke.csv` are also preserved: S01 NOT_APPLICABLE for both strategies; S02/S03/S04 SUCCESS for both; S05 static TELEPORTED/dynamic SUCCESS; S06 both TELEPORTED; S07 both SUCCESS. The older S06 teleport record is not rewritten as the later integrated NO_ROUTE outcome. These are different implementations/checkpoints, outside the official matrix. The older integration-profiles smoke additionally samples congested demand and does not expand the official dataset.

A departure timestamp is not the moment an edge is classified stopped/blocked. Initial speed zero, subsequent movement to the stop and speed-based versus isStopped detection can produce different observation times. Core uses accidentVehicle speed ≤0.1 m/s on external edges; historical experiment detection uses isStopped. Explain the distinction.

## S05 reconstruction: final integrated evidence

Source: `data/output/integration/exception-safety-hotfix-smokes/S05/runtime/events.jsonl`, generating commit `b88015815a20cb1f394638ecb55d8e611cc79682` (unchanged execution code on frozen main).

| Time s | Evidence | Interpretation |
|---:|---|---|
| 300 | Scheduled ambulance/accident departures in XML | Stimulus, not yet accepted P0 |
| 301 | P0 physically verified/accepted: E13→E5→E7→E23 | Dispatch on observed state |
| 307 | Scheduled E7 blocker departure | Do not equate with fully stopped classification |
| 311 | REPLAN: E5→E19→E11, then physical verification and P1 acceptance | Material score benefit after commitment |
| 335 | Physical hospital arrival / SUCCESS | 34 s from dispatch; active state finalized |

At 311, E7 average speed is approximately 2.973 m/s, congestion HIGH, travel estimate 28.789 s, and blocked is not flagged. Current route score is 59.770; alternative score 22.140; minimum improvement is 5 score units. Commitment/cooldown are satisfied. This is congestion-driven improvement before a fully blocked E7 classification, not proof that a fully stopped edge triggered the reroute.

In the historical 60 S05 trials, dynamic success is 30/30, static 12/30. Among jointly successful pairs the travel difference is zero. The defensible gain here is observed reliability, not faster travel among survivors.

## S06 failure boundary

Final integrated NO_ROUTE is observed at 316 s with no arrival or travel-time success metric. Observed blocked edges include E3, E7 and E11; independent network-XML reachability from current E5 cannot reach either hospital incoming edge E11/E23. The regression topology lacks the S08 northern bypass. NO_ROUTE means no path under the current blockage assumptions, not permanent impossibility after incident clearance.

The runtime must not invent a route from a favourable score or treat disappearance as arrival. Teleport can remove and later reinsert a vehicle to resolve simulation deadlock; it invalidates emergency trip continuity. The terminal latch prevents a later arrival from converting that failed emergency to SUCCESS. The simulation environment is synthetic; accident recognition itself is not validated image recognition.

## S07 results and interpretation

All static and dynamic S07 cells have 10/10 successful runs. Source: actual CSV rows, matched by profile and seed.

| Profile | Static mean s | Dynamic mean s | Difference s | Reduction in group mean |
|---|---:|---:|---:|---:|
| Normal | 53.0 | 34.0 | 19.0 | 35.85% |
| Heavy | 78.6 | 34.0 | 44.6 | 56.74% |
| Peak | 85.1 | 34.0 | 51.1 | 60.05% |

These percentages describe group means, not a significance test. Normal static median is 34 s despite mean 53 s; some seeds see no benefit, while others have long delays. Consult the full mean/median/sample-SD table. No general traffic-network superiority follows.

## S08: research study versus final integration

**HISTORICAL CONTROLLED S08 EXPERIMENT — Research V2:** 60 trials = 3 profiles × 10 seeds × 2 modes. Static 0/30 SUCCESS and 30/30 TELEPORTED; dynamic 30/30 SUCCESS and no teleports. Dynamic 0/1/2+ changes are 0/10/20 overall. By normal/heavy/peak, one-change counts are 6/2/2 and two-change counts 4/8/8. Each dynamic profile has mean 123.5 s, median 123.5 s and sample SD about 0.527 s, with range 123–124 s. Static successful timing and paired travel improvements are unavailable.

The read-only disk audit validates all 50 applied changes. Mean eligible-candidate-to-application latency is 1.02 simulated seconds across applications, range 0–2 s. Profile means are 0.857, 1.111 and 1.056 s over 14, 18 and 18 applications. The saved evidence has 3,428 actual replan calls and 6,746 candidate evaluations. Forty-six applications pass benefit/commitment; four use blocked-route override. First environmental deterioration is observed at 308 s, second at 316; first application 311–316, second 320–321. These are historical protocol observations, not final integration timestamps.

**FINAL INTEGRATED S08 DEMONSTRATION — Final integration smoke:** catalogue plus generic fallback accepts P0 at 301 (E13→E5→E7→E23), P1 at 311 (E5→E19→E11), P2 at 316 (E5→E19→E27→E33→E30), then SUCCESS at 425, travel 124 s. P2 is topology-discovered in the final runtime. The study instead supplied explicit R_EM_5 in the experiment runner. Both demonstrate successive changes, through different candidate/gating contracts. Default all-topology integration may need only one replan; do not force P2 for presentation.

## Dataset audit, fairness and reproducibility

[Audit JSON](AUDIT.json) and [tables](RESULT_TABLES.md) verify 180 unique identities, exact expected coverage and 90 matched input pairs. Every CSV outcome/route/change/travel field checked matches its per-run checkpoint; static/dynamic generated route XML is byte-identical within each pair. S08 additionally passes provenance/result/event/config/network checks through its existing read-only audit. This is an inventory of two studies, not a single pooled effect estimate.

PR #3 has 120 S05/S07 runs. PR #4's official S08 V2 adds 60. Superseded S08 V1, demonstration smokes and other exploratory results are not additional independent replications. V1/V2 preserve identical six compared outcome fields, but V2 fixes infinity serialization/resume auditing. The optional 560-run suite is unexecuted.

Seeds are 1–10 for every scenario/profile/mode cell. A seed initializes SUMO stochastic behavior, including car-following randomness; demand is not described as a newly sampled Bernoulli probability when the input actually specifies vehsPerHour. Equal input, seed, horizon and initial configuration control the comparison; routes may subsequently change traffic interactions as a consequence of treatment.

**Viva:** “I paired runs by scenario, profile and seed, and checked the generated inputs and checkpoints. Static and dynamic received the same initial environment; the intended difference was reassessment after dispatch. I retain failures in denominators and compare travel time only where arrival is valid. Identical inputs do not mean every later vehicle trajectory remains identical after interventions.”

Ten seeds expose variability but do not establish citywide reliability or statistical independence between all scenario groups. Per-cell 10/10 successes have a 95% Wilson interval approximately 72.2–100%; 0/10 has 0–27.8%. Hardware, version and provenance hashes help reproducibility; deterministic timing does not imply real-world accuracy. Use generating revisions for exact historical reproduction, not the frozen integrated runner. Do not rerun completed official trials for this package.

## Observation, interpretation and bounded claim

**Observation:** dynamic routing completed all tested official emergency runs; static had S05 failures and S08 teleports. S07 successful group means favour dynamic. Twenty S08 dynamic trials applied two changes. Final integrated evidence physically verifies sequential acceptance and arrival, while S06 rejects the unreachable case.

**Interpretation:** reassessment can avoid deteriorating alternatives in these designed networks. Reliability and conditional travel-time effects must be separated. The S08 extension deliberately makes a later bypass possible; it is not an unbiased sample of urban networks. ETA errors and small background-traffic differences must also be reported.

**Claim:** CityBrain demonstrates state-aware emergency routing and continuous reassessment in a reproducible, synthetic SUMO digital-twin environment, including successive physically verified replanning under changing conditions. It does not demonstrate real-world emergency effectiveness, production readiness, physical green corridors, hardware performance or real accident detection.

## Limitations and future work

Current limitations: simplified synthetic topology, fixed incident families, single-emergency focus, static hospital selection/availability, bounded candidates, no real traffic/GPS/bed feeds, no physical signals, ten seeds per cell, state-estimated ETA rather than calibrated prediction, and a simulation-to-reality gap. Runtime lane permissions are cached and evidence has memory/storage limits. Initial Emergency location does not model a full pickup journey.

Future work, not implemented: larger OSM-derived networks, topology/timing sensitivity studies, more seeds, multi-emergency resource contention, calibrated traffic/ETA models, real sensing/GPS/hospital feeds, explicit signal-priority contracts and eventual hardware-in-the-loop validation.
