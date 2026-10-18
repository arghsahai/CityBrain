# CityBrain V4 architecture and gap audit

Baseline: V3 commit 8d87f398adadd16b535d8a94317e841761fe0da2; PR #10 was already merged as aa3a57fc1edd35f1a7cf257a8a9eeec3ad1dbf06 (identical tree). V4 branches from that merged main. Baseline verification on 19 October 2026: **447 pytest tests passed in 33.95 seconds**.

## Existing implementation inspected

Core/CityState, the five agents, EmergencyPlanner, RouteScorer, PlanValidator, ReplanningPolicy, RouteExecutor, TraCI interface, Chennai network/runtime/server, provider normalization/matcher/cache, dashboard and tests were inspected. Simulation dispatch selects supplied resources and candidate edge sequences. It does not support arbitrary city coordinates, authorized hospital updates, public incident verification, or real fleet execution. Its travel times are SUMO observations. Provider observations remain advisory in V3.

The retained OSM-derived directed graph and lane connections can support a **bounded routing pilot** without running SUMO. Reading its SUMO-format network with sumolib is data parsing, not TraCI execution. Display coverage must not imply routing coverage. Pilot bounds (west, south, east, north): **80.132, 12.823, 80.174, 12.863**. These imported roads are not field-validated for ambulance access.

## Extension boundary

V3 simulation → existing Core/agents/planner → verified RouteExecutor → SUMO. This path stays unchanged.

V4 live-data prototype → validated public test incidents → authenticated verification → user-selected test ambulance position → directed graph matching → recommendation → explicit operator review/approval. No RouteExecutor, TraCI calls, dispatch, police communication, or real signal control exists in this path. ETA is an estimate, never evidence of arrival.

Reuse the existing agent interfaces, RouteScorer and PlanValidator where their input contracts fit. A separate geographic search is necessary because the existing planner selects supplied candidate edge sequences and assumes explicit simulated resource records. Hospital unknown capacity must never be coerced into available to satisfy that contract.

## Planned additive modules

- `citybrain/live`: geographic search, live-state/service, bounded persistent incident/status/audit store, loopback-only HTTP server.
- `dashboard/live`: V4 controls, existing locally vendored Cesium, SVG fallback, explicit mode/source/coverage labels.
- Offline traffic path: reuse existing normalization/matching/freshness contracts. Authorized network access remains disabled. Estimated graph speeds are distinct from observations.
- Hospital directory: retained OSM locations with attribution; discard simulation capacity fields. Authorized recent reports are STAFF_REPORTED, never clinical guarantees.
- Authentication: independent operator and facility-scoped credentials, no public role choice; no credentials in URLs/logs/source. This is a local prototype, not an Internet deployment.

## Gaps and safety gates

No genuine provider responses, fleet participation, hospital partnership, real signal authorization, or field ETA validation is available. Citywide routing import is deferred; citywide map viewing may use attributed OSM tiles. Existing traffic-light phases lack a reviewed movement/minimum-green/clearance/restoration contract; priority remains ADVISORY_ONLY unless that gate is established. Google Routes licensing must be evaluated before any integration, especially non-Google-map rendering.

Implementation status and actual test evidence will be maintained in V4_FEATURE_STATUS.md. Planned modules above are not completion claims.

## Implemented design

`citybrain/live/graph.py` indexes retained road segments in 50 m spatial cells. Matching requires a pin within 25 m of a passenger-access road inside the pilot; competing matches within a 3 m distance margin require a directed-edge choice. This is geometry-only test positioning, not GPS certainty. The bounded graph contains 781 eligible edges. Search uses legal lane connections, a virtual start for same-edge reverse destinations, and clipped start/end edge fractions. Whole edge speed-limit estimates are scaled to the traversed fraction. Road-level endpoints and unmodeled intersection delay are explicit limitations.

`service.py` owns separate live state. It reuses AmbulanceAgent, TrafficAgent, PoliceAgent and SignalAgent structured interfaces, and HospitalAgent when a recent explicit ICU report meets its contract. A live suitability adapter handles the non-ICU case; positive reported beds and accepting status are mandatory. Geographic search is new; existing RouteScorer and PlanValidator validate cost components after graph connectivity validation. The existing EmergencyPlanner is not modified or forced to pretend an incident road is a hospital. Agents expose actual source time separately from assessment time.

`store.py` retains bounded incident/status/audit records; `server.py` enforces local RBAC and request boundaries. `__main__.py --mode live` starts neither SUMO nor TraCI. `--mode simulation` delegates to the preserved launcher. The additional dashboard mode link is the only change to the old Cesium page; runtime and its data remain separate.

`traffic.py` reuses TrafficObservation, RoadMatcher, TrafficService, FreshnessPolicy and ReplayTrafficProvider. It has **no network-provider activation path**. Eligible fresh directed matches also need at least 95% reverse longitudinal coverage of each full edge before they become full-edge costs; a measurement spanning multiple edges is not copied as a full travel time onto every edge. Source speed or geometry/time-derived speed supplies length-scaled costs. Partial/ambiguous/unknown/stale observations remain nonauthoritative. Closures use current stream state; reopenings replace closures. Future observations are quarantined before ordering. Fresh zero speed makes an edge unavailable; speeds >70 m/s are rejected as implausible prototype inputs.

Live reassessment uses current position and current costs. Known invalidation and position/hospital changes bypass soft-change delay. Otherwise an alternative needs a separate **60-second cooldown**, at least **30 seconds** and **10%** improvement; this is a prototype recommendation policy, not field-calibrated ambulance behavior. Approval is tied to the exact current recommendation ID and revalidated before acceptance. No ETA reports arrival. History is bounded to 50 entries and duplicate polling KEEP events are coalesced. This does not alter the V3 20-second Chennai simulation guard.

The SVG fallback and Cesium share actual WGS84 coordinates. Optional city overview uses attributed OSM tiles on explicit request, with at most 64 viewport tiles in the SVG path. Display outside the dashed pilot does not add routing coverage. Default offline operation loads retained pilot geometry only; no citywide geometry download or simulation was added. Browser verification limitations are recorded in V4_FEATURE_STATUS.md.
