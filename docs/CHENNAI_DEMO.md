# Run the Chennai demonstration

V2.2 advisory traffic support is now implemented. See
[CHENNAI_LIVE_TRAFFIC.md](CHENNAI_LIVE_TRAFFIC.md) for offline replay, optional
HERE/TomTom setup, source labels and limitations. Existing SUMO/planner behavior
and the Chennai 20-second guard remain authoritative. Real traffic coverage is
unverified; credentials and explicit request authorization are required.

Prerequisites: Python 3.12+ recommended, SUMO 1.27.1 on `PATH`, a WebGL-capable
browser. The local 2D fallback works without WebGL. This repository already has a
`venv`; on a fresh checkout:

```sh
python3 -m venv venv
venv/bin/python -m pip install -r requirements-chennai.txt
```

One command starts SUMO, the existing CityBrain runtime, telemetry and the browser:

```sh
./tools/run_chennai.sh
```

The Chennai runtime now confirms soft route-change recommendations for 20 simulation
seconds. Confirmed hard blockages retain immediate handling. Configure the window
with `--confirmation-seconds 20` and the seed with `--seed 19`. The revision count
emerges from actual decisions: guarded seed 17 accepted P0 only; seed 19 accepted
one sustained replan. See [the stability report](CHENNAI_STABILITY_FIX.md).

Dashboard: **http://127.0.0.1:8770**. Output goes to a fresh timestamped directory
under `data/output/chennai/`. Final metrics remain visible after the simulation
finishes; Ctrl-C closes the local server. Ctrl-C during simulation records an
interrupted outcome and closes SUMO. Use `--exit-on-complete` for automation.

The default minimum pacing is **0.33 wall seconds per simulated second**. Planner
computation runs normally; pacing waits only after computation/observation. A
759-s scenario therefore targets about 250 wall seconds on a capable machine,
plus startup. A slower host can take longer. The first unpaced run took 183 s.
Simulation time, observation time and wall-clock duration are distinct values.

```sh
# Other synthetic demand profiles:
./tools/run_chennai.sh --profile HEAVY
./tools/run_chennai.sh --profile PEAK

# Fast headless simulation (still writes real telemetry and audit evidence):
./tools/run_chennai.sh --seconds-per-step 0 --no-server --no-browser \
  --output data/output/chennai/my-fresh-smoke

# Live-assisted boundary: SUMO works; external provider reports UNAVAILABLE.
# No API request is made by the current placeholder adapters.
./tools/run_chennai.sh --mode live-assisted

# Offline traffic/GPS fixtures, explicitly labeled REPLAY:
./tools/run_chennai.sh --mode replay-assisted

# Replay a completed output directory; no SUMO simulation is started:
./tools/run_chennai.sh --mode replay \
  --events data/output/chennai/smoke-01
```

Replay starts near simulation time zero; use the slider or 1×/2×/4× playback.
Pause/seek changes only the replay, not the live simulator. Live pause/control is
not implemented. Use the Study area / Follow ambulance / 2D–3D controls to inspect
the response. Optional OSM imagery requires internet; the baseline view does not.

What to explain to faculty:

1. OSM supplies real roads. Traffic demand, signals, incidents and hospital
   availability are simulated and labeled.
2. Around 40–51 s, the ambulance appears and CityBrain obtains its initial plan.
3. Watch the actual accepted-plan history, route scores and verified execution.
   Revision count varies with traffic and decisions; no P1/P2 events are scripted.
4. Roadworks lower actual SUMO speed limits when a viable diversion exists.
5. Signals display actual SUMO phases. Recommendations do not control real lights.
6. Arrival is verified at the configured hospital access-road endpoint.

Independent verification:

```sh
venv/bin/python -m pytest -q
venv/bin/python -m citybrain.chennai.validate --historical \
  --run data/output/chennai/smoke-01
```

Screenshots: `docs/chennai/desktop.png`, `fallback.png`, `tablet.png`.
Audit details, limitations and external-provider status:
[`CHENNAI_DIGITAL_TWIN.md`](CHENNAI_DIGITAL_TWIN.md).
