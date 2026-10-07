# Final software integration

The single-emergency runtime in `citybrain/main.py` owns coordination. SUMO remains physical truth. Core observes canonical CityState/RoadState/VehicleState; Subhashini's unchanged adapter, agents, planner, validator and ReplanningPolicy decide; the executor verifies physical actions before logical acceptance. The historical experiment runners, scenarios and 180 official trials are separate and unchanged.

## Architecture and execution order

`SUMO → Core refresh/events → adapt_city_state → current-position candidates → planner/validator/policy → physical validation → TraCI setRoute → exact read-back → logical acceptance → evidence/measurement → repeat`.

P0 is registered only after verified execution. P1/P2 proposals are validated and physically applied before `Replanner.accept`. A failed attempt does not advance revision, acceptance time, cooldown, active plan or accepted history. The executor checks whether the previous physical route survived and restores/verifies it when necessary. Verified recovery allows later reevaluation; inability to reconcile physical state terminates as EXECUTION_FAILED and archives the previous accepted history. Stale proposals and unexpected external route changes are rejected.

Runtime changes are confined to Core, integration support and orchestration; no planner algorithms or scenario XML are rewritten. Existing executor tests retain their assertions and now supply concrete position/topology mocks required by the stronger preflight contract.

## Commands and configuration

Install the existing SUMO requirements and pytest in your chosen environment. Run from the repository root:

```sh
python -m pytest -q
python -m citybrain.main simulation/scenarios/S05_dynamic_blockage/S05.sumocfg 900 --output data/output/integration/my-run
python -m citybrain.main path/to/config.sumocfg 900 --routes routes.json --hospitals hospitals.json --topology-fallback --minimum-improvement 5 --minimum-commitment 10 --cooldown 5 --reevaluation-interval 1 --candidate-limit 8
```

Output must be a fresh directory; existing directories are never overwritten. `experiments/results` is explicitly protected. By default the runtime creates a unique directory under ignored `data/output/integration`. The runner stops when the emergency is terminal, or at its horizon; it does not stop merely because the network is temporarily empty before future departures.

`RuntimeConfig` provides the same options programmatically. Its interval, improvement, commitment, cooldown and horizon must be positive and finite. The CLI starts one scenario-configured ambulance emergency; callers may explicitly supply an Emergency through `create_emergency_plan`. Simultaneous emergency allocation is not implemented. Ambulances already reserved or latched terminal are unavailable. Hospital ICU availability is a static configuration assumption, not a live capacity feed.

## Hospital and route contracts

Hospital JSON is a list, for example:

```json
[{"id":"H1","destination_junction":"J9","icu_available":true}]
```

Alternatively configure `destination_edge`; both fields together must both match. The legacy `location` field is accepted as a junction ID. Missing destination metadata or no suitable configured hospital yields an explicit ERROR. A route score cannot establish destination correctness.

Every application checks usable external edges, vehicle-class lane permissions, real SUMO lane-to-lane connections, current physical edge, no repeated-edge cycle, and hospital endpoint. The planner receives only current-position candidate suffixes. An internal junction defers evaluation/application until a compatible external edge is observed.

Omitted routes (`None`) enable up to eight simple topology paths ordered by observed travel cost. SUMO topology discovers any bypass; no S08 route is embedded. Enumeration has a 20,000-expansion bound, reported in evidence. Explicit `{}` means NO_ROUTE. A supplied nonempty catalogue is normalized to the current edge and validated. Optional `topology_fallback` discovers paths only once all catalogue suffixes are unusable. It never expands an explicitly empty catalogue. The unchanged planner chooses among the supplied candidates.

TraCI may retain travelled prefixes in `getRoute`. The executor compares the observed suffix at the current route index to the intended active suffix exactly, and requires the physical edge to remain unchanged across the synchronous command/read-back. No simulation step occurs between them. Partial overlaps and extra destination edges fail. A legacy full-route action can be normalized only if its travelled prefix exactly agrees with the observed route history. Live invalidation tracks remaining suffixes, excluding travelled roads.

## Continuous recalculation

ROAD_BLOCKED, ROAD_UNBLOCKED, CONGESTION_CHANGED and ROUTE_INVALIDATED trigger evaluation, alongside a configurable periodic interval (default one simulation second). Deferred internal-junction attempts are reconsidered on subsequent steps.

