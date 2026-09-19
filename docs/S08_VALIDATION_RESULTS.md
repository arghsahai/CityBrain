# S08 official V2 validation checkpoint

**Official dataset: V2, 60/60 trials, all post-run audits passed. Evidence classification: REPEATED MULTI-REPLAN EVIDENCE.** The S05/S07 validated 120-trial baseline is unchanged. These are separate datasets, not a pooled 180-trial experiment. S06 remains the unreachable-destination boundary case. The optional 560-trial suite was not executed. Scope remains software + SUMO; hardware is future work.

## Versions and provenance

| Version | Generating commit | Status |
|---|---|---|
| V1 | `b7842f4bf553586cf1e13015b3289fef82ed6970` | COMPLETED BUT SUPERSEDED FOR OFFICIAL ANALYSIS; all 60 outcomes preserved |
| V2 | `d380cb9216bff8d27bf72b3728220036cdb60a32` | Official, independently executed 60-trial matrix; audited and resume-verified |

V1's simulation outcomes are not fabricated or invalid. Its post-run saved-evidence audit found that generic JSON sanitization converted infinite ETA/cost values to null, and resume could not compare those values numerically. This violated the intended evidence round-trip contract. The original result/event hashes still match all 60 per-trial provenance records. A partial aggregate written by the unsuccessful resume was restored from those intact checkpoints without rerunning or changing any trial.

The V2 fix represents infinite S08 evidence values explicitly as JSON strings `Infinity` / `-Infinity`, preserves null for unavailable values, rejects NaN, and validates serialized evidence. It also defers checkpoint-only resume aggregate writes until validation succeeds. Its commit changes evidence/resume correctness only. Network, scenario timing, routes, candidate routes, generated demand, horizon and planner thresholds remain unchanged. The matrix definition changes only its version label. There was no seed-specific tuning. V1 and V2 must not be pooled as independent replications.

Before V2 execution, all implementation, analysis, tests and protocol were committed and pushed, and `git status` was clean. V2 ran headlessly from 2026-09-19 10:15:10 UTC to 10:22:52 UTC with Python 3.13.5 and Eclipse SUMO 1.27.1. Its execution fingerprint is `91f842136414cb68242ca720463f59e26836cbf74e7c9a827455f09b30dd273e`. The [manifest](../experiments/results/s08_validation_provenance.json) records the full definition, generating commit, timestamps, network hash and definition hash. Each trial preserves input/result/event hashes and its generating commit/fingerprint. The final documentation commit is separate from the generating revision.

## Matrix and measured outcomes

S08 × normal/heavy/peak × seeds 1–10 × static/dynamic = 60 trials and 30 matched pairs. Every pair has identical generated inputs and initial route/ETA, seed, ambulance, incident assumptions, horizon and hospital. Response strategy is the intended controlled difference.

| Demand | Static success | Static teleport | Dynamic success | Dynamic teleport | Dynamic 0 / 1 / 2+ replans | Dynamic travel mean / median / SD (s) | Mean applied latency (simulation s) |
|---|---:|---:|---:|---:|---|---|---:|
| Normal | 0/10 | 10/10 | 10/10 | 0/10 | 0 / 6 / 4 (0% / 60% / 40%) | 123.50 / 123.50 / 0.53 | 0.857 |
| Heavy | 0/10 | 10/10 | 10/10 | 0/10 | 0 / 2 / 8 (0% / 20% / 80%) | 123.50 / 123.50 / 0.53 | 1.111 |
| Peak | 0/10 | 10/10 | 10/10 | 0/10 | 0 / 2 / 8 (0% / 20% / 80%) | 123.50 / 123.50 / 0.53 | 1.056 |

Overall: 30 SUCCESS, 30 TELEPORTED, zero ERROR/TIMEOUT/other failures. All static trials have zero Replanner calls and zero CityBrain route changes. Dynamic distribution: zero replans 0/30 (0%); one replan 10/30 (33.3%); two or more 20/30 (66.7%). No trial made more than two. Mean applied route changes are 1.4, 1.8 and 1.8 by demand. Successful dynamic travel ranges from 123 to 124 seconds. Static successful-trip statistics are unavailable. There are **zero jointly successful pairs**, so no paired travel-time difference or travel-time superiority estimate is reported.

The [detailed metrics](../experiments/results/s08_validation_metrics.md) include ETA error, normal-traffic waiting/time loss, throughput, computation time, success uncertainty and all outcome counts. Mean initial ETA error is about 98 seconds; the current edge-cost ETA is not a calibrated arrival-time predictor. Successful-trip means alone are not evidence of general superiority.

## Continuous-replanning evidence

