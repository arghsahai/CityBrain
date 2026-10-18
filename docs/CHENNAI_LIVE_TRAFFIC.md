# CityBrain V2.2 — Chennai advisory traffic

**INTERNAL STABILITY GATE PASSED.** This is an internal technical review, not
independent human sign-off. The reviewed base is
`4ed30b79b1ae1c8f1063fa4cd9d924762fc5cc0c`, including the Chennai 20-second soft-change
guard. Fetched `origin/main` (`fe471a863858489229c6bb956498405c77a2558e`) is already
an ancestor. Work is on `feature/chennai-traffic-providers`; shared main is unchanged.

**LIVE COVERAGE NOT VERIFIED — CREDENTIALS REQUIRED.** Neither `HERE_API_KEY` nor
`TOMTOM_API_KEY` was present. No traffic API transaction was attempted. Mock tests
establish software behavior, not Chennai coverage, accuracy, licensing or quotas.

## Architecture and isolation

HERE / TomTom / normalized replay → provider adapter → normalized observation →
directed geographic matcher → bounded background cache → existing telemetry.jsonl →
GET-only localhost server → existing Cesium viewer.

SUMO → Core → existing planner/scorer/validator/replanner/policy → Chennai guard →
verified executor remains authoritative. The new `traffic/` package imports none
of Core, TraCI or the planner. The launcher reads a snapshot only **after** the
runtime step; no external speed, closure or incident becomes a planner input.
No external-data-triggered ambulance replan or actual signal control is implemented.
The legacy point-fixture `ReplayProvider` remains for old evidence compatibility;
new launches exclusively use `ReplayTrafficProvider` and directed matching.
Legacy live names re-export the new adapters instead of duplicating HTTP logic.

The existing network is `simulation/chennai/network/chennai.net.xml`; sumolib uses
its retained geographic projection. The existing `geography.json` supplies Cesium
road coordinates. No network, official trial or teammate control component changes.

## Observation interface

`TrafficObservation` is a frozen dataclass with provider/segment/observation IDs,
directed WGS84 `(longitude, latitude)` polyline, nullable speed (m/s), travel time
(seconds), congestion (0–1), incident type/description, timezone-aware UTC source
and retrieval timestamps, provenance, freshness, match status/edges/confidence/reason,
raw permitted measurements and quality notes. `to_dict()` is JSON serializable and
always includes `applied_to_sumo=false`. Null means unavailable, not zero.
`observation_kind` separates FLOW from INCIDENT streams; optional `stream_id`
identifies an event across provider revisions. `matching_coverage` reports the
accepted-path longitudinal overlap fraction, including rejected low-coverage cases.

Missing, negative, boolean or nonfinite numeric measurements, naive timestamps,
invalid coordinates, individual geometry jumps over 2 km, overlarge geometry and
nonfinite raw data are rejected. An entire point-only record can be retained for
inspection, but cannot acquire a verified road match. Provider raw fields are
bounded to 64 KiB per record. A provider response is limited to 2 MiB/2,000 records.
HERE speeds stay in m/s; TomTom requests kmph and explicitly divides speeds by 3.6.
No travel time or congestion is fabricated from a missing measurement. Congestion
from HERE's documented 0–10 jam factor is scaled to 0–1; TomTom congestion is null.

## HERE setup and documented contract

