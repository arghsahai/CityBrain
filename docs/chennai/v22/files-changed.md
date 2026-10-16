# V2.2 complete changed-file inventory

Every changed or untracked repository file reviewed before the local commits. No credentials, dependency changes, network edits or frozen research artifacts are included. Screenshots are synthetic replay verification; no provider downloads are included.

| File | Classification | Purpose |
|---|---|---|
| `citybrain/chennai/run.py` | OTHER | Advisory CLI selection and cached telemetry integration, isolated lifecycle |
| `citybrain/chennai/server.py` | DASHBOARD | Replay-safe source labels and aging kept-open genuine observations |
| `citybrain/chennai/traffic/__init__.py` | PROVIDER | Public advisory provider exports |
| `citybrain/chennai/traffic/freshness.py` | PROVIDER | Configurable source-time freshness and clock-skew classification |
| `citybrain/chennai/traffic/here_provider.py` | PROVIDER | HERE flow and optional incidents adapter |
| `citybrain/chennai/traffic/matching.py` | ROAD MATCHING | Spatially indexed directed geometry matching and ambiguity rejection |
| `citybrain/chennai/traffic/models.py` | PROVIDER | Validated SI/WGS84/UTC normalized observation schema |
| `citybrain/chennai/traffic/normalization.py` | PROVIDER | Documented HERE/TomTom field and unit normalization |
| `citybrain/chennai/traffic/provider.py` | PROVIDER | Authorization gate, bounded/redacted HTTP, retry contracts |
| `citybrain/chennai/traffic/replay_provider.py` | PROVIDER | Bounded chronological provenance-aware offline replay |
| `citybrain/chennai/traffic/service.py` | TRAFFIC SERVICE | Non-overlapping background fetcher, bounded cache and immediate stop |
| `citybrain/chennai/traffic/tomtom_provider.py` | PROVIDER | Single-point TomTom flow adapter; conservative unknown time/direction |
| `citybrain/chennai/traffic_providers.py` | PROVIDER | Re-export new live adapters; preserve legacy fixture compatibility |
| `dashboard/cesium/app.js` | DASHBOARD | Separate flow/incident overlays and road measurement comparison |
| `dashboard/cesium/index.html` | DASHBOARD | Traffic panel, source legend and V2.2 label |
| `dashboard/cesium/styles.css` | DASHBOARD | Traffic panel and legend styling |
| `docs/CHENNAI_DEMO.md` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/CHENNAI_DIGITAL_TWIN.md` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/CHENNAI_LIVE_TRAFFIC.md` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/CHENNAI_V22_REPORT.md` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/baseline-smoke-validation.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser-final/browser-check.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser-final/desktop.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser-final/fallback.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser-final/keep.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser-final/tablet.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser-final/traffic.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser/browser-check.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser/desktop.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser/fallback.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser/keep.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser/tablet.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/browser/traffic.png` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/compatibility.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/files-changed.md` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/final-replay-summary.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/final-replay-validation.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/provider-status.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/pytest.txt` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/replay-replans.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/replay-smoke-validation.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/smoke-comparison.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/stability-gate.json` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `docs/chennai/v22/stability-gate.md` | DOCUMENTATION | Verification evidence, screenshots, setup/progress or final report |
| `simulation/chennai/scenarios/traffic-sample-v22.json` | PROVIDER | Three clearly synthetic observations on real Chennai geometry |
| `tests/test_chennai_traffic.py` | TEST | 60 mocked/offline provider, matching, lifecycle, isolation and labeling cases |
| `tools/check_chennai_browser.py` | TEST | Browser checks for geometry, overlays, provenance and unknown/expired time |
