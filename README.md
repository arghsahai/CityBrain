# CityBrain SUMO experiments

Current scope: **software + SUMO digital twin only**. The research PDF is architectural and research context, not the current implementation specification. Hardware-in-loop, real cameras, ESP32, edge devices, GPS, physical signals, real drones and live traffic feeds are future work.

Krishna owns `simulation/` and `experiments/`. The experiment runner uses a TraCI dictionary adapter and main’s unchanged EmergencyPlanner and Replanner. Argh’s core integration remains a separate dependency. It does not replace teammate agents or routing architecture. This integration branch starts from team main; the independently rooted Krishna branch remains a historical reference. See docs/INTEGRATION.md for the port decisions.

## Setup

Install Eclipse SUMO (tested with 1.27.1) and Python dependencies:

```sh
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r experiments/requirements-analysis.txt
```

Run commands from the repository root. `sumolib.checkBinary` selects `sumo`, `sumo-gui` and `netconvert` portably; install SUMO on PATH or configure SUMO_HOME. GUI is optional (`--gui`).

## Reproduce experiments

```sh
python -m experiments.runners.compare --scenarios S05 --seeds 1 2 3 4 5 6 7 8 9 10 --output experiments/results/my-s05
python -m experiments.runners.compare --scenarios S07 --seeds 1 2 3 4 5 6 7 8 9 10 --output experiments/results/my-congestion
python -m experiments.runners.compare --scenarios S01 S02 S03 S04 S05 S06 S07 --profiles normal heavy peak congested --seeds 1 2 3 4 5 6 7 8 9 10 --output experiments/results/my-suite
python -m experiments.analysis.summarize experiments/results/my-s05/results.csv
python -m experiments.analysis.charts experiments/results/my-s05/results.csv
python -m unittest discover -s tests -v
python -m simulation.tools.check_signals
python -m simulation.tools.build_network --output /tmp/citybrain-rebuilt.net.xml
```

Each comparison executes static then dynamic trials with identical SUMO inputs and seed. The static strategy applies one initial plan; dynamic evaluation runs every simulated second, skipping internal intersection edges until a route can be safely applied. Output directories must be fresh, preventing accidental overwrites. Errors stop the suite and preserve completed rows. The full suite is 560 simulations; smoke-check a small subset first. `experiments/configs/suite.json` records the reference suite and policy parameters; the commands above are the execution interface.

Every trial saves generated route/config files, `result.json`, explainable `events.json`, edge measurements every 10 seconds in `edges.csv`, and SUMO `tripinfo.xml`. The suite saves a CSV, Markdown summary and input manifest with SUMO version, Git commit, network hash and policy values. Generate charts separately. Large raw artifacts should remain local; retain compact research CSVs and summaries in Git.

## Network and signals

The bidirectional 3×3 grid has J1–J3 on the bottom row, J4–J6 on the middle row and J7–J9 on the top row; junction spacing is 100 m, with one lane per directed edge at 13.9 m/s.

| Edge pair | Forward connection | Reverse connection |
|---|---|---|
| E1 / E2 | J1 → J2 | J2 → J1 |
| E3 / E4 | J2 → J3 | J3 → J2 |
| E5 / E6 | J4 → J5 | J5 → J4 |
| E7 / E8 | J5 → J6 | J6 → J5 |
| E9 / E10 | J7 → J8 | J8 → J7 |
| E11 / E12 | J8 → J9 | J9 → J8 |
| E13 / E14 | J1 → J4 | J4 → J1 |
| E15 / E16 | J4 → J7 | J7 → J4 |
| E17 / E18 | J2 → J5 | J5 → J2 |
| E19 / E20 | J5 → J8 | J8 → J5 |
| E21 / E22 | J3 → J6 | J6 → J3 |
| E23 / E24 | J6 → J9 | J9 → J6 |

All nine junctions expose traffic-light state, controlled links and phase changes through TraCI. The check tool changes to the next phase, verifies it and restores the original phase before advancing simulation. It does not implement SignalAgent or a green corridor. The committed network and its header use netconvert's automatically generated signals. The incompatible legacy `city.tll.xml` was not ported. Main’s original network/config/routes remain at their original paths. Rebuild from `simulation/network/regression/city.nod.xml` and `simulation/network/regression/city.edg.xml`, preserving the same SUMO version for comparisons.

## Demand and scenarios

