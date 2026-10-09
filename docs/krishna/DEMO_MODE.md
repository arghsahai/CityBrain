# CityBrain DEMO mode

Optional Krishna presentation layer on `feature/krishna-watchable-demo`, based on dashboard HEAD `4bf0f48`. Remote main was checked and remains `fe471a8`. Core/runtime/planner, team modules, official scenario sources and official results are unchanged.

The runtime uses one TraCI connection. `citybrain.demo` calls the existing runtime step/dispatch interfaces and reads SUMO vehicle positions, speeds, signal phase, link states and next-switch times. Snapshot collection/writes are caught at a separate presentation boundary. No signal setter is called. Hospital H1 at J9 and ICU availability are synthetic configuration, not external hospital data. The normal SUMO signal programs change automatically; some junction programs remain all-green by design.

Normal cars, demand, seed 1, one-second simulation steps, emergency departure and all decision settings remain frozen. The ambulance's color/GUI shape and hospital POI affect drawing only. No physical speed, vehicle dimensions, emergency bypass, signal timing or route changes are introduced by presentation settings.

Simulation 0–279 runs quickly as traffic warmup. At 280 seconds, default pacing becomes 1.8 wall seconds per one simulation second. Through SUCCESS at 425 this gives 262.8 seconds (~4m23s) of watchable playback, plus startup/warmup overhead. Planner commitment, cooldown, ETA and decisions use simulation time. Pacing happens after each completed runtime step and observation, outside decision algorithms. On an unusually slow machine playback can take longer. Use 0 only for verification.

## Launch

From the checkout root, use a Python environment with the repository requirements and installed SUMO. Set `SUMO_HOME` to the installed SUMO location if needed. Each run must use a fresh output path, outside `experiments/results`.

Terminal 1:

```sh
python -m citybrain.demo --output /absolute/fresh/path/demo-run
```

Terminal 2 (may start before Terminal 1):

```sh
python -m citybrain.dashboard --events /absolute/fresh/path/demo-run/runtime/events.jsonl --scenario 'DEMO S08' --port 8775
```

Open http://127.0.0.1:8775 alongside SUMO GUI. The viewer fetches observations every 500 ms. Signal strings describe individual controlled links; a junction can have red and green links simultaneously. The map shows those colors present rather than implying one color applies to every approach. The full actual link string remains in the signal table. Before the ambulance departs at 300 s, the dashboard correctly shows no ambulance. After arrival the ambulance is absent; SUCCESS comes from runtime arrival evidence.

Replay the same saved simulation observations, including signals and vehicles:

```sh
python -m citybrain.dashboard --events /absolute/demo-run/runtime/events.jsonl --scenario 'DEMO S08' --port 8776 --replay
```

Headless verification:

```sh
python -m citybrain.demo --headless --seconds-per-step 0 --output /absolute/fresh/path/demo-check
```

The dashboard remains GET-only with no runtime command path. Optional observation failure can stop snapshot updates but cannot change logical acceptance or route execution. Existing runtime evidence handling is unchanged. A stale display is not proof of a healthy TraCI connection. The demo-health file records observation failures after completion.

## Ownership and limits

Krishna owns this demo launcher, optional presentation telemetry and dashboard extension. Existing teammate planner, core, perception and signal recommendations remain unchanged. This is software-only simulated data. No real hospital, city sensing or signal-control service is connected. One configured hospital is shown; extra hospital destinations are not invented.

Validation: 262 pytest tests; frozen S08 accepted plans/outcome/arrival/travel/replan metrics match exactly; all 425 optional observation calls forced to fail without changing the outcome; original historical artifacts 2172/2172 with identical hashes and sizes. Actual paced SUMO GUI execution was exercised with the dashboard. Native XQuartz accessibility timed out, so direct visual inspection of the SUMO window is a remaining limitation. Browser map was visually inspected.