One authoritative `ReplanningPolicy` uses minimum improvement **5 score units**, minimum commitment **10 simulated seconds**, cooldown **5 simulated seconds**, and invalid-route override. Score units are the existing scorer's travel seconds plus congestion penalties; this is not the old experiment's 15% ETA rule. No second runtime decision gate is applied. The unchanged policy's invalid-route override includes blocked or otherwise invalid measured routes, not just a particular scenario incident. Candidate latency measures the first observed materially eligible proposal to its verified acceptance; physical execution computation time is not the same metric.

## Terminal lifecycle

- SUCCESS: a TraCI arrival event, no latched teleport, and the preceding physical observation on the accepted destination edge at the final route index, matching the selected hospital.
- TELEPORTED: terminal failure, including when SUMO keeps the vehicle active or later reinserts it. A later arrival cannot replace this outcome.
- NO_ROUTE: explicit empty candidates, or topology proves no hospital path under current observed blockages. This is a current-blockage boundary, not a claim that an incident can never clear.
- Temporarily infinite measured costs or a limited catalogue with topology still reachable produce NO_ROUTE_WAIT and later reevaluation, bounded by the horizon.
- FAILED_BLOCKED: unexplained disappearance or unverified/wrong-destination arrival; its name does not establish the physical cause.
- TIMEOUT: the configured horizon expires.
- EXECUTION_FAILED: initial execution fails, physical recovery is unverifiable, or an uncommanded route change is detected.
- ERROR: configuration, perception or other runtime exceptions.

Terminal outcomes are immutable, persist a summary, release the reservation, clear runtime/replanner active state and stop replanning. Accepted plans remain immutable historical snapshots. Travel/arrival metrics are populated only for verified SUCCESS. Arrival verification is deliberately conservative: very large time steps that skip the final edge cannot establish success from the preceding observation; the supplied runner uses a one-second step.

## Evidence and signals

`events.jsonl` stores immutable strict JSON snapshots: time and resource IDs, physical position/index/suffix, active plan, road observations, candidate routes/scores/rejections, structured planner validation/decision/reason/gates, requested action, execution/read-back/recovery, accepted revision, latency, lifecycle observation and terminal metrics. Infinite costs use explicit JSON strings; null means unavailable. `summary.json` is replaced atomically at termination. Provenance includes Git revision, dirty-tree flag, source fingerprint, input hashes, seed, Python/SUMO versions and UTC start time.

Each accepted plan's SignalAgent recommendations pass through SignalExecutor. Evidence records junction, recommendation, reason and `execution_attempted=false`, with advisory results marked `executed=false`. No physical signal priority, phase forcing, restoration or green corridor is claimed.

## Reproduce lightweight integration smokes

```sh
python -m citybrain.integration.smoke --output data/output/integration/topology-smokes
python -m citybrain.integration.verify data/output/integration/topology-smokes
python -m citybrain.integration.smoke --candidate-source legacy-catalog --output data/output/integration/catalog-smokes
python -m citybrain.integration.verify data/output/integration/catalog-smokes
```

Both commands use the same normal-demand seed-1 S05/S06/S08 definitions generated by the existing scenario utility into fresh integration directories. The catalogue command reads the existing four routes and uses generic topology fallback; it contains no S08 bypass literal or scenario-time policy. Each smoke is a runtime demonstration, not a regenerated research trial or statistical result. The full historical 180-trial datasets must not be pooled with these outputs.

The verifier checks saved JSON, execution-before-acceptance ordering, exact physical suffixes, sequential revisions, lifecycle evidence, signal advisory status, final outcome/timing consistency, and input hashes. Regression tests additionally inject failures and validate terminal latching, policy gates, candidate normalization and topology contracts.

## Limits

One emergency, configured candidate bounds and static hospital availability remain explicit limits. Lane topology/permissions are cached for the duration of a run; runtime lane-permission changes require invalidating/rebuilding that cache. Road blockage and measured costs remain live. The topology search is not a calibrated citywide traffic assignment model. Full evidence is retained in memory as well as on disk, so very long runs need a streaming retention policy. Signal actuation, hardware, real sensing and real-city validation remain future work.
