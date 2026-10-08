# CityBrain Live Control Center

## Feasibility verdict and architecture

Implemented non-invasively. The frozen runtime already emits JSONL events containing
canonical road observations, planner decisions/scores, verified executions, accepted
revisions and terminal outcomes. No telemetry bridge or runtime edit is necessary.

```text
Frozen CityBrain runtime ↔ SUMO / TraCI
          |
          +→ existing events.jsonl → separate GET-only viewer → browser
```

There is no arrow from the viewer to runtime. The dashboard imports neither TraCI nor
planner/Core modules. It binds only 127.0.0.1, serves three fixed assets and one read-only
JSON endpoint, and has no route mutation, experiment launch or runtime control endpoint.
Replay controls select a display timestamp only; they do not advance SUMO.

## Technology and data contract

Python standard-library HTTPServer plus static HTML/CSS/JavaScript; no new runtime
packages, Node build or frontend framework. Incremental binary reading preserves partial
UTF-8/JSONL tails until newline, detects file replacement/truncation, and reports missing
or malformed input. Viewer memory is bounded by a 128 MiB source-file acceptance limit;
large archived traces should be viewed separately rather than treating this as a scalable
monitoring platform. Per-request reduction is designed for these small demonstration logs.

The browser polls every 500 ms. It renders text using textContent, not telemetry HTML.
Server paths are fixed and POST is unsupported. A replay cursor filters events by recorded
simulation time. No future plan/terminal outcome is shown before its recorded timestamp.
The full source duration is visible as replay metadata, not as a predicted outcome.

## Layout and honest status

The page displays simulation time, scenario label, emergency identifiers, last observed
edge/speed, current or archived accepted plan, plan history, last decision and policy gates,
candidate scores, road state, event timeline, agent recommendations and health information.
Large status cards emphasize revision/route/outcome; normal, warning and failure outcomes
use distinct colours and text. The five agent panels only show fields exposed by evidence.
Initial resource/traffic recommendations may be old; current roads and decision snapshots
carry their own observation times. Signal recommendations are advisory.

The scenario argument is a presentation label, not independently verified scenario identity.
Speed and state are last observations, not a direct current TraCI query. The health card
states that TraCI connectivity is UNKNOWN; fresh file reads are not a heartbeat. Evidence
failure information is shown when persisted, but memory-only writer errors cannot be
recovered from a failed disk write. The UI says so rather than showing a false healthy light.
Terminal state archives the last accepted plan; it does not suggest that runtime is still active.

## Start and demo

```sh
venv/bin/python -m citybrain.dashboard --events data/output/integration/faculty-s08/S08/runtime/events.jsonl --scenario S08
```

Open http://127.0.0.1:8765. The source may not exist yet; the viewer waits without creating it.
In another terminal, run the existing smoke command:

```sh
venv/bin/python -m citybrain.integration.smoke --scenarios S08 --candidate-source legacy-catalog --output data/output/integration/faculty-s08
```

For GUI, use `SUMO_BINARY="$(command -v sumo-gui)"` before the same smoke command and a fresh
output directory; press Play in SUMO if initially paused. The installed sumolib.checkBinary
supports that environment variable. Detailed two-terminal commands and S05 backup are in
[SLIDES_AND_DEMO.md](SLIDES_AND_DEMO.md). No source patch or route/threshold change is used.

Add `--replay` when presenting saved logs. Replay is prominently labelled. Use the slider
or Play recorded events; playback advances only display time, currently two simulated
seconds per wall second. Stop the viewer with Ctrl-C independently of the runtime.

## Failure isolation and validation

- Dashboard absent: CityBrain has no dependency on it; existing baseline runs remain valid.
- Source missing, incomplete, malformed or replaced: only the viewer's status changes.
- Browser disconnect: the HTTP response catches broken pipe; runtime has no involvement.
- Viewer killed during live S08: runtime continued with identical accepted plans, outcome,
  arrival/travel time and replan latencies compared with the frozen hotfix baseline.
- Serialization/persistence failure: the already-merged hotfix's regression tests remain
  passing; this dashboard introduces no new runtime serialization path.

Seven viewer tests cover real S05/S06/S08 traces, incremental/error handling, replay visibility,
HTTP read-only restrictions and import isolation. Browser automation checked S08 at
301/311/316/425, with zero JavaScript errors; desktop/tablet screenshots were inspected.
Fresh headless S05/S06/S08 runs retained SUCCESS/NO_ROUTE/SUCCESS and exact baseline plans.
The GUI S08 process also completed with P0/P1/P2 and 425-second success through the frozen
runtime. GUI test inputs differed only by generated gui_only start/quit-on-end/30 ms delay
options; scenario demand, seed, step length and policy were unchanged. This validates GUI
execution/telemetry, not a new visual inspection claim about the SUMO window itself.

Artifacts: `data/output/integration/dashboard-isolation-smokes/` and
`data/output/integration/dashboard-gui-smoke/`. No official trial was regenerated.
See VALIDATION.md for final checks and historical integrity.

## Files and scope

`citybrain/dashboard/{__init__.py,__main__.py,server.py,index.html,style.css,app.js}` adds the
isolated viewer. `tests/test_dashboard.py` adds contracts. `tools/build_krishna_package.py`
only reads official evidence and writes derived documentation/figures under docs/krishna.
No existing tracked implementation file is changed. Planner, scoring, models, Core,
executor, lifecycle, exception safety, scenarios, seeds and archived results stay frozen.

## Limitations

Local demonstration tool; no authentication, remote deployment, live connectivity probe,
telemetry backpressure/control, large-log pagination or clinical/operational readiness.
The 500 ms polling and JSON processing can consume host resources but create no logical
runtime dependency. A stalled writer can make the display stale; it cannot be diagnosed
fully from read-only files. In replay, stale source age is expected. Historical experiment
`events.json` is a different schema; this viewer consumes final-runtime JSONL only.
