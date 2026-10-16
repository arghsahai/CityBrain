# SUMO DIGITAL TWIN AND EXPERIMENTAL EVALUATION

## 1. Simulation Environment

The experimental environment uses Eclipse SUMO 1.27.1 with TraCI to connect microscopic traffic simulation to CityBrain. Experiments use a 900-second horizon and one-second simulation steps. All road networks, vehicle populations and incident schedules are synthetic. The purpose is controlled evaluation of emergency routing under repeatable conditions rather than reproduction of a particular city's transport system.

## 2. Digital-Twin Design

The environment is a simulation-based traffic digital twin: an evolving road/vehicle representation is observed through TraCI, used for decisions, changed through route application and measured again. This supports a continuous observation–state update–recalculation–application–measurement loop. It is not a live synchronized twin of a real city, since no real traffic feed, ambulance GPS or hospital occupancy feed is connected.

## 3. Road Network

The regression network consists of nine signalized junctions J1–J9 and 24 directed single-lane external edges, with 100-metre coordinate spacing and 13.9 m/s edge speed limits. The S08 research network extends this topology to 12 junctions and 34 external edges. The additional row provides an engineered alternative after successive disruptions. Compiled lane lengths and individual connections are documented in NETWORK.md; these physical lane lengths differ from node spacing because of junction geometry.

## 4. Traffic Generation

Four background flows are defined over the common 0–900-second interval. Their base demands are 450, 250, 500 and 200 vehicles per hour. Vehicle interactions, car-following randomness, signals and insertion conditions determine the realized traffic state. Specified demand must therefore be distinguished from measured arrivals and throughput.

## 5. Traffic Profiles

Normal, heavy and peak multiply the four baseline flows by 1, 1.5 and 2 respectively, giving total scheduled rates of 1,400, 2,100 and 2,800 vehicles per hour. These profiles vary demand while retaining the experimental topology and incident definition. S07 additionally introduces a fixed slow-car queue flow; its rate is not scaled with these background multipliers. The configurable fourth congested profile is not part of the official evaluation reported here.

## 6. Emergency Vehicle

The ambulance is scheduled to depart at 300 seconds and is typically dispatched at observed simulation time 301 seconds. Its configured maximum speed is 20 m/s, but realized speed remains constrained by the network, traffic and junction rules. H1 is represented by destination junction J9 and static availability metadata. The evaluated journey models transport from the configured vehicle origin to the hospital rather than a complete patient-pickup workflow.

## 7. Accident and Blockage Modelling

Accidents are represented by stopped synthetic accidentVehicle objects, not detected real crashes. The base accident is scheduled on E3 at 300 seconds; the S05 dynamic E7 vehicle departs at 307 seconds and moves to a stop lasting 600 seconds. Departure time, changing speed and fully stopped classification are distinct observations. The final runtime's speed-based blockage classification and the historical runner's stopped-vehicle check should not be treated as identical detectors.

## 8. Scenario Design

S01–S04 implement background, initial incident, higher-demand incident and pre-dispatch obstruction cases. S05 examines changing route conditions, S06 tests destination unreachability, S07 introduces congestion without the dynamic E7 blocker and S08 introduces successive disruptions on an extended network. The official research matrices cover S05, S07 and S08; S06 is evaluated as a failure boundary through separate evidence. Implemented scenarios outside the matrices do not automatically carry equivalent statistical validation.

## 9. Static Baseline

The static strategy selects and applies its initial plan using the same initial environment as its dynamic pair, then performs no CityBrain post-dispatch replanning. Static does not mean an arbitrarily poor route or absent initial planning. Frozen-route outcomes remain classified, including teleports and failures, so a comparison does not reward failure by treating disappearance as quick completion.

## 10. Dynamic CityBrain Configuration

The historical experiment runner reevaluates current-position candidates and applies changes when the ETA benefit meets the larger of five seconds and 15% of current ETA, subject to a ten-second commitment unless the active route is blocked. S08's historical candidate catalogue explicitly contains an additional bypass. The final integrated runtime is a separate configuration: it uses the structured ReplanningPolicy with five score units of minimum improvement, ten-second commitment, five-second cooldown and invalid-route override, and can discover topology alternatives. Historical outcomes are not relabeled as results of this later runtime.

## 11. Experimental Methodology

The validated inventory comprises 120 S05/S07 trials and 60 official S08 V2 trials. Each scenario is evaluated across normal, heavy and peak demand, ten seeds and static/dynamic strategies. This produces 180 distinct identities and 90 matched pairs. The studies are reported separately because their network/candidate configurations and research questions differ; the inventory total is not a pooled effect estimate.

