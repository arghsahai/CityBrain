# CityBrain final viva cheat sheet

## One-sentence description

CityBrain is a research software prototype that links an OSM-derived Chennai road network to SUMO simulation, a preserved emergency-planning and verified route-execution path, and a Cesium/SVG dashboard.

## Likely questions and concise answers

**What is the project objective and contribution?**
To demonstrate and evaluate an integrated simulation workflow for emergency route observation, planning, execution and verification. The contribution is bounded engineering integration and evidence; novelty over prior routing research is not claimed.

**Why SUMO and Cesium?**
SUMO supplies microscopic, controllable vehicle and signal simulation through TraCI. Cesium provides a geospatial browser view for roads, vehicles, routes and overlays; SVG/2D is the fallback.

**What is real and what is simulated?**
The study-area road geometry is OSM-derived. Vehicles, demand, congestion, incidents, signals, hospital availability and response outcomes are simulated. Provider observations were not live-verified.

**How does OSM become the SUMO network?**
The project uses the retained Chennai network assets built from OSM-derived roads and their geographic projection. SUMO consumes the network and demand configuration; Cesium uses the corresponding geographic road geometry. OSM geometry does not provide current traffic conditions.

**What does TraCI do?**
It is the runtime interface used to observe and control the running SUMO process, including vehicle/signal state and applying a route through the executor.

**What are the agents?**
Traffic, Ambulance, Hospital, Police and Signal agents assess parts of the simulation state and contribute planning context. The existing planner and validation remain the decision path.

**How is a route accepted?**
The planner proposes a route, validation checks it, `RouteExecutor` applies it, and the runtime reads the route back from SUMO. Logical acceptance follows successful physical read-back.

**What do KEEP / REPLAN / NO_ROUTE mean?**
KEEP retains the accepted route; REPLAN proposes a replacement for validation and verified execution; NO_ROUTE means no valid candidate was found and the failure path must be handled.

**What does the 20-second stability guard do?**
It confirms a soft route-cost change over time before changing the route. Genuine hard invalidation keeps existing immediate handling; it is not delayed by the soft-change guard.

**Why are teleports failures?**
A teleport means SUMO removed/reinserted a vehicle after an exceptional condition. It is not verified ambulance arrival, so it stays a failure in the completion denominator.

**What is the static versus dynamic comparison?**
The preregistered harness compares its existing static and dynamic policy arms on the same normal-demand seeds in scenarios S05, S06 and S08. The traffic advisor is not an arm.

**What is the experiment design?**
Three scenarios × ten matched seeds × two arms = 60 synthetic SUMO trials. Outcomes are reported for all runs. Successful-time comparisons are conditional on success; paired comparisons require both runs for a seed to succeed.

**What were the results?**
S05: 7/10 static versus 10/10 dynamic; S06: 0/10 both; S08: 0/10 static versus 10/10 dynamic. Mean successful response times: S05 35.0 seconds static (n=7) and dynamic (n=10); S08 dynamic 124.5 seconds (n=10). Seven S05 matched successes had zero-second mean and median time difference. There were no successful paired time comparisons for S06/S08.

**Do results prove dynamic planning is better?**
No. Outcomes vary by scenario, n=10 intervals are broad, and there are no matched successful pairs for S06/S08. The results are exploratory and synthetic; they do not show general superiority or real-world performance.

**Are HERE and TomTom operational?**
Adapters exist, but no genuine response was obtained for this package. Chennai coverage, accuracy, freshness latency, account cost and road-class coverage remain unverified.

**What is replay traffic?**
Offline synthetic sample data used to exercise normalization, matching and dashboard paths. It is explicitly labeled `REPLAY` / `SYNTHETIC_SAMPLE`; it is not live measurement.

**Can external traffic alter scores or trigger replanning?**
No. The provider sidecar is isolated from canonical planner costs and ambulance replanning. The opt-in evaluator is display-only and cannot commit a route.

**How is GPS handled?**
The optional marker requires browser permission and remains tab-local. It is not uploaded and is not used by runtime routing.

**Does the system control traffic signals?**
No. It displays SUMO phase/link telemetry and advisory suggestions. Physical actuation is disabled; signal movement/clearance compatibility and restoration safety are not established.

**What does hospital arrival mean?**
The simulated ambulance reached its configured hospital access road. It does not prove driveway access, clinical capacity, admission or service availability.

**What validation exists?**
The recorded V3.1 validation reports 447 passing pytest tests, ten passing compatibility scripts, fresh simulation/replay smokes, browser replay checks, and 2,172/2,172 historical manifest entries verified. The V3.2 submission package adds document, PDF and presentation rendering checks without changing runtime behavior or regenerating the study.

**Why is it not production-ready?**
It lacks live-provider coverage validation, real-world calibration, physical signal control contracts, verified hospital services, field testing, multi-emergency coordination, a safety case, and operational security/privacy review.

**What would real deployment require?**
Calibrated local data; validated provider contracts and costs; municipal and hospital integration; signal movement, clearance and restoration safety; human-factors and cybersecurity review; controlled field evaluation; clinical/dispatch governance; and independent safety approval.

## Evidence boundaries to remember

- **Formal study:** 60 static/dynamic synthetic SUMO trials; no advisor arm.
- **Fresh smoke:** seed-17 simulation and replay-assisted runs reached SUCCESS at 704 simulation seconds; not research trials.
- **Dashboard replay:** saved synthetic offline evidence; not live traffic.
- **External providers:** adapters implemented; actual provider coverage/accuracy unverified.
- **Arrival:** simulated access-road condition only.
- **Signals:** simulated telemetry, advisory recommendations, no physical actuation.
