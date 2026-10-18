# CityBrain V3.0 review and viva questions

**What is real in the digital twin?** The road geometry comes from OSM and vehicle,
road and signal measurements come from SUMO. Demand, disruptions, signal programs
and hospital availability are simulated.

**Does the provider integration prove live Chennai traffic?** No. HERE and TomTom
adapters are implemented but no genuine provider response was obtained in this
work. Replay and mocks test software handling only.

**Can provider traffic change ambulance routes?** No. It is advisory. A new,
disabled-by-default sidecar can compare candidate costs, but it does not invoke the
planner, mutate SUMO road measurements or commit routes.

**How is a route accepted?** The existing planner proposes it, existing validation
checks it, the route executor applies it in SUMO and the runtime reads back the
physical route before logical acceptance. The 20-second soft-change guard remains.

**Are real traffic signals controlled?** No. Only SUMO states are observed. Direct
phase writes are not used because the current request does not encode validated
movements, clearance transitions, minimum greens and a restoration policy.

**Does GPS track cars?** No. A browser user can explicitly consent to a local
device marker. The coordinate stays in tab memory and is never sent to the runtime
or a provider. It does not replace SUMO position.

**What does SUCCESS mean?** The ambulance reached the configured SUMO hospital
access road. It does not mean clinical admission, emergency service availability
or real-world dispatch readiness.

**What is the research claim?** This is a reproducible software demonstration.
The V3 evaluator has no controlled performance results yet. No improvement in
emergency response time is claimed.