Background traffic derives from the existing S05 flows (450, 250, 500 and 200 vehicles/hour). Normal/heavy/peak/congested multiply demand by 1/1.5/2/3. These are controlled synthetic profiles, not calibrated city demand. S03 imposes at least heavy demand. Flow insertion may be delayed by queues; throughput measures actual arrivals, not requested demand.

| Scenario | Conditions |
|---|---|
| S01 | Background traffic only; emergency outcome is NOT_APPLICABLE |
| S02 | E3 accident vehicle and ambulance depart at 300 s |
| S03 | S02 with at least 1.5× background demand |
| S04 | E7 blocker departs at 295 s, before emergency dispatch |
| S05 | E3 accident at 300 s, E7 blocker departs at 307 s |
| S06 | S05 plus E11 blocker departs at 310 s; single emergency with two changes |
| S07 | E3 accident plus moving 3 m/s traffic entering E7→E23 at 1800 veh/h from 305–450 s; E7 is not explicitly blocked |

The runner builds scenario variants from the existing S05 XML, preserving the existing S02 and S05 files. Demand records are chronologically sorted. An edge becomes logically blocked only when its scenario blocker is present and stopped. Nominal departure is not the same as physical stop/detection time. Ambulance0 uses SUMO's emergency vehicle class with no blue-light device or collision/teleport bypass. H1 at J9 is the existing logical hospital destination. Police allocation remains the existing agent's logical response; a physical police dispatch and simultaneous multi-emergency allocation need teammate integration.

## Continuous loop and stability

Detect stopped blockers and traffic → update the planner state snapshot → build live planner state → evaluate reachable candidate route suffixes → call the existing Replanner → apply through TraCI → measure → repeat.

Blocked remaining routes bypass the commitment timer. Congestion changes require at least 10 seconds since the last route assignment, at least 5 seconds predicted ETA improvement and at least 15% improvement. This decision gate belongs to the experiment harness; it does not rewrite the planner. Route prefixes already traversed are removed when evaluating alternatives. No alternative is invented after the last usable turn. Logs include the current route, candidate, blocked edges, predicted benefit, computation time and APPLY/KEEP/APPLY_FAILED decisions.

## Metric definitions and schema

`SUCCESS` requires SUMO's arrived event. `TELEPORTED` takes precedence over arrival and is terminal even if SUMO later reinserts the vehicle. Unexplained disappearance is `FAILED_BLOCKED`; no initial plan is `NO_ROUTE`; remaining unresolved trips at 900 s are `TIMEOUT`. Do not infer success from disappearance.

Travel time is arrival minus dispatch. Response time is arrival minus the nominal 300 s accident event. ETA error is absolute error against the initial dispatch ETA; failed/teleported trials have blank arrival/travel/response/ETA-error fields. Dispatch can occur after nominal departure due to insertion delay. Initial ETA reflects the existing adapter's edge-speed estimate and excludes explicit intersection-delay prediction.

Replanning latency is simulated seconds from physical E7 blockage detection to the first successful updated route application. It is distinct from `planner_computation_ms`, measured with `time.perf_counter()` and summed across initial planning and re-evaluations; individual call times are logged in events. Congestion decisions and multi-change events remain available in events rather than being forced into a single E7 latency metric.

`number_of_replans` and `successful_route_changes` count successful route applications, not evaluations or route-prefix shortening. Edge logs include speed (m/s), travel time (s), occupancy (%), vehicles and queue length (halted vehicles). Background waiting/time loss are means over completed and unfinished car trips in a common 900-second window. Throughput is background arrivals × 3600/900. Average speed is the average of per-step fleet means; it is not distance divided by total trip time.

Legacy controllers and historical CSVs remain on the preserved reference branch. The integrated runner provides both strategies. Read the new paired schema by field name; historical observations are not integration measurements.

## Research limits

Report all seeds and failures. Summaries include success count, teleport count, mean/median/spread of successful travel times and normal-traffic effects. Successful-trip averages alone cannot establish improvement when failure rates differ. Some seeds initially choose a route avoiding E7, so static success is expected and retained. The small synthetic network and four existing candidate routes limit generalization. S06 can exhaust reachable candidates and fail; this is evidence of an integration limit, not a reason to replace teammate routing. No hardware, perception accuracy, real-city validity or joint route-and-signal optimization is claimed.
