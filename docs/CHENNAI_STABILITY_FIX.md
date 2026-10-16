# CITYBRAIN V2.1 — REPLANNING STABILITY FIX

The Chennai-only hotfix is implemented and verified. The shared planner, scorer,
validator, replanner, policy, executor, Core and research runners remain unchanged.
No HERE/TomTom integration was started.

1. **Root cause.** Core deliberately reports infinite travel time for stopped
   traffic. PlanValidator calls that `unreachable_edge`; ReplanningPolicy's configured
   invalid-route override bypasses timing gates. The policy behaved correctly for
   its supplied validation result. The missing distinction was at the Chennai
   integration boundary: a single stopped vehicle was allowed to trigger the same
   immediate acceptance path as an explicit closure. Finite score fluctuations
   also repeatedly selected different future corridors before their divergence.
   Neither actual signal causation nor a real closure is established for the two
   stopped-vehicle observations; they must not be called confirmed road closures.
2. **Affected modules.** New `citybrain/chennai/stability.py` implements a small
   `ChennaiRuntime` subclass and pure `SoftRouteGuard`. `chennai/run.py` selects that
   subclass and exposes its single confirmation parameter. The dashboard reducer
   consumes the separately recorded effective decision. All listed teammate-owned
   routing/control components are untouched, including `citybrain/main.py`.
3. **Previous timeline.** [The compact timeline](chennai/stability/before-timeline.md)
   shows all eight original replans, route/candidate corridors, trigger reasons,
   scores and VERIFIED executions. At 91 and 97 s a single vehicle at 0 m/s,
   without an explicit blockage flag, invalidated a future edge. The 97-s switch
   followed acceptance by only six seconds. Full routes, score inputs, event trigger
   types and source hashes are in `before-replans.json` and the prior V2.1 audit.
4. **Stability mechanism.** One new threshold: **20 simulation seconds** of the
   same usable soft REPLAN recommendation at evaluated observations. This spans two
   nominal 10-s reevaluation intervals and filters the observed 6/10-s reversals.
   A new candidate or KEEP/NO_ROUTE resets confirmation. Progress along the same
   route suffix does not reset it. Internal-junction deferrals do not invent a new
   observation. Existing commitment and cooldown are additionally checked against
   actual acceptance times for soft invalidation overrides. There is no new score
   threshold, smoothing model, forced revision count, route-ID rule or artificial
   planner delay. No canonical measurement or score is changed.
5. **Hard/soft distinction.** Explicit remaining-route blockage and failed physical
   route validation bypass confirmation for a REPLAN proposal. Genuine NO_ROUTE
   handling remains in the original runtime, before the guard. Valid finite cost
   changes and specifically identified stopped-vehicle infinities are soft. Missing
   or otherwise invalid measurement contracts retain conservative existing handling;
   the guard does not assert they are real-world closures. Confirmed hard handling
   still uses the original executor and read-back before logical acceptance.
6. **Files changed.** Control implementation commit `6a62e932e75bc5bb45ab09c757a3c62012e0ecdf`:
   new stability module and unit tests; launcher integration; existing dashboard
   reducer; SUMO closure tests; browser QA and read-only replan audit tool; a small
   renderer diagnostic improvement preserves the cause of a 3D fallback. Follow-up
   observation commit `ad141eee088b1fd25044d594671418c34974b3b1` removes duplicated
   STABILITY_DECISION context from compact dashboard records; complete raw audit
   logs remain unchanged. This keeps the seed-19 recording within the existing
   viewer size limit (138.52 → 98.21 MiB). New local compact streams were reprojected
   with this function after the simulations; raw events/telemetry were preserved. This
   report, usage updates and `docs/chennai/stability/` evidence form the separate
   documentation/verification commit. Exact inventory: `git diff --name-status
   fc9c887..HEAD`.
7. **Tests added.** 30 deterministic guard/integration cases cover temporary stops,
   signal-like queues, brief spikes, persistent congestion, sustained alternatives,
   alternation, suffix progress, commitment/cooldown, hard blockage/disconnection,
   NO_ROUTE, verified/failed/read-back execution, evidence failures, exceptions,
   terminal cleanup, teleportation, true/false arrival and dashboard KEEP records.
   Three additional actual-SUMO cases extend the existing tests to guarded NO_ROUTE
   and baseline/guarded physical emergency-road restrictions with a verified diversion.
8. **Tests passed.** Complete pytest: **315 passed in 34.02 s**. The six dedicated
   actual-SUMO cases passed, including both higher-demand startup checks. All ten
   legacy teammate scripts exited zero. JavaScript syntax and Python compilation
   checks passed. The read-only audit's four regression tests also passed after
   its metrics extension.
9. **Before/after comparison — observed results.**

   | Run | Outcome | Dispatch s | Arrival s | Travel s | Verified replans | Earlier-corridor returns | Planner evaluations |
   |---|---|---:|---:|---:|---:|---:|---:|
   | Before, seed 17 | SUCCESS | 51 | 759 | 708 | 8 | 6 | 627 |
   | Guarded, seed 17 | SUCCESS | 51 | 704 | 653 | 0 | 0 | 583 |
   | Guarded, seed 18 | SUCCESS | 51 | 705 | 654 | 0 | 0 | 576 |
   | Guarded, seed 19 | SUCCESS | 51 | 900 | 849 | 1 | 0 | 756 |

   Network, route-demand and SUMO configuration hashes match exactly for the
   seed-17 pair. The scenario script is unchanged, but its second restriction
   deliberately targets the then-accepted route. Therefore its realized target
   and time change: before `24160185#49` at 587 s, after `30424374#8` at 210 s.
   Arrival is 55 s earlier in this pair; this is an **OBSERVED DIFFERENCE**, not an
   isolated causal estimate, calibrated traffic result or guaranteed improvement.
