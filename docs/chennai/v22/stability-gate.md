# Internal stability gate — 2026-10-16

INTERNAL STABILITY GATE PASSED

Base: 4ed30b79b1ae1c8f1063fa4cd9d924762fc5cc0c. All three requested historical
reports were read; the older blocked V2.1 audit was interpreted together with the
subsequent implemented hotfix, not treated as current code behavior.

| Criterion | Reviewed evidence |
|---|---|
| A — 20-second soft guard | SoftRouteGuard only replaces soft REPLAN results; suffix progress retains timer |
| B — hard bypass | Explicit blockage/physical failure bypass; actual SUMO emergency-permission diversion test |
| C — light queues | Transient stopped/queue observations defer and reset after recovery; no inferred permanent closure |
| D — stopped vehicle | Specific positive-count/zero-speed/infinite-time readings remain soft |
| E — sustained improvement | Finite and stopped persistent alternatives physically execute/read back at 20 s |
| F — policy/timing | Original minimum improvement unchanged; actual commitment/cooldown enforced for soft invalid overrides |
| G — physical execution | Original validation + executor + read-back precede acceptance |
| H — acceptance | Failed action/read-back preserves accepted plan; no unverified logical revision |
| I — terminal semantics | Actual hospital arrival evidence; false arrival rejected; explicit unreachable hospital NO_ROUTE + cleanup |
| J — no route hacks | Generic suffix/cost/physical checks; no route ID/seed/revision-count special case |

Fresh focused tests: `venv/bin/python -m pytest -q tests/test_chennai_stability.py tests/test_chennai_sumo.py`
→ **36 passed in 30.23 s**. These include actual SUMO startup, closures/diversion,
NO_ROUTE and heavier profile checks. Saved seed-19 full raw evidence independently
passes the read-only validator (arrival 900, one verified replan) and all 2,172
historical hashes match; see stability-gate.json.

A fresh base smoke was launched before provider work, with clean base provenance,
and subsequently finished SUCCESS at 704 s, dispatch 51, travel 653, zero replans,
no evidence/telemetry/dashboard failures. See baseline-smoke-validation.json and
smoke-comparison.json. No provider code ran in that baseline process.

Limitations retained: only evaluated recommendations establish persistence; real
sensor/permission-change detection is not introduced. Physical hard-route checks
in the guard operate on REPLAN proposals; this review does not broaden the original
runtime's perception contract. Missing/other invalid measurements retain the original
conservative override rather than being claimed as verified physical closures.
This is an internal Codex technical review, not independent human review or a new
research performance conclusion. Shared control code and the guard remain unchanged.
