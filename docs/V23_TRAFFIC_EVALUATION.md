# V3.1 experimental traffic evidence and candidate evaluation

The evaluator is an isolated experimental sidecar. The existing
CityBrain planner, canonical SUMO road measurements, replan triggers, stability
guard, route validator and executor remain authoritative. The evaluator returns
a side-by-side cost comparison and evidence ledger; it does not call the planner
or commit a route.

The runtime/dashboard feature is disabled unless the user passes
`--experimental-traffic-evaluation`. This flag only displays a comparison and
advisory recommendation; it cannot execute a route. `TrafficEvaluationConfig.enabled`
defaults to `false`. With it disabled, adjusted costs equal the supplied baseline
scores. With it enabled, an observation is
eligible only when it has a supported provenance, fresh source time, known forward
direction, verified matched edge, at least 0.8 geometric confidence, at least 95%
coverage, and valid current/free-flow speeds. The result records each observation,
its provenance and timestamps, uncertainty, match confidence, acceptance and
rejection reason. Unknown-time TomTom data and stale, future, ambiguous, unmatched,
low-confidence or conflicting observations do not affect candidate costs.

For eligible observations the sidecar estimates a bounded segment delay from its
geometry length and speed measurements. Penalties are capped per edge and route.
Conflicting estimates on one edge quarantine that edge for the evaluation. The
separate recommendation helper also requires known connected directed routes,
minimum absolute and relative improvement, satisfied commitment and cooldown,
and absence from recent-route history. It emits KEEP,
ADVISORY_RECOMMENDATION or NO_ROUTE with per-candidate reasons. These decisions
are display-only; `planner_invoked`, `route_committed` and
`canonical_measurements_modified` remain false. This is an experimental ranking
signal, not calibrated travel-time prediction or evidence of response-time
improvement. Paired comparisons must retain failures.

The component accepts normalized observation objects/dictionaries, candidate
routes, their existing baseline costs, and an explicit timezone-aware evaluation
time. Automated tests use fixtures; no HTTP provider or credential is needed.
For an explicit replay experiment in the dashboard, use
`./tools/run_chennai.sh --mode replay-assisted --experimental-traffic-evaluation`
with a fresh output directory. The opt-in `EXPERIMENTAL ROUTE ADVISOR` panel
shows candidate scores and evidence. The ordinary launcher does not enable it.
Genuine live coverage and matching remain unverified. See
[`CHENNAI_LIVE_TRAFFIC.md`](CHENNAI_LIVE_TRAFFIC.md) for provider status and limits.