10. **Replans.** Seed 17: 8 → 0. No revision count is imposed. In seed 19 the actual
    alternative remained recommended from 231 to 251 s; one soft replan was
    physically verified and accepted at 251 s after exactly 20 s of confirmation.
    Persistent-congestion unit sequences also accept a verified alternative. Zero
    accepted changes in seeds 17/18 does not mean their planner stopped evaluating.
11. **Corridor reversals / unnecessary changes.** Recorded earlier-suffix returns
    decrease from 6 to 0 in seed 17; all three guarded runs have zero returns.
    The number of *unnecessary* changes is not directly observable without a
    counterfactual. Suffix returns are an explicit stability proxy, not proof that
    every old switch was harmful or that every future decision will be optimal.
12. **Genuine blockage response.** Actual SUMO tests physically disallow the
    emergency class on a future divertible road and supply the explicit Core
    closure flag. Both runtimes physically execute/read back a route avoiding it.
    The guarded decision is `HARD_FAILURE_BYPASS`, not a soft confirmation wait.
    Closing the hospital destination produces immediate NO_ROUTE and cleanup.
    A deterministic six-second post-acceptance hard-block case also bypasses the
    soft window; a corresponding temporary-stop case enforces commitment instead.
13. **Final arrival.** All three full guarded runs independently pass actual ARRIVED
    evidence, accepted destination edge, read-back/execution ordering, geographic
    alignment and changing signal-state audits. They end with no pending guard,
    no telemetry/dashboard/evidence failures and no fabricated arrival. Success
    denotes the mapped hospital access-road endpoint, not medical admission.
14. **Travel, evaluation frequency and latency.** Seed-17 guarded travel is 653 s.
    The nominal reevaluation interval remains 10 s with the same event triggers.
    Effective evaluation rates are about 0.888/s before and 0.896/s afterward over
    their observed evaluation spans. Counts differ because trajectories/duration
    differ. The guard never skips the upstream planner evaluation. Internal junctions
    still defer planning/execution; maximum observed gaps are 4 s before and 12/17/25 s
    in guarded seeds 17/18/19. Existing original reported replan latency is 0 s for
    the eight before acceptances. Guarded seed 19 records 20 simulation seconds from
    first consistent recommendation to acceptance; the hard-block unit test records
    0 s of guard delay. This is simulation-time confirmation latency, not a CPU
    benchmark or artificially slowed planner computation.
15. **Browser.** Fresh Chrome WebGL QA passes with zero page errors: actual guarded
    KEEP at 61 s, unchanged accepted P0, moving ambulance/vehicles, exact displayed
    route geometry matching backend coordinates, actual signal states, terminal
    SUCCESS at the new 704-s time, SVG fallback and 800-px layout. The QA tool now
    reads the recording's terminal time instead of assuming 759 s. Screenshots and
    checks are in `chennai/stability/browser/`. A second recording (seed 19) verifies
    actual accepted P1 at 251 s, verified execution, updated route geometry and
    terminal SUCCESS at 900 s, with zero page errors; see `browser-seed19/`.
    An initial browser attempt entered
    fallback; the renderer now retains its error reason. The final QA run passed.
16. **Historical integrity.** All **2,172 / 2,172** frozen entries match size and
    SHA-256, with zero missing, extra or changed entries. No official experiment
    trial was regenerated. Three new isolated runs live under ignored
    `data/output/chennai/stability-seed{17,18,19}/`.
17. **Remaining limitations / UNVERIFIED EXPECTATION.** Twenty seconds is a configurable
    pilot default supported by the audited transient switches and these tests, not
    a generally calibrated optimum. Consistency is confirmed at evaluated samples,
    not continuously between them. A real useful soft alternative can lose its
    opportunity before confirmation; these tests do not prove globally optimal
    travel. Only three NORMAL seeds were run end-to-end. Dynamic physical restrictions
    are tested with explicit closure flags; comprehensive sensor/permission-change
    detection remains outside this hotfix. Raw evidence is intentionally verbose.
    No live traffic, clinical capacity, surveyed real signal control or real GPS
    tracking is added.
18. **Git.** Branch: `feature/chennai-live-traffic`. Base:
    `fc9c88761c97ff5b36027b6437240da91ea9c581`. Implementation commit above; final
    documentation HEAD is reported in the delivery message (`git rev-parse HEAD`).
    Local commits only; no main edits, reset, force push, push or merge. Per-run
    provenance truthfully records implementation-time working-tree state; the
    reports do not relabel those runs as clean-release runs.
19. **Next implementation stage.** Independent review of this guard and its hard
    bypass/latency evidence. After stability sign-off, resume the separately scoped
    advisory traffic-provider stage. HERE/TomTom work was not started here.

Launch the guarded pilot:

```sh
./tools/run_chennai.sh
# Configurable single soft-confirmation window and demand seed:
./tools/run_chennai.sh --confirmation-seconds 20 --seed 19
# Fast validation; always choose a fresh output directory:
./tools/run_chennai.sh --seed 17 --seconds-per-step 0 --no-server --no-browser \
  --output data/output/chennai/my-new-stability-run
venv/bin/python -m pytest -q
venv/bin/python -m citybrain.chennai.validate --historical \
  --run data/output/chennai/my-new-stability-run
venv/bin/python tools/audit_chennai_replans.py \
  data/output/chennai/my-new-stability-run/runtime/events.jsonl \
  --output /tmp/my-stability-audit.json
```

Machine-readable comparison: [comparison.json](chennai/stability/comparison.json).
Per-seed source hashes, routes, evaluations and independent audits are retained beside it.

CITYBRAIN REPLANNING STABILITY — READY FOR INDEPENDENT REVIEW
