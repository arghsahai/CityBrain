# CityBrain V3.0 demonstration script

## Full local SUMO demonstration

From the repository root, start the supported runtime:

```sh
./tools/run_chennai.sh --mode simulation
```

The browser opens at `http://127.0.0.1:8770`. Explain the status in this order:

1. OSM provides the road geometry; SUMO creates the vehicles, emergency vehicle,
   signal programs, disruptions and hospital availability.
2. Watch the ambulance's observed SUMO position, accepted route and hospital
   destination. Route acceptance follows physical route application and read-back.
3. Signal states are observed simulated states. Recommendations remain advisory;
   no priority phase is applied.
4. External traffic is either unavailable or explicitly labeled synthetic/replay.
   It remains advisory; route planning does not read it.
5. The optional device location panel asks for browser permission only after the
   user presses Share. Demonstrate it with a test device or automation fixture;
   press Stop to clear the local marker.
6. Explain terminal outcome and limitations: arrival means the ambulance reached
   a configured hospital access road, not that a patient was admitted.

Use `Ctrl-C` to stop and clean up. For an unattended headless smoke, use a fresh
`/tmp` output directory and `--exit-on-complete`; see [V3_SETUP.md](V3_SETUP.md).

## Saved replay demonstration

```sh
./tools/run_chennai.sh --mode replay --events data/output/chennai/v22-final-replay \
  --port 8773 --no-browser
```

Open `http://127.0.0.1:8773`. Replay is read-only and cannot control the simulator.
Use the timeline and playback controls to inspect movement and accepted plans.
The traffic panel must say `REPLAY` or `SYNTHETIC_SAMPLE`; it is not live.

## 2D fallback demonstration

In the viewer, select **2D / 3D** when WebGL is available. If Cesium fails to
initialize, the local SVG fallback activates automatically and retains roads,
vehicles, route, hospital and advisory overlays. Use the toggle to return to 3D
when available. The map does not require external imagery; the optional OSM tile
button is a separate internet request.
