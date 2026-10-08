# Four slides and speaking scripts

## Slide 1 — SUMO Digital Twin

- Synthetic, closed-loop SUMO environment
- 9-junction regression / 12-junction S08 network
- Live TraCI observations and physical route application
- Ambulance transport to configured hospital H1

**Visual:** NETWORK.md's grid, with S08 extension distinguished by colour; SUMO GUI beside read-only dashboard.

**Say:** “My primary contribution is the simulation and experimental environment. SUMO models vehicle movement and traffic interaction; TraCI couples observations to CityBrain and applies the resulting routes. This is a simulation-based digital twin, not a live model of Chennai. The extra S08 row gives a controlled bypass for successive disruptions.”

## Slide 2 — Experimental Methodology

- 120 S05/S07 trials + 60 official S08 V2 trials
- Three demand profiles; ten seeds; static/dynamic pairs
- Matched input files and recorded provenance
- Failures retained; teleport never treated as arrival

**Visual:** Table 1 trial-count audit and a static/dynamic matched-pair diagram.

**Say:** “The inventory contains 180 distinct official trials and 90 matched pairs. Static and dynamic receive the same scenario, demand and seed. I verified generated route inputs and checkpoint agreement. I report success on every trial, and travel time only for valid arrivals; these are two separate research studies rather than a pooled superiority claim.”

## Slide 3 — Static vs Dynamic Results

- S05: dynamic 30/30 successes; static 12/30
- S07: means 53.0/78.6/85.1 s static versus 34.0 s dynamic
- S08: dynamic 30/30 successes; static 30/30 teleports
- Conclusions bounded to tested synthetic conditions

**Visual:** Figure 1 success plus Figure 3 S07 profile comparison; use Figure 2 as backup.

**Say:** “Different scenarios answer different questions. S05 mainly improves reliability; jointly successful routes take the same time. S07 shows a travel-time difference with all pairs successful. S08 shows reliability and repeated replanning, but there is no successful static timing baseline. Ten seeds per cell do not establish real-world reliability.”

## Slide 4 — S08: Continuous P0 → P1 → P2 Replanning

- Observe changing road costs and candidate scores
- Verify physical route before accepting each revision
- Integrated smoke: P0 301 → P1 311 → P2 316 s
- Hospital SUCCESS 425 s; research study kept separate

**Visual:** Figure 5 timeline; Figure 4 research-frequency distribution as backup.

**Say:** “This is the integrated demonstration, not a row added to the research study. The first accepted route is reassessed as costs change, and the later proposal is evaluated relative to P1. The final bypass is topology-discovered, physically verified, then accepted as P2. In the historical study, twenty of thirty dynamic trials had two changes; it is not mandatory in every run.”

## Exact final-runtime + dashboard commands

From the repository root, with the existing SUMO-enabled `venv`. Use a fresh output directory each time. Run the viewer first in terminal A:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m citybrain.dashboard --events data/output/integration/faculty-s08/S08/runtime/events.jsonl --scenario S08
```

Open `http://127.0.0.1:8765` in the browser. Terminal B, headless verification using the unchanged runner:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m citybrain.integration.smoke --scenarios S08 --candidate-source legacy-catalog --output data/output/integration/faculty-s08
```

For SUMO GUI instead of headless, use a fresh output directory and point the viewer to it. The existing sumolib.checkBinary reads SUMO_BINARY; no runtime patch is required:

```sh
SUMO_BINARY="$(command -v sumo-gui)" PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m citybrain.integration.smoke --scenarios S08 --candidate-source legacy-catalog --output data/output/integration/faculty-s08-gui
```

Viewer command for that GUI run:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m citybrain.dashboard --events data/output/integration/faculty-s08-gui/S08/runtime/events.jsonl --scenario S08
```

The GUI may open paused: press Play in SUMO. Use its wall-clock delay control to make the explanation visible; do not alter simulation step length, seed, demand or policy. Pause for narration if useful. Stop one viewer before reusing port 8765, or use `--port 8766`. Runtime options stay at their documented defaults. Signal lights are ordinary SUMO signals, not a CityBrain-controlled green corridor.