All 50 applied route changes passed saved-evidence checks. Logs preserve physical edge, speed/distance, prior full route and active suffix, observed roads, candidates and real scorer calls, current score, decision gate/reason, selected route, TraCI command and full/remaining route read-back. There were 3,428 actual Replanner calls and 6,746 candidate scorer evaluations, separate from dispatch and audit-only scoring.

Across all trials, the first meaningful E7 deterioration was observed at 308 s and the second E11 deterioration at 316 s. First applications occurred at 311–316 s; second applications at 320–321 s. These observation labels are distinct from incident departure/stop times and from candidate eligibility. Application latency is measured from the first meaningful eligible candidate to application: mean 1.02 simulated seconds, range 0–2, across 50 applications. Static application latency is unavailable, not zero.

Forty-six applications passed the benefit/commitment gate; four bypassed commitment because the active route was observed blocked. Ten applications involved infinite old ETA and finite candidate ETA, now explicitly retained in JSON. At application, every ambulance had travelled at least 104.54 m and had positive speed (minimum 8.51 m/s). Evidence therefore covers changed observed state, plan reevaluation and a physically applied valid route after dispatch, rather than merely counting setRoute requests.

## Audit and preservation

The [audit record](../experiments/results/s08_validation_audit.json) confirms:

- 60 unique expected identities, no missing/duplicate trials, 30 complete pairs.
- Strict disk JSON parsing and checkpoint round trips; aggregate CSV equals all checkpoint rows.
- Consistent success/teleport flags and successful/failure timing fields.
- Matching pair input hashes and generating commit/fingerprint; route-change counts match application events.
- Actual resume command loaded all 60 checkpoints and executed zero new trials; all per-trial hashes and modification times were unchanged, and aggregate/manifest bytes were unchanged.
- V1 versus V2 comparison found **zero differences** in completion status, travel time, route-change count, initial route, final route or teleport status across all 60 matching identities. Wall-clock runtime/computation timing is not expected to be identical.

Full local outputs remain in `experiments/results/s08-official-v1/` and `s08-official-v2/`, including trip XML and edge measurements. Compact tracked [V1 evidence](../experiments/results/s08_evidence_v1.tar.gz) and [V2 evidence](../experiments/results/s08_evidence_v2.tar.gz) preserve each version's manifest, aggregate CSV, and all 60 result/event/provenance/input XML/config sets. They retain every decision, including KEEP, and are not limited to successful runs. They omit bulky trip XML/edge CSV, which remain local. [Archive hashes](../experiments/results/s08_evidence_archives.json) support transfer verification. V1 retains its original null representation; it is not silently upgraded by the archive.

Extract the V2 archive into a fresh location to inspect or audit without running SUMO:

```sh
mkdir -p /tmp/citybrain-s08-evidence
# Use a fresh extraction destination; do not extract over original trial outputs.
tar -xzf experiments/results/s08_evidence_v2.tar.gz -C /tmp/citybrain-s08-evidence
python -m experiments.analysis.s08 /tmp/citybrain-s08-evidence/s08-official-v2 --output /tmp/citybrain-s08-report
```

The [protocol](S08_VALIDATION_PROTOCOL.md) documents exact run/resume commands. Resume requires the clean generating revision and matching runtime; after the final documentation commit, use a separate checkout of `d380cb9` for that operation. All original V2 trials are complete and need no reruns.

## Validation and interpretation

Before V2: 22 assertion tests passed, all ten unchanged teammate scripts passed, and paired S08 seed-1/seed-2 smoke trials plus disk-evidence validation passed. The focused tests cover infinite/missing costs, strict JSON, completed resume without reruns, changed-input rejection, aggregate preservation after late rejection, static zero replans, repeated route applications and physical route read-back. Existing teleport/completion tests remain unchanged. Final assertion tests and all ten teammate scripts were rerun successfully after preparing analysis/documentation.

The existing S05 actual sumo-gui and S08 headless demo verification from the merged baseline remains preserved; no completed demo was rerun unnecessarily. Its GUI process completed with TraCI evidence; earlier computer-use visual inspection timed out, so visual GUI inspection is not newly claimed.

Twenty V2 dynamic trials demonstrate two replans across all three profiles, with all ten seeds represented somewhere in that group. This satisfies the predeclared rule for **REPEATED MULTI-REPLAN EVIDENCE**. It is not classified as strong synthetic evidence: one engineered topology and incident schedule, limited candidate routes, no timing/topology sensitivity suite and no real-world calibration remain important limits. Ten trials per profile also leave substantial uncertainty (dynamic success 95% Wilson interval 72.2–100%; static 0–27.8%). No real emergency-response generalization is justified.

The [four-panel chart](../experiments/results/s08_validation.png) shows success/teleport counts, successful-trip-only mean travel, dynamic route-change distribution and per-application latency. The chart was visually inspected. Missing static latency denotes no applications; missing static travel denotes no successes.
