# CITYBRAIN V2.2 — CORRECTNESS HOTFIX REPORT

The three correctness blockers reproduced against `b6bb67f2cf8195559aa0636641fc8ff04eb4e739`
are corrected on `feature/chennai-traffic-providers`. No V2.3 work, paid provider
requests, main changes, force pushes or automatic merges were performed. Existing
Draft [PR #9](https://github.com/arghsahai/CityBrain/pull/9) remains the review target.

## Root causes and exact corrections

1. **Longitudinal road coverage.** The old matcher checked distance to clamped
   road endpoints but not how much provider length actually overlapped finite road
   extent. The reviewed 40 m provider line over a 10 m road returned MATCHED.
   The matcher now clips each provider leg against finite road-axis extent and
   perpendicular tolerance on the accepted directed path, merges overlap intervals,
   and requires **95%** length-weighted coverage by default. Endpoint buffers add
   no length. Inadequate overlap returns UNMATCHED with no assigned SUMO edges,
   a coverage fraction and a reason. Provider fragments inside longer roads remain
   valid; up to 5% uncovered geometry is the documented pilot allowance. Direction,
   ambiguity, monotonic progress and connectivity checks remain in force. Commit
   `6760a68` was tested and pushed before moving to the next fix.
2. **Obsolete closures.** Including `bool(incident_type)` in cache identity separated
   closed and open versions of the same stream, so both remained current. Identity
   is now provider + FLOW/INCIDENT kind + stable stream/segment identity. Closure is
   mutable state. New FLOW records replace old closure/open states; older source
   updates are rejected. HERE incident versions use `originalId` when supplied,
   independently of the version segment ID. Independent incidents and flows cannot
   collide. Cesium entity IDs use the same kind/stable identity, and existing marker
   cleanup removes reopened closures. Deduplication compares complete normalized
   contents excluding retrieval time, so reused observation IDs cannot hide new
   states or bypass ordering. Commits `9250579` and `0bb421f` were separately tested
   and pushed. Legacy fixtures default to FLOW for compatibility.
3. **Future clock poisoning.** The old service classified future time only after
   replacing current cache state. A record one year ahead therefore prevented a
   corrected timestamp from passing its ordering check. Source times more than
   `FreshnessPolicy.future_tolerance` ahead (default 5 s) are now quarantined before
   matching/current-cache ingestion. They cannot update the current ordering
   watermark. The last valid record remains and subsequent valid records recover.
   Metadata-only quarantine history is independently bounded to min(64, cache size),
   stays UNKNOWN and is never automatically promoted. The dashboard shows its
   count. Missing source time remains UNKNOWN, including TomTom; retrieval time is
   not substituted. Commit `5f858b9` was tested and pushed as its own milestone.

## Reproduction and regressions

The three exact reproductions all failed on the original commit before production
edits; [before-reproductions.txt](chennai/v22-hotfix/before-reproductions.txt) retains
that output. All now pass.

**30 new pytest cases** (including parameterization):

- 15 coverage cases: exact 40/10 failure, one-/two-sided partial overlap, contained
  provider fragments, small allowed endpoint discrepancies, lateral offsets, curved
  connected multi-edge geometry, invalid configuration and all **744** eligible
  actual Chennai passenger-road geometries. The original reviewed case now reports
  **25% coverage / UNMATCHED**, and a mocked live-source row cannot claim LIVE DATA.
- 6 identity cases: closure → open → closure, delayed older states, independent
  incident/flow streams, HERE incident version identity, unknown-time TomTom reopening,
  and reused record IDs with timestamp ordering and genuine duplicate detection.
- 9 clock cases: exact year-ahead poisoning, 5-second tolerance boundaries, first-row
  quarantine/recovery, bounded immutable diagnostic snapshots, custom tolerance and
  missing-time behavior. Invalid future records never become current or fresh.

Final focused pipeline: **90 passed in 0.36 s**. Final full pytest: **405 passed in
38.17 s**. All ten legacy compatibility scripts exit zero. Python/JavaScript syntax
and diff whitespace checks pass. The existing guard/SUMO closure/execution/arrival
and terminal regression cases are included in the full suite. HTTP remains mocked.

## Chennai simulation, isolation and browser

| Fresh NORMAL seed-17 run | Outcome | Dispatch s | Arrival s | Travel s | Replans |
|---|---|---:|---:|---:|---:|
| Simulation | SUCCESS | 51 | 704 | 653 | 0 |
| Advisory replay | SUCCESS | 51 | 704 | 653 | 0 |

Accepted plans are identical. Both have no pending guard, zero telemetry/dashboard
write failures and no runtime evidence failures. The independent validators check
physical execution/read-back, actual hospital-road arrival, geographic alignment
and simulated signal changes. These are reproducibility/isolation observations,
not traffic-performance improvements or independent human sign-off.

Run provenance is preserved truthfully: the two long runs launched on clean
`5f858b9` after the three primary fixes; the subsequent reused-ID refinement in
`0bb421f` is covered by the final full suite. Raw logs remain in ignored
`data/output/chennai/v22-hotfix-{simulation,replay}`; they are not committed datasets.
A separate actual-SUMO provider-exception injection on the refined implementation
still dispatches at 51 s and reaches its expected 55 s TIMEOUT with normal guard
cleanup, zero telemetry/dashboard failures and no evidence failures. No external
provider object has a Core/planner/TraCI control reference.

The browser checks run on the newly generated replay with current renderer/service
code. They validate actual movement, hospitals, both simulated signals, accepted
route geometry, guarded KEEP, SUCCESS, 800 px layout, SVG fallback, source labels,
UNKNOWN/EXPIRED presentation and external overlay geometry. Backend-generated
synthetic closure/open/closure snapshots verify **1 → 0 → 1** incident markers in
both Cesium and SVG, including rejection of a delayed closure. An injected future
record preserves the current closure, shows quarantine count 1, and a subsequent
valid reopening clears both marker layers. These are explicitly synthetic UI tests,
not provider coverage observations. Browser evidence and screenshots are under
[chennai/v22-hotfix/browser/](chennai/v22-hotfix/browser/).

## Historical integrity, Git and remaining limitations

All **2,172 / 2,172** frozen entries match size and SHA-256, zero missing, extra,
changed or size mismatches. The official 180 trials were not regenerated. Shared
Core, agents, planner, `citybrain/main.py`, Chennai stability guard and imported
network are unchanged from the reviewed base.

The four implementation commits above were pushed individually. Verification,
updated setup guidance and this report form the final evidence/documentation
milestone, whose exact final local/remote SHA is reported in the delivery message.
No secrets, virtual environments, caches or raw generated datasets are included.
The final report records observed working-tree and PR status after push.

There are no remaining reproduced blockers from PR #9. Independent review is still
required. Real HERE/TomTom access, coverage, accuracy and licensing remain unverified;
no paid API request was made. TomTom still lacks validated direction/source time;
OpenLR decoding and external-data-assisted routing remain unimplemented. The 95%
coverage default is a conservative pilot setting, not a surveyed accuracy guarantee;
excessive geometry gaps are rejected rather than guessed. Geometry fingerprints
remain a fallback where providers supply no persistent segment identity, so changed
segmentation still requires separate live validation. Bounded quarantine retains
recent diagnostic history, not an unbounded incident archive. Original reports and
research conclusions are preserved.

## Reproduction commands

```sh
venv/bin/python -m pytest -q
venv/bin/python -m pytest -q tests/test_chennai_traffic_coverage.py \
  tests/test_chennai_traffic_streams.py tests/test_chennai_traffic_clock.py
# Choose fresh output directories for new runs:
./tools/run_chennai.sh --traffic-source simulation --seconds-per-step 0 --no-server --no-browser \
  --output data/output/chennai/my-hotfix-simulation
./tools/run_chennai.sh --traffic-source replay --seconds-per-step 0 --no-server --no-browser \
  --output data/output/chennai/my-hotfix-replay
venv/bin/python -m citybrain.chennai.validate --historical --run data/output/chennai/my-hotfix-replay
./tools/run_chennai.sh --mode replay --events data/output/chennai/my-hotfix-replay --no-browser --port 8773
venv/bin/python tools/check_chennai_browser.py --url http://127.0.0.1:8773 \
  --traffic --closure-hotfix --keep-at 61 --output /tmp/chennai-hotfix-browser
```

CITYBRAIN V2.2 HOTFIX COMPLETE — READY FOR INDEPENDENT REVIEW
