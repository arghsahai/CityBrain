# CityBrain 3D DEMO

The 3D scene is a local Three.js/WebGL2 visualization of SUMO observations. SUMO remains the traffic simulator. The browser never connects to TraCI, commands vehicles or changes signals. The original team runtime, planner and official networks/demand remain unchanged.

The installed macOS SUMO GUI 1.27.1 build lists no OpenSceneGraph feature. SUMO's native 3D rendering requires an OpenSceneGraph-enabled build (https://eclipse.dev/sumo/docs/sumo-gui.html). Using the browser avoids rebuilding SUMO/XQuartz or migrating validated algorithms to a new simulator.

## What is actual and what is illustrative

- Roads use the existing SUMO lane shapes in network coordinates; accepted routes use their recorded edge IDs.
- Vehicle IDs, types, position, speed and heading are observed through the existing connected TraCI client, in the optional snapshot emitter only.
- Signal bulbs display every observed SUMO link state. The row of bulbs is a presentation of controlled-link indices, not a survey of physical pole locations; junctions can have simultaneous red/green links. No CityBrain signal execution is claimed.
- Hospital H1 corresponds to J9. Its building model, nearby city buildings and vehicle bodies are illustrative. H1 availability is synthetic configuration; no hospital service is queried.
- Sizes, labels and camera views prioritize legibility, not photorealism. Cars use simple reusable 3D meshes.
- Movement interpolates between consecutive observed positions for smoother display, without extrapolation or invented traffic. Seeking a nonconsecutive replay step snaps to that observation. A stale source holds the last position and shows a warning. Observations update once per simulation second; the viewer polls twice per wall second.
- Existing saved demo files without heading still render using displacement heading; accepted-route highlighting requires the new `road_edges` metadata and is absent if that metadata was not recorded. Old official evidence lacking demo observations shows a clear unavailable message.

## Launch live 3D

From the feature branch checkout, use the existing Python environment and SUMO installation. Choose a fresh output directory outside experiments/results.

```sh
python -m citybrain.demo --headless --output /absolute/fresh/demo-3d
```

In a second terminal:

```sh
python -m citybrain.dashboard --events /absolute/fresh/demo-3d/runtime/events.jsonl --scenario 'DEMO S08 3D' --port 8778
```

Open http://127.0.0.1:8778/3d. Headless here only removes SUMO's separate 2D window: the SUMO simulation and CityBrain runtime execute normally and feed the browser. To see both SUMO GUI and browser 3D, omit `--headless`. The existing default pacing preserves ~4m23s of watchable emergency playback after the rapid warmup.

## Replay

```sh
python -m citybrain.dashboard --events /absolute/completed/demo-3d/runtime/events.jsonl --scenario 'DEMO S08 3D' --port 8777 --replay
```

Open http://127.0.0.1:8777/3d. Replay is prominently labeled. Seek to 301 for P0, 311 for P1, 316 for P2, 425 for SUCCESS. Playback uses 1.8 wall seconds per recorded simulation second. The 2D dashboard is available at `/` on the same server.

Camera controls: drag to orbit, scroll/pinch to zoom, City overview to reset, Top view for routes, Hospital view for H1 and the destination approach, Follow ambulance to track the observed vehicle. Follow waits when the ambulance is absent and holds its last view after arrival. Hide details gives more room on a narrow screen; Show details restores metrics and replay controls.

The viewer requires browser WebGL2 support. If initialization fails it reports the limitation and the ordinary dashboard link remains available. Dependency three@0.180.0 is pinned and bundled locally with its MIT license; no internet access is needed for playback.

## Ownership and evidence

Krishna's demo visualization only. Added telemetry reads are optional and failure-contained. Core control modules, teammate algorithms, official trials and frozen output artifacts are unchanged. New 3D evidence is generated outside official results.
