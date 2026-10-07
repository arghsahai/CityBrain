# Evidence exception-safety hotfix

PR #7 was merged as `37ea15bf19d762883769c6964a807455131aae17`.
Its independent review reproduced an evidence-write failure after verified physical
P1 execution but before logical acceptance. A second failure writing TERMINAL
interrupted cleanup, leaving logical P0, physical P1 and a retained reservation.

## Fix and invariants

`CityBrainRuntime._record_evidence` now isolates snapshot and writer exceptions from
control flow. It returns structured status and records failures directly in memory,
without recursively using the writer. Directory-access errors use the same diagnostic
mechanism; explicit protected paths and existing output directories still fail early.
The low-level EvidenceWriter remains strict, so direct callers still see its errors.

1. Verified physical execution proceeds to logical acceptance despite evidence failure.
   Failed physical execution still follows the unchanged executor reconciliation path.
2. Terminal cleanup clears runtime/replanner active plans, registered routes, policy
   timers and reservations before attempting terminal snapshot/event/summary reporting.
   Accepted plan history is preserved. Evidence cannot prevent cleanup.
3. Terminal outcomes remain immutable; subsequent steps do not advance or replan.

Diagnostics include event type, simulation time, exception type/message/errno, associated
plan ID, physical execution attempted/verified, logical acceptance completion and cleanup
completion. Completion fields are refreshed after acceptance and finalization. For events
without an execution result, physical status describes previously accepted execution.
The summary adds `evidence_failures`; other event fields remain compatible. TERMINAL's
`active_plan` is now null after cleanup, while `last_accepted_plan` preserves the archive.

## Coverage and regression

Complete pytest: **252 passed**, including all previous 227 cases and 25 new cases.
All ten standalone legacy scripts passed. `git diff --check` and changed-file AST
checks passed. The new tests retain the actual planner, policy, route executor and
stateful physical-interface double; only storage faults are injected.

Coverage includes exact ENOSPC during P1/P2 execution evidence, initial P0 evidence,
normal execution failure, verified rollback, failed rollback, all terminal outcomes,
real lifecycle dispatch for teleport/arrival/unreachable state, repeated post-terminal
steps, serializer errors, writer exceptions, unavailable directories and summary-only
failure. Optimized-Python verification and smoke failure exit status are also tested.

No planner, Core executor, scenario, scoring or experiment implementation is rewritten.
All 2,172 historical files match their recorded hashes and sizes. Official trials and
existing evidence archives are unchanged.

## Small review cleanups

The saved-evidence verifier uses explicit exceptions rather than removable assertions.
The smoke command saves all results, then exits non-zero for unexpected scenario outcomes,
unfinalized state, evidence failures or missing P2 in the catalogue S08 demonstration.
Documentation now records that PR #7 is merged rather than awaiting merge.

## Limits

Failed evidence is observable in memory, but is not guaranteed durable when storage is
unavailable. No retries, alternative disk destination or crash-recovery transaction log
are introduced. Process termination or memory exhaustion is outside this in-process
exception-safety contract. Existing single-emergency, static-hospital, bounded-search,
cached-permission, signal-advisory and archive-path portability limitations remain.

Run `python -m pytest -q`, the ten root `test_*.py` scripts, and the smoke commands in
[FINAL_INTEGRATION.md](FINAL_INTEGRATION.md). Use a fresh output directory for each run.

## Fresh SUMO verification

Generating commit: `b88015815a20cb1f394638ecb55d8e611cc79682`; all three runs recorded
a clean working tree. Python 3.13.5 / SUMO 1.27.1, normal demand, seed 1, existing
catalogue plus generic topology fallback. No policy or scenario settings changed.

| Scenario | Outcome | Terminal time | Travel time | Accepted revisions |
|---|---|---:|---:|---|
| S05 | SUCCESS | 335 s | 34 s | P0, P1 |
| S06 | NO_ROUTE | 316 s | unavailable | P0, P1 |
| S08 | SUCCESS | 425 s | 124 s | P0, P1, P2 |

S08 acceptance times were 301, 311 and 316 seconds. Every accepted route has preceding
verified physical read-back. Both successful runs have hospital arrival evidence and no
teleport. All three cleared active state/reservations and recorded zero evidence failures.

```sh
python -m citybrain.integration.smoke --candidate-source legacy-catalog --output data/output/integration/exception-safety-hotfix-smokes
python -O -m citybrain.integration.verify data/output/integration/exception-safety-hotfix-smokes
```

Both commands exited zero. Existing directories are not overwritten: choose a new output
name when reproducing. Raw outputs remain in that ignored integration directory, separate
from official experiments. Event stream SHA-256 values:

- S05: `6de33c814191364d26a7e886226201ec12ea721c69eabe6cd8caa2858bd83f05` (77 records)
- S06: `a71bde0d6cb89a890353634cf8c15a06d4b0674d74669320407675b907570eac` (40 records)
- S08: `d2887ccda8403b05f77b2ca1f3e9420316b4228e9478220f412f51cf619a33c7` (322 records)

The exact review fault injection now leaves logical/physical/registered P1 all equal to
`[a, c, z]`, with no terminal error caused by the writer. Subsequent TIMEOUT finalization
with failing TERMINAL and SUMMARY writes leaves active plan null, reservations empty,
registered routes empty, accepted P1 history preserved, and repeated steps unchanged.
In-memory diagnostics report OSError, errno 28, successful physical verification,
completed logical acceptance and completed cleanup. No real disk was damaged or filled.
