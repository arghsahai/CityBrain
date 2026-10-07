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