Create a platform application/API key following the official
[HERE setup guide](https://docs.here.com/traffic-api/docs/send-request-readme).
Set `HERE_API_KEY` privately in the shell; never put it in browser code, Git or an
evidence file. Review account entitlements and charges before authorizing requests.
The default adapter uses [Traffic API v7 flow](https://docs.here.com/traffic-api/reference/traffic-api-v7-getflow)
with `in=bbox:west,south,east,north` and `locationReferencing=shape`.
It reads `results[].location.shape.links[].points` and `currentFlow`; documented
[flow measurements](https://docs.here.com/traffic-api/docs/flow) include `speed`,
`freeFlow`, `jamFactor` and `traversability`. Source freshness uses the response's
`sourceUpdated`, explicitly labeled as a source update, not an individual sensor time.
No advanced paid feature or deep-coverage parameter is enabled.

`HERETrafficProvider(incidents=True, ...)` also supports the separate
[incident endpoint](https://docs.here.com/traffic-api/reference/traffic-api-v7-getincidents).
This adds a transaction per poll and is disabled in the launcher. It reads the
incident ID, type and description, and uses source update time. HERE shape links
can be non-consecutive, so each link is a separate observation rather than a
fabricated bridge across a fork. Geometry fingerprints are explicitly local
fallback identifiers when the response does not supply a persistent segment ID.

## TomTom setup and documented contract

Set `TOMTOM_API_KEY` privately after reviewing your account access and terms.
The adapter uses the official [Flow Segment Data v4 contract](https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/traffic-flow/flow-segment-data):
`/traffic/services/4/flowSegmentData/absolute/16/json`, with one configured
`point=latitude,longitude`, `unit=kmph`, and `openLr=true` per poll. It reads
`currentSpeed`, `freeFlowSpeed`, `currentTravelTime`, `freeFlowTravelTime`,
`roadClosure`, `coordinates.coordinate` and optional `openlr`. A positive closure
is an advisory incident only. There is no separate incident-detail fetcher.

This endpoint does not supply a source measurement timestamp: freshness remains
UNKNOWN. Its documentation does not establish coordinate order as a driving
bearing; the adapter conservatively marks direction UNKNOWN. Consequently TomTom
flow is visible as a provider geometry overlay but cannot obtain a verified SUMO
match until a directional reference (for example validated decoded OpenLR) is added.
This is an explicit limitation, not an invented heading or a real coverage result.
A geometry fingerprint is used when OpenLR is absent.

## Authorization, failures and configuration

Credentials absent: `NOT_CONFIGURED`. Credentials present with authorization off:
`READY_BUT_NOT_TESTED`. Neither state performs a network call. The explicit launcher
flag `--authorize-traffic-requests` authorizes potentially billable requests for
that invocation; it is never inferred from a key. No automatic key discovery from
.env or secret files occurs. The adapters also accept `authorized=True` in Python.

Default request timeout is 5 s (configurable up to 30 s), polling 60 s. Authentication
errors (401/403), 429, timeout, outage and malformed data receive separate safe
statuses. Exception messages, provider error bodies and full URLs are never logged.
Redirects are rejected to prevent forwarding query credentials. Retry-After seconds
and HTTP dates are honored; failures otherwise wait at least 60 s. There are no
immediate retry bursts. HERE optional incidents currently fail the combined poll
if that second request fails; prior valid cache data remains available.

Constructors expose `study_bounds`, timeout and mocked transport injection. TomTom
also accepts a query point within those bounds. Bounds must be <=0.1 degree per
side; default is the existing VIT study area, not a Chennai-wide crawl.
`TrafficService` exposes `poll_seconds`, `max_records`, `FreshnessPolicy` and clock.
No keys leave the adapter. Provider payload fields are not accepted as error text.

## Offline replay

```sh
./tools/run_chennai.sh --traffic-source replay
```

The small bundled `simulation/chennai/scenarios/traffic-sample-v22.json` contains
three **SYNTHETIC_SAMPLE** observations on real imported road geometry. Speeds,
congestion and the sample incident are invented solely for pipeline demonstration.
They are not recorded Chennai traffic. The simulation replay clock starts at
2026-10-16 00:00 UTC and advances with simulation time, independent of execution date.

A normalized JSON file has `provenance` and `observations` keys. Each observation
uses the fields above, timestamps as ISO 8601 strings, and geometry as coordinate
arrays. Required identity/direction/retrieval/source fields are shown in the fixture.
Allowed provenance is `SYNTHETIC_SAMPLE`, `RECORDED_PROVIDER_DATA` or `REPLAY`.
Synthetic files retain SYNTHETIC_SAMPLE; provider recordings become REPLAY, with
recording provenance preserved. Rows are validated, invalid row indices reported,
and valid rows sorted by source time. Missing source times are rejected for replay
ordering. Fetches emit each chronological record once as the monotonic replay clock
advances. Restart the provider to rewind. Source timestamps are never rewritten.
Files are limited to 2 MiB and 2,000 records. Dashboard time seeking uses existing
recorded telemetry, not network requests or a second simulation.

## Geographic matching

The matcher projects provider geometry using the existing SUMO projection, samples
at <=10 m spacing and compares local directed tangents against passenger-road
segments. Default acceptance requires <=15 m distance and <=35° heading difference.
Non-connected competing roads within a 3 m distance margin are AMBIGUOUS; no edge
is assigned. Accepted sample sequences must move monotonically along an edge and
cross only actual directed outgoing connections. Reverse carriageways, cross streets,
short (<15 m) geometry, unknown direction and disconnected fragments are rejected
or explicitly insufficient. A provider segment may match a connected series of
SUMO edges. No provider road ID is treated as a SUMO edge ID.

The correctness hotfix additionally requires **95% longitudinal coverage** by
finite road segments on that accepted path (`minimum_coverage=0.95`, configurable).
For every provider leg, linear interval clipping constrains both the road-axis
projection to [0, road length] and perpendicular distance to the existing tolerance.
The union of those intervals gives length-weighted provider coverage; overlapping
road pieces are not double counted. Clamped endpoint buffers never count as extent.
A provider fragment fully inside a longer road is supported; insufficient partial
overlap is UNMATCHED with no SUMO edge assignment. The reviewed 40 m / 10 m case is
25% coverage and rejected. Up to 5% uncovered geometry permits small discrepancies;
this is a conservative pilot policy, not a calibrated matching accuracy claim.

Outputs are MATCHED / AMBIGUOUS / UNMATCHED / INSUFFICIENT_DATA, with reason,
provider segment ID, SUMO IDs and geometric confidence. Confidence is a heuristic,
not a calibrated probability. Tests cover synthetic opposite carriageways, close
parallel roads, intersections, missing geometry, connected multi-edge paths,
disconnection, plus the actual Chennai sample edge `-1192027270`.
The algorithm favors rejection; it is not a coverage-wide or surveyed matching study.
Only passenger-permitted edges participate; emergency-only roads are not inferred.

## Freshness and bounded service

Defaults: FRESH through 120 s, STALE through 600 s, EXPIRED thereafter. No source
time means UNKNOWN; a source clock >5 s ahead is UNKNOWN and quarantined before
it can replace current data or change the ordering watermark. Small tolerated
clock skew retains its signed age. Retrieval time never substitutes for source time.
These pilot thresholds are configurable, not calibrated provider guarantees.

One daemon worker performs non-overlapping fetches and matching. A bounded
last-valid cache holds 256 segment/type records by default (maximum 2,000), evicting
old insertion/update entries. Cache identity is provider + observation kind +
(stream ID, otherwise segment ID, otherwise observation ID). Closure state is not
part of identity: newer closure → open → closure values replace the current FLOW
record. Independent INCIDENT streams remain separate. HERE incidents use
`originalId` when available to retain identity across version IDs. When a provider
supplies no stable identity, the adapter's documented geometry fingerprint or
record identity is the compatibility fallback; changing/split geometry still needs
coverage validation. No arbitrary association between unrelated streams is inferred.

Duplicates require equality of normalized contents excluding retrieval time; reusing
an observation ID cannot hide a new state or bypass timestamp ordering. Older source
records cannot replace newer cached measurements. Unknown-time TomTom flow updates
retain UNKNOWN quality and use sequential poll arrival order, not invented source time.
The last valid observation survives outages with its own source age and failure
status; expired data is visibly historical. Future-dated records are excluded from
current observations and all overlays. A separate metadata-only quarantine history
holds at most min(64, cache size) records, always UNKNOWN, with rejection reason and
detection time; it is never automatically promoted. Subsequent valid records can
recover immediately because quarantine does not affect the current watermark.
The panel reports quarantined timestamp count; full diagnostics reuse the existing
external-data details. Repeated rejections are counted separately. `start()` is idempotent and single-use;
`stop()` returns immediately, wakes a waiting worker and discards late responses.
An in-flight socket finishes under its timeout; it does not hold up terminal cleanup.
Snapshot locks cover cache access only; network and matching hold no cache lock.

No database or raw provider recorder is added. Current normalized snapshots reuse
the existing pilot telemetry stream, whose simulation horizon bounds storage. The
cache does not append unbounded provider history. Replay input is bounded too.
Account licensing must permit any normalized/raw fields retained in pilot evidence;
only synthetic data was recorded during this milestone. Do not commit provider
recordings or enable licensed production retention without checking your agreement.

## Existing dashboard integration and source labels

The LIVE TRAFFIC OBSERVATIONS panel shows provider statuses, last successful poll,
source age, study bounds, record/match/unmatched/stale/unknown counts and safe errors.
Select a matched road from the dropdown or click a SUMO road to compare
SUMO_SIMULATED speed with separate external speed, free-flow speed, reported
congestion, segment ID, source timestamp and match reason. Unoccupied roads absent
from existing SUMO telemetry display unavailable simulated speed; no limit is
substituted for a measurement.

Existing SUMO congestion colors stay intact. Purple dashed provider polylines and
gold incident markers are separate entities at a different height. Grey external
lines indicate stale/expired/unknown time. The geographical SVG fallback includes
these separate layers. Provider geometry can be displayed even when unmatched;
its overlay description explicitly includes the match status. It never implies
that an unmatched provider measurement belongs to a nearby SUMO road.

Source values are SUMO_SIMULATED, HERE_LIVE, TOMTOM_LIVE, REPLAY,
SYNTHETIC_SAMPLE and UNAVAILABLE. NOT CONFIGURED and NO VERIFIED ROAD MATCHES
are explicit. No green live indicator is tied to a running fetcher. LIVE DATA
requires a successful current poll, actual live-provider provenance, FRESH source
time and a verified road match. Mock tests exercise that logic only. Recorded
viewer replay converts API source labels to REPLAY while preserving the recorded
source separately. Kept-open genuine provider observations age at GET time.
SUMO signals remain simulated and all recommendations advisory.

## Commands and verification

The non-networking readiness command never reads or displays key values:

```sh
venv/bin/python tools/verify_traffic_provider.py --provider here
venv/bin/python tools/verify_traffic_provider.py --provider tomtom
```

These report `NOT_CONFIGURED` or `CONFIGURED_NOT_VERIFIED`. To make exactly one
real request in a future, separately authorized check, use
`venv/bin/python tools/verify_traffic_provider.py --provider here --authorize-live-request`
(or `tomtom`). This opt-in command may incur charges. It reports a provider as
`VERIFIED` only after a genuine successful response with fresh source timestamps;
stale data reports `STALE`, unknown source time reports `UNKNOWN`, and errors
report their safe category. This implementation did not execute the live-request
command. Mocked and replay observations cannot verify provider connectivity.

```sh
# Existing default remains simulation-only:
./tools/run_chennai.sh --traffic-source simulation
./tools/run_chennai.sh --traffic-source replay
# Optional custom normalized replay:
./tools/run_chennai.sh --traffic-source replay --traffic-replay /path/to/recording.json
# Missing credentials / authorization => explicit advisory unavailability; SUMO continues:
./tools/run_chennai.sh --traffic-source here
./tools/run_chennai.sh --traffic-source tomtom
# Only after checking account terms and deciding to incur any charges:
./tools/run_chennai.sh --traffic-source here --authorize-traffic-requests --traffic-poll-seconds 60
# Fresh isolated fast run (choose a new directory each time):
./tools/run_chennai.sh --traffic-source replay --seconds-per-step 0 --no-server --no-browser \
  --output data/output/chennai/my-v22-run
venv/bin/python -m pytest -q
venv/bin/python -m citybrain.chennai.validate --historical --run data/output/chennai/my-v22-run
# Read-only dashboard of the completed recording:
./tools/run_chennai.sh --mode replay --events data/output/chennai/my-v22-run --no-browser --port 8772
venv/bin/python tools/check_chennai_browser.py --url http://127.0.0.1:8772 \
  --traffic --keep-at 61 --output /tmp/chennai-v22-browser
```

Old `--mode simulation|live-assisted|replay-assisted|replay` syntax is retained;
new `--traffic-source` explicitly overrides the old advisory selection. Existing
GPS replay stays synthetic and consent checked. Default dashboard persistence and
Ctrl-C behavior remain unchanged. `--exit-on-complete` closes a serving pilot at
terminal outcome; `--no-server` always exits after simulation.

Verification evidence and exact final outcomes: [V2.2 report](CHENNAI_V22_REPORT.md)
and `docs/chennai/v22/`. Original 180 trials are not regenerated.

## Limitations and next milestone

Live coverage, billable access, speed accuracy and licensing are unverified for
both providers. Only one TomTom query point is configured by default; it is not an
area coverage estimate. TomTom time/direction remain unknown. HERE shape-link
splitting favors correctness over long-segment continuity. No live GPS, real signal
control, clinical capacity verification or experimental performance improvement is
claimed. Mock data and synthetic replay cannot establish real-world congestion.

A future separately validated assimilation boundary would be: MATCHED FRESH traffic
→ calibrated road observation → CityBrain state → route evaluation → KEEP / REPLAN.
It requires authorized coverage sampling, directional reference validation, matching
accuracy evaluation, timestamp policy, unit/calibration checks, conflict resolution,
reproducibility and its own planner study. **That path is not activated in V2.2.**

Correctness hotfix results and limits: [CHENNAI_V22_HOTFIX.md](CHENNAI_V22_HOTFIX.md).
