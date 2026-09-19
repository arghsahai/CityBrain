# Subhashini planner subsystem

## Scope and ownership

This document describes the planner-facing state adapter, advisory agents,
route scoring, emergency planning, plan validation, and planner-level
replanning APIs implemented by Subhashini.

Responsibility is deliberately separated:

- **Implemented by Subhashini:** state adaptation for planner inputs, agent
  recommendations, route choice, `EmergencyPlan`, structured results,
  validation, planner policy, and replanning proposals/acceptance state.
- **Executed by Argh/runtime:** canonical state collection, action execution,
  route application, signal actuation, and runtime orchestration.
- **Simulated/validated by Krishna:** SUMO networks, scenarios, experiment
  runners, metrics, and frozen research evidence.
- **Future work:** real hardware, HIL, cameras, GPS, live feeds, physical
  signals, and real police/ambulance dispatch.

The planner decides; runtime executes; SUMO simulates; experiments evaluate.
No planner or agent module imports TraCI.

## Architecture

Canonical `CityState`/`VehicleState`/`RoadState` objects flow through the pure
adapter into a dictionary snapshot. Advisory agents and `RouteScorer` inspect
that snapshot. `EmergencyPlanner` returns a proposed `EmergencyPlan` plus an
auditable result. `PlanValidator`, `ReplanningPolicy`, and `Replanner` then
separate validation, proposal, decision, acceptance, and external execution.

## Input adapter

`citybrain.perception.adapt_city_state` copies only supplied values. It
preserves vehicle measurements, canonical road fields, `NO_TRAFFIC`,
`UNKNOWN`, zero travel time, explicit topology, and explicit blocked edges.
It does not infer resources, measurements, incidents, or availability; score
or select routes; or mutate its inputs.

`citybrain/core` is still absent from current `main`, although Argh's remote
core branch contains it. Adapter tests therefore use structural fixtures.
Production code relies on attributes rather than importing or copying Argh's
canonical classes, so canonical integration remains a separate boundary.

## Agent responsibilities

Every agent retains its legacy `run` interface and adds a structured method:

- `TrafficAgent.assess` records supplied congestion, assessment, advice, and
  reason for each road.
- `AmbulanceAgent.select` chooses only an explicitly available supplied
  ambulance and reports `no_available_ambulance` otherwise.
- `HospitalAgent.select` chooses only a supplied hospital with explicit ICU
  availability and reports `no_suitable_hospital` otherwise.
- `SignalAgent.recommend` creates advisory priority requests for known route
  junctions. It does not change a signal or claim a green corridor.
- `PoliceAgent.recommend` creates a logical accident-response advisory. It
  does not claim physical dispatch.

## Route scoring semantics

`RouteScorer.calculate_score(route, state)` remains the numeric compatibility
surface used by PR #4 instrumentation. `explain_score`/`score_route` returns a
`RouteScore` containing the route, per-edge components, supplied or estimated
travel cost, congestion penalty, availability, invalidating edge, final score,
and reason.

Positive supplied travel time is the base cost. The existing deterministic
penalties remain LOW=0, MEDIUM=5, and HIGH=15 seconds. `NO_TRAFFIC` adds no
penalty. `UNKNOWN` stays explicit and adds no penalty for compatibility.
Blocked, missing, negative, invalid, and infinite measurements make a route
unusable rather than artificially cheap.

A zero travel time is usable only for `NO_TRAFFIC` when positive finite
`road_length` (metres) and `speed_limit` (metres/second) are supplied; the
free-flow estimate is `road_length / speed_limit`. No units or measurements
are invented.

## EmergencyPlanner and EmergencyPlan

`EmergencyPlanner.create_plan` remains the legacy `EmergencyPlan | None` API.
`create_plan_result` (aliases `plan` and `create_structured_plan`) coordinates
traffic, ambulance, hospital, route, signal, and police agents and returns a
`PlanningResult`.

`EmergencyPlan` keeps its original required constructor fields. Optional
metadata now includes `plan_id`, `emergency_id`, `created_time`, structured
recommendations, status, revision, and parent plan ID. A new plan starts at P0
with `PROPOSED` status. Signal and police data are retained as advisory data.

