# CityBrain V3.1 faculty demonstration

## Main demonstration (about 6 minutes)

Before the session, install the documented SUMO/Python dependencies and run the
synthetic replay-assisted mode once to ensure the local network builds and the
Cesium viewer is available. No provider credential or external API call is
needed.

```sh
./tools/run_chennai.sh --mode replay-assisted --experimental-traffic-evaluation
```

1. **0:00–0:45 — Set the evidence boundary.** Explain that roads are based on
   OSM in the selected Chennai study area; vehicles, demand, signals, incidents
   and hospital availability are simulated. The traffic replay is synthetic,
   not live Chennai traffic.
2. **0:45–1:45 — Digital twin.** Show ordinary vehicles moving, the ambulance,
   simulated incident, hospital marker and selected road context. Read the
   source and freshness labels aloud.
3. **1:45–2:45 — CityBrain route lifecycle.** Show P0/current accepted route,
   planner decision and physical SUMO route read-back. Explain that the existing
   verified executor remains the only route-commit path and soft changes use
   the Chennai confirmation guard.
4. **2:45–3:45 — Signals and traffic.** Select a traffic light and show its
   simulated phase/link state. Recommendations are advisory; no signal is
   actuated. Open a matched traffic overlay and show its replay source, geometry
   match and freshness. Do not describe it as live.
5. **3:45–4:45 — Experimental advisor.** Open the opt-in route advisor panel.
   Explain baseline and adjusted scores, match evidence and rejection reasons.
   Its connected-route, freshness, coverage, confidence, minimum-improvement,
   commitment, cooldown and oscillation gates produce advice only; it cannot
   invoke the production planner or commit an alternative route.
6. **4:45–5:30 — Privacy and fallback.** Show the consented device marker
   controls; do not enable them unless the presenter explicitly chooses to use
   their own location. Stop clears the marker. Toggle 2D / 3D and show the SVG
   fallback. No location enters routing.
7. **5:30–6:00 — Explain limits.** A SUCCESS means reaching a configured
   simulated hospital access road. It does not verify driveway access, clinical
   capacity, actual municipal signals, live provider coverage or emergency
   response readiness.

The dashboard remains available after terminal state for review. Press `Ctrl-C`
to clean up. For a controlled fresh output, add an explicit new `--output`
directory under `/tmp`.

## Reliable fallback demonstration

If Cesium/WebGL or live simulation display is unreliable, replay a completed
local output without starting new traffic/provider activity:

```sh
./tools/run_chennai.sh --mode replay \
  --events /tmp/citybrain-v31-advisor-smoke \
  --port 8773 --no-browser
```

Open `http://127.0.0.1:8773`, select **2D / 3D** if Cesium is available, and
use the timeline to inspect vehicle movement, route, signals, replay labels and
the opt-in advisor evidence captured in that run. The replay mode is read-only.
If that temporary output is unavailable, first create a completed local run
with the main command and retain its output folder.

## Offline smoke alternative

```sh
./tools/run_chennai.sh --mode simulation --seed 17 --seconds-per-step 0 \
  --no-server --no-browser --exit-on-complete --output /tmp/citybrain-v31-smoke
venv/bin/python -m citybrain.chennai.validate --run /tmp/citybrain-v31-smoke
```

This headless command verifies the simulation but does not open a presentation
dashboard.
