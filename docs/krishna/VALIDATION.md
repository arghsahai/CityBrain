# Final validation — 2026-10-08

Frozen baseline: `fe471a863858489229c6bb956498405c77a2558e`. Branch: `feature/krishna-live-dashboard`.
No pre-existing tracked file differs from the baseline. Local main remains
`e660ecd6abbf5fff391c4e09d51f645198df18ae`. No push or merge is authorized.

## Checks

- Fresh full pytest: **259 passed in 3.90 s**, including seven viewer tests.
- All ten root-level legacy `test_*.py` scripts: PASS individually.
- AST parse of all added Python modules/tests/builder: PASS. Dashboard imports exercised by pytest.
- `node --check citybrain/dashboard/app.js`: PASS.
- Saved final browser log: all S05/S06/S08 checks pass, zero console errors.
- S08 replay: P0 at 301, P1 at 311, P2 at 316, terminal SUCCESS at 425.
- Desktop/tablet screenshots inspected; timeline and plan history readable. TraCI health explicitly UNKNOWN.
- Saved live isolation test observed P0 at 303, forcibly killed viewer while runtime active, then completed normally.
- Freshly compared saved S05/S06/S08 summaries with frozen hotfix summaries: accepted plans, outcomes, arrival/travel, route changes and latencies match exactly.
- S05 SUCCESS at 335, travel 34; S06 NO_ROUTE at 316, no arrival; S08 SUCCESS at 425, travel 124.
- Saved actual sumo-gui S08 run: SUCCESS at 425, travel 124, two replans. This is process/telemetry validation, not visual inspection of the SUMO window.
- No official experiment trials rerun; prior simulations reused.

Command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/citybrain-readiness-pytest-deps venv/bin/python -m pytest -q -p no:cacheprovider`. The temporary path supplies the existing local pytest installation; other environments need pytest installed.

## Historical integrity

Existing pre-change SHA-256/size manifest checked against every file under experiments/results:
expected **2,172**, actual **2,172**, missing **0**, extra **0**, hash mismatches **0**, size mismatches **0**.
Manifest is also preserved inside docs/final-integration-evidence.tar.gz at verification/historical-hashes.json.
AUDIT.json records 120+60 unique official trials, 90 matched route-input pairs, 90 matched config pairs and 50 audited S08 applications.
Historical controlled S08 and final integrated demonstration remain separate.

## Evidence locations and limits

Browser: `/tmp/citybrain-dashboard-browser-final.log`. Isolation: `/tmp/citybrain-dashboard-isolation.py` and `/tmp/citybrain-dashboard-isolation.log`. GUI: `/tmp/citybrain-dashboard-gui.log`.
Saved runtime outputs: `data/output/integration/dashboard-isolation-smokes/` and `data/output/integration/dashboard-gui-smoke/`.
These local ignored outputs and temporary logs are not portable committed artifacts. The package builder requires the saved raw evidence locally; it does not download or regenerate trials.
Viewer failure has no logical path into runtime: separate process, file reader, no TraCI/planner imports, no control endpoint. Shared host resource exhaustion is not a fault-containment guarantee. Signals remain advisory; file freshness cannot prove TraCI connectivity.

## Pre-commit review

`git diff --stat fe471a8...HEAD` and tracked working-tree diff were empty before staging: all work consists of the additions below. No correctness-critical or historical file changed.

| Added file | Classification | Reason |
|---|---|---|
| `citybrain/dashboard/__init__.py` | DASHBOARD | Defines the isolated viewer package. |
| `citybrain/dashboard/__main__.py` | DASHBOARD | Provides the dashboard CLI. |
| `citybrain/dashboard/app.js` | DASHBOARD | Renders recorded state and replay controls. |
| `citybrain/dashboard/index.html` | DASHBOARD | Defines dashboard panels. |
| `citybrain/dashboard/server.py` | DASHBOARD | Reads JSONL and serves GET-only snapshots. |
| `citybrain/dashboard/style.css` | DASHBOARD | Styles responsive presentation layout. |
| `docs/krishna/AUDIT.json` | RESEARCH DOCUMENTATION | Records trial counts, pairing and source hashes. |
| `docs/krishna/CONTRIBUTION_MAP.md` | RESEARCH DOCUMENTATION | Attributes contributions to actual Git history. |
| `docs/krishna/DASHBOARD.md` | RESEARCH DOCUMENTATION | Documents architecture, operation and limitations. |
| `docs/krishna/METRICS_AND_FIGURES.md` | RESEARCH DOCUMENTATION | Defines metrics and figure sources. |
| `docs/krishna/NETWORK.md` | RESEARCH DOCUMENTATION | Inventories network, routes and signals. |
| `docs/krishna/README.md` | RESEARCH DOCUMENTATION | Indexes the complete contribution package. |
| `docs/krishna/REPORT_SECTION.md` | RESEARCH DOCUMENTATION | Provides academic report prose. |
| `docs/krishna/RESEARCH_PACKAGE.md` | RESEARCH DOCUMENTATION | Explains scenarios, findings and bounded claims. |
| `docs/krishna/RESULT_TABLES.md` | FIGURE/TABLE | Contains six evidence-derived result tables. |
| `docs/krishna/SLIDES_AND_DEMO.md` | RESEARCH DOCUMENTATION | Provides slides, scripts and exact demo commands. |
| `docs/krishna/VALIDATION.md` | RESEARCH DOCUMENTATION | Records final checks and every added file. |
| `docs/krishna/VIVA_BANK.md` | RESEARCH DOCUMENTATION | Provides 40 questions with short and deeper answers. |
| `docs/krishna/dashboard-preview.png` | FIGURE/TABLE | Shows verified dashboard presentation. |
| `docs/krishna/figures/01_success.png` | FIGURE/TABLE | Compares success rates. |
| `docs/krishna/figures/02_travel.png` | FIGURE/TABLE | Shows successful travel times. |
| `docs/krishna/figures/03_profiles.png` | FIGURE/TABLE | Compares S07 demand profiles. |
| `docs/krishna/figures/04_replans.png` | FIGURE/TABLE | Shows historical S08 replan frequencies. |
| `docs/krishna/figures/05_timeline.png` | FIGURE/TABLE | Shows the separate integrated S08 timeline. |
| `tests/test_dashboard.py` | TEST | Tests reader, replay, real scenarios and isolation. |
| `tools/build_krishna_package.py` | OTHER | Reproduces derived analysis from saved evidence only. |