**S05 backup:** replace S08 with S05 and use `faculty-s05` and `S05/runtime/events.jsonl`; preserve `--candidate-source legacy-catalog`. **S06 boundary:** use S06 and a fresh directory; explain NO_ROUTE, not failure of the demo. The dashboard's `--scenario` is only a display label; the smoke's `--scenarios` selects the actual input.

**Replay backup (clearly labelled):**

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m citybrain.dashboard --events data/output/integration/exception-safety-hotfix-smokes/S08/runtime/events.jsonl --scenario S08 --replay
```

Use the time slider to inspect 301, 311, 316 and 425 seconds. Replay is saved evidence, not a live simulator. The console and dashboard will not claim a live TraCI connection.

**Existing historical professor demo:**

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m experiments.runners.demo --gui --scenario S08 --seed 1 --output data/output/integration/historical-professor-s08
```

This existing command runs the historical experiment loop (explicit bypass and ETA-based gate), not the final runtime, and writes `events.json` rather than dashboard-compatible JSONL. Do not attach the new viewer to it or promise the integrated P2 time of 316. Explicit output avoids adding to official experiment directories.

## 90-second S08 script

**Startup, ~15 seconds:** “I built and validated the SUMO environment and experiments. The left window shows physical traffic; the right reads CityBrain's evidence. It cannot send commands to the planner. This is a synthetic digital twin, not a live city feed.”

**P0, ~15 seconds:** “At observed dispatch, P0 is chosen from current conditions. Watch the route-execution verification before plan acceptance. H1 at J9 is the configured destination. The initial ETA is an estimate, not the final measured journey.”

**P1, ~20 seconds:** “Road conditions now deteriorate and the candidate scores change. The decision records its reason and stability gates. In this configuration, P1 is accepted around 311 seconds only after SUMO's actual remaining route matches the proposal. Congestion can justify a change before an edge is fully stopped.”

**P2, ~20 seconds:** “A later change affects the accepted route. CityBrain evaluates relative to P1, discovers a valid topology alternative and verifies it before P2 acceptance, around 316 seconds. These are actual records, not scripted animations.”

**Arrival, ~20 seconds:** “The expected smoke reaches H1 around 425 seconds, with 124 seconds from dispatch. SUCCESS requires arrival evidence and correct destination; teleport would be a terminal failure. This smoke proves integration, while the separate 60-trial S08 study tests variability across ten seeds and three demand profiles.”

## 45-second S08 script

“SUMO shows physical traffic, while this independent read-only dashboard shows CityBrain's recorded reasoning. The ambulance receives P0 at dispatch. When road costs change, the planner proposes P1; SUMO applies and verifies it before acceptance. A later change prompts P2 relative to P1, using a topology-discovered bypass. This integrated configuration typically accepts revisions around 301, 311 and 316 seconds and reaches H1 around 425. Teleport or disappearance would not count as success. My separate research evaluation used matched static/dynamic runs across ten seeds and three profiles, so I distinguish this live integration demonstration from the statistical results.”

## S05 backup speaking cue

“Here we need one justified change rather than two. At the observed P1 decision, E7 is highly congested but not yet flagged fully blocked. The alternative is sufficiently better after commitment, and hospital arrival is verified. If no second change is needed, KEEP is correct; additional replans are not a presentation objective.”

## Presentation-day checklist

1. Start Terminal 1's viewer first, using the GUI-run viewer command above. It waits for the file.
2. Open http://127.0.0.1:8765, then start Terminal 2's S08 SUMO GUI command above.
3. Arrange SUMO on the left and the dashboard on the right. Press SUMO Play if paused.
4. Primary: explain P0 → P1 → P2 → SUCCESS, separating last planner decision KEEP from terminal SUCCESS.
5. Backup: stop the viewer with Ctrl-C and use the S05 commands below, or clearly labelled S08 replay.
6. Stop each process with Ctrl-C in its own terminal. A stopped/crashed viewer leaves CityBrain running.

S05 backup, Terminal 1:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m citybrain.dashboard --events data/output/integration/faculty-s05-gui/S05/runtime/events.jsonl --scenario S05
```

S05 backup, Terminal 2:

```sh
SUMO_BINARY="$(command -v sumo-gui)" PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m citybrain.integration.smoke --scenarios S05 --candidate-source legacy-catalog --output data/output/integration/faculty-s05-gui
```

Use an unused output directory for each new demonstration and update both commands together.
