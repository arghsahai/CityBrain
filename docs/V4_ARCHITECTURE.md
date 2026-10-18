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
