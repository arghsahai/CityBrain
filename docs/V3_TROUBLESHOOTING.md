# CityBrain V3.0 troubleshooting

| Symptom | Check |
|---|---|
| `sumo` or TraCI cannot start | Install SUMO 1.27.1, confirm `sumo` is on PATH / `SUMO_HOME`, and install `requirements-chennai.txt` in `venv`. |
| Dashboard does not open | Visit the printed localhost URL. Use a free port with `--port`; local loopback only. |
| Cesium is blank | Confirm the local vendor bundle is present and WebGL is enabled. The SVG fallback should remain available. |
| Map imagery is absent | Base OSM geometry is local. Optional raster tiles need internet and are not required for the demo. |
| Traffic says NOT CONFIGURED / CONFIGURED NOT VERIFIED | This is expected without an explicitly authorized live provider check. Use synthetic replay; do not infer traffic coverage. |
| Traffic has no road match | Inspect freshness, direction, confidence, coverage and match reason. Unmatched evidence is intentionally not assigned to a SUMO road. |
| Browser location denied | Use the browser permission controls, secure localhost origin, and press Share again. The feature is optional. |
| Browser location stale or rejected | Keep permission active; use a test device with accurate fixes. Stop clears the local marker. No fix affects SUMO or routing. |
| Simulation ends in TIMEOUT / NO_ROUTE | Retain the output and inspect `runtime/summary.json`, `runtime/events.jsonl`, `health.json` and SUMO error log. Do not overwrite historical evidence. |
| Unexpected process remains | Send Ctrl-C to the owning launcher. It closes the local server and TraCI connection and records terminal state. |

Keep all credentials out of logs and evidence. Provider checks are opt-in and can
incur charges. Do not troubleshoot by polling repeatedly.