## Structured outcomes and failure semantics

`PlannerOutcome` defines `PLAN_CREATED`, `KEEP`, `REPLAN`, `NO_ROUTE`,
`NO_RESOURCE`, and `INVALID_INPUT`. Results always carry a reason.

- No ambulance or hospital produces `NO_RESOURCE`.
- No candidates, or all blocked/unreachable/unscorable candidates, produces
  `NO_ROUTE`.
- Invalid emergency/state input produces `INVALID_INPUT`.
- The planner never fabricates a route, resource, measurement, or success.

## Plan validation

`PlanValidator.validate` remains a boolean compatibility API. It checks plan
existence, road existence, and blockage while tolerating legacy road records
without travel-time fields. `validate_structured`/`validate_result` adds strict
measurement checks and returns validity, reason, invalidated component,
replanning requirement, remaining route, and checked components.

Callers may provide the current remaining suffix so traversed history is not
revalidated. An ambulance already assigned to an active plan is not rejected
merely because it is unavailable for a new dispatch.

## ReplanningPolicy

`ReplanningPolicy` is an independent planner API with configurable absolute
minimum improvement, minimum commitment period, cooldown, and invalid-route
override. It returns `KEEP`, `REPLAN`, or `NO_ROUTE` with timing flags,
improvement, threshold, and reason. Defaults are neutral; S08 values are not
embedded as universal policy.

This policy is **not** inserted into PR #4's runtime gate. The legacy
`Replanner.replan` path performs candidate selection only, leaving PR #4's
route-suffix, improvement, commitment, blocked-route override, and physical
application logic unchanged. Policy is therefore not double-applied.

## Replanner and successive plans

The legacy `replan(current_plan, state)` continues to mutate and return the
supplied plan for runtime compatibility. It uses `calculate_score`, so PR #4's
`ScoreRecorder` still observes actual calls. This legacy mutation is confined
to that API.

The structured lifecycle is explicit:

1. `propose` returns a new candidate without mutating the current plan.
2. `replan_structured` combines proposal, current remaining-route validation,
   and one planner-policy decision.
3. Runtime may inspect and physically apply a proposal; this module does not.
4. `accept` records a successful logical acceptance and makes the proposed
   plan active.
5. `evaluate_active` evaluates later changes against that newest active plan.

Thus P0 accepted → P1 proposed/accepted → P2 proposed/accepted updates the
active plan at each acceptance; P2 is never evaluated relative to stale P0.

## KEEP, REPLAN, and NO_ROUTE

`KEEP` covers a matching best route, insufficient improvement, commitment, or
cooldown. `REPLAN` covers material improvements after configured gates and may
bypass optional-delay gates when the active remaining route is invalid.
`NO_ROUTE` means no usable candidate exists. Each decision exposes its reason.

## Auditability

Structured planning results include all candidate `RouteScore` objects and
agent results. Structured replanning results include current/proposed plan IDs,
current and remaining routes, candidate routes and scores, validation,
current/proposed score, improvement, threshold, timing-gate status, decision,
reason, and proposal reason. This data is returned, not hidden in console
printing.

## Integration contract

The runtime supplies measured state and candidate routes, executes an accepted
route or advisory action, and reports whether physical application succeeded.
Planner acceptance must follow external execution success when integrated.
Krishna's existing runtime experiment gate remains authoritative for PR #4's
validated code path. Frozen PR #4 evidence was neither regenerated nor claimed
as evidence for these new structured APIs.

## Testing

Unit tests cover adapter preservation/immutability, route-scoring edge cases,
structured and legacy agents, planner success/failures, remaining-route
validation, policy gates, structured proposals, explicit acceptance, P0→P1→P2
replacement, no-TraCI boundaries, and legacy PR #4 compatibility. Unit tests
require no SUMO process.

## Known gaps and demonstration prerequisites

Current `main` lacks Argh's canonical `citybrain/core` package. Before a final
end-to-end demonstration, the admin/team must integrate that canonical state
package and connect structured acceptance to runtime execution without
duplicating policy. Any physical signal priority, police dispatch, resource
reservation, multi-emergency allocation, and hardware/HIL integration remain
outside this module.