## 12. Reproducibility

Each pair shares scenario, profile, seed and generated route input. This package checks byte-identical paired demand files and agreement between aggregate CSV rows and trial checkpoints. S08 additionally validates generating revision, execution fingerprint, environment, input hashes, result hashes and event hashes. Seeds 1–10 vary stochastic realization while preserving controlled pairing. Superseded S08 V1 and V2 are not counted as independent replications; V2 addresses evidence serialization/resume correctness while preserving the compared outcome fields.

## 13. Evaluation Metrics

Success and failure rates use all trials as denominators. Emergency travel time is arrival minus dispatch and is available only after valid success; response time is arrival minus the configured 300-second incident reference. Absolute initial ETA error, route changes, actual replan calls, candidate evaluations, simulation-time application latency and wall-clock computation are reported where recorded. Background waiting, time loss and throughput are measured in the common observation window. Metric definitions and missing-value rules are provided in METRICS_AND_FIGURES.md.

## 14. S05 Results

The official S05 matrix records dynamic success in 30 of 30 runs, compared with static success in 12 of 30. Static success counts are seven, three and two out of ten under normal, heavy and peak demand. Successful travel times are 34 seconds in both strategies, including jointly successful pairs. Consequently, the principal observed benefit is reliability rather than a successful-trip time reduction. Final integration evidence separately shows P0 at 301 seconds, P1 at 311 and success at 335; at the replan, E7 was highly congested but not flagged fully blocked.

## 15. S06 Failure Case

In the integrated S06 demonstration, current observed blockages prevent a path from E5 to H1, and the emergency terminates as NO_ROUTE at 316 seconds. Independent graph reachability confirms the cut under those conditions. No arrival or successful travel-time value is manufactured. This illustrates correct handling of a constrained problem boundary rather than evidence that dynamic routing can always rescue an emergency.

## 16. S07 Results

All S07 runs succeed. Normal static/dynamic successful means are 53.0/34.0 seconds; heavy means are 78.6/34.0; peak means are 85.1/34.0. Descriptive reductions in the group means are approximately 35.85%, 56.74% and 60.05%. These comparisons use ten jointly successful matched pairs per profile. Static distributions vary substantially; for example, the normal median is 34 seconds despite a mean of 53 seconds, indicating that not every seed benefits equally.

## 17. S08 Multi-Replanning Results

Official S08 V2 records 30 dynamic successes and 30 static teleports. Of the dynamic runs, ten apply one change and twenty apply two; none apply zero or more than two. Dynamic travel spans 123–124 seconds with mean and median 123.5 seconds for each profile. Fifty route applications pass the saved-evidence audit, with mean application latency 1.02 simulated seconds. There are no jointly successful static/dynamic pairs, so a paired travel-time superiority estimate is unavailable. Separately, the integrated catalogue/fallback demonstration verifies P0/P1/P2 at 301/311/316 seconds and hospital arrival at 425 seconds, for a 124-second journey.

## 18. Overall Discussion

The results support state-aware reassessment under the tested synthetic conditions. S05 primarily demonstrates reliability improvement, S07 demonstrates conditional travel-time improvement and S08 demonstrates repeated replanning with physical route application. S06 establishes that safe refusal is part of correct operation. These are complementary observations, not evidence that one metric or one successful demonstration captures the full system's effectiveness.

## 19. Threats to Validity

The networks and incidents are engineered and limited in number. Ten seeds per profile leave substantial binomial uncertainty; even ten successes in ten trials have an approximate 95% Wilson lower bound of 72.2%. Conditional successful-trip comparisons can be biased if failures are omitted without disclosure. Runtime evolution, ETA estimation error, candidate limitations and differences between historical and integrated policies constrain comparison across studies. Wall-clock performance depends on the execution machine, and the prototype does not simulate clinical outcomes.

## 20. Limitations

The work focuses on one emergency, static hospital availability and synthetic SUMO traffic. It lacks live city sensing, real ambulance GPS, a hospital feed, physical signal priority and hardware validation. Larger networks, scenario sensitivity, more seeds, concurrent emergencies and eventual real-data calibration are future research directions. The present claim is a reproducible software prototype demonstrating continuous emergency-route reassessment and physically verified successive replanning in a controlled simulation-based digital twin.

**Evidence:** RESULT_TABLES.md, NETWORK.md and AUDIT.json are derived from the actual frozen repository. Raw sources are the two official CSVs, paired checkpoints/inputs and S08 V2 event/provenance files. Integration smoke timing is sourced separately from the recorded final hotfix evidence. No official trials were regenerated for this section.
