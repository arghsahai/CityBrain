# V2.3 traffic evidence and candidate evaluation

The first V2.3 milestone adds an isolated offline evaluator. The existing
CityBrain planner, canonical SUMO road measurements, replan triggers, stability
guard, route validator and executor remain authoritative. The evaluator returns
a side-by-side cost comparison and evidence ledger; it does not call the planner
or commit a route.

`TrafficEvaluationConfig.enabled` defaults to `false`. With it disabled, adjusted
costs equal the supplied baseline scores. With it enabled, an observation is
eligible only when it has a supported provenance, fresh source time, known forward
direction, verified matched edge, at least 0.8 geometric confidence, at least 95%
coverage, and valid current/free-flow speeds. The result records each observation,
its provenance and timestamps, uncertainty, match confidence, acceptance and
rejection reason. Unknown-time TomTom data and stale, future, ambiguous, unmatched,
low-confidence or conflicting observations do not affect candidate costs.

For eligible observations the sidecar estimates a bounded segment delay from its
geometry length and speed measurements. Penalties are capped per edge and route.
Conflicting estimates on one edge quarantine that edge for the evaluation. This
is an experimental ranking signal, not calibrated travel-time prediction. It must
not be interpreted as evidence of response-time improvement. The same evidence
and routes should be used for paired baseline comparisons, retaining failures.

The component accepts normalized observation objects/dictionaries, candidate
routes, their existing baseline costs, and an explicit timezone-aware evaluation
time. Automated tests use fixtures; no HTTP provider or credential is needed.
Genuine live coverage and matching remain unverified. See
[`CHENNAI_LIVE_TRAFFIC.md`](CHENNAI_LIVE_TRAFFIC.md) for provider status and limits.
