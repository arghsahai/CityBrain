# CityBrain team quick start

Latest complete branch: **feature/krishna-watchable-demo**. It includes the validated runtime baseline, Krishna research package, read-only dashboard, paced S08 launcher and local 3D viewer.

## Pull the shared work

Save your own changes before switching branches. In an existing repository:

```sh
git fetch origin
git switch --track origin/feature/krishna-watchable-demo
```

If you already have this branch locally, use `git switch feature/krishna-watchable-demo` followed by `git pull --ff-only`.

## Install once

Install Eclipse SUMO (tested with 1.27.1), with `sumo` on PATH; `sumo-gui` is optional. Use Python 3.10 or later (validated with 3.13). From repository root:

```sh
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Windows activation: `venv\Scripts\activate`. Use your activated environment in both terminals. Three.js is bundled with its MIT license; no npm/CDN setup is required. Browser needs WebGL2.

## Fresh live 3D demo

Start viewer first in terminal 1:

```sh
python -m citybrain.dashboard --events data/output/team-s08-live/runtime/events.jsonl --scenario 'DEMO S08 3D LIVE' --port 8778
```

Terminal 2:

```sh
python -m citybrain.demo --headless --output data/output/team-s08-live
```

Open **http://127.0.0.1:8778/3d**. Ordinary dashboard: http://127.0.0.1:8778/. Omit `--headless` for a separate SUMO GUI window. Default pacing gives approximately 4 minutes 23 seconds after warmup. Every new run requires an unused output directory; change both commands together. Stop either process using Ctrl-C in its terminal.

## Replay the already completed fresh live demo

The checked-in archive preserves the actual completed local 3D demo, separate from official experiments. It includes snapshots, metadata, summary and telemetry health, without process IDs or machine-specific launch configuration. No new SUMO run is needed:

```sh
python -c "import pathlib,tarfile; p=pathlib.Path('data/output/shared-s08-replay'); p.mkdir(parents=True,exist_ok=False); tarfile.open('docs/krishna/s08-3d-demo-evidence.tar.gz').extractall(p,filter='data')"
python -m citybrain.dashboard --events data/output/shared-s08-replay/runtime/events.jsonl --scenario 'DEMO S08 3D' --port 8778 --replay
```

Use Python 3.12+ for this safe archive extraction command. Open http://127.0.0.1:8778/3d. Seek 301 → 311 → 316 → 425: P0 → P1 → P2 → SUCCESS, travel 124 seconds. Replay is explicitly labelled saved evidence. Original provenance inside the summary retains source machine paths; those paths are evidence, not dependencies.

## Tests and research

```sh
python -m pip install pytest
python -m pytest -q
```

See [package index](README.md), [3D controls and limitations](3D_DEMO.md), [paced demo details](DEMO_MODE.md), [tables](RESULT_TABLES.md), [figures](METRICS_AND_FIGURES.md), [slides and viva](SLIDES_AND_DEMO.md). Analysis regeneration additionally needs experiments/requirements-analysis.txt and the original raw historical datasets; normal demo/replay does not.

Signals are observed SUMO programs, with advisory CityBrain recommendations. Hospital availability is synthetic. The viewer has no control endpoint. The saved demo is integration evidence, not another official trial; the official 180 trials are unchanged.

## Sharing checkpoint — 2026-10-15

Validation before publication: full pytest **262 passed**, all **10 legacy scripts passed**, Python and JavaScript syntax passed, bundled Three.js hashes matched. All **2,172 historical files** matched archived hashes and sizes. The shared demo contains 748 events, zero telemetry failures, P0/P1/P2 at 301/311/316 and SUCCESS at 425 seconds. The archive is a preserved completed run; official experiments were not regenerated.
