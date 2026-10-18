# V4 local setup

Requirements: the existing `venv` with `requirements-chennai.txt` (including sumolib/pyproj), retained Chennai network, Python 3.13 tested. **Live-data mode does not need a SUMO process or provider credentials.** It reads the retained SUMO-format OSM network as a directed graph. SUMO binary is required only for simulation mode. Windows is not tested.

From the repository root, generate separate temporary local test credentials in the current terminal. Do not paste them into source, URLs, screenshots, PRs or committed files:

```sh
export CITYBRAIN_OPERATOR_TOKEN="$(venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export CITYBRAIN_HOSPITAL_TOKEN="$(venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export CITYBRAIN_HOSPITAL_ID=osm_7257289060
V4_DEMO_DIR="$(mktemp -d /tmp/citybrain-v4-demo.XXXXXX)"
venv/bin/python -m citybrain.live --mode live --database "$V4_DEMO_DIR/state.sqlite"
```

Open <http://127.0.0.1:8784>. Use `?fallback=1` to force offline SVG. Both map paths have pilot/Chennai overview controls; optional OSM tiles require Internet and remain display only outside the pilot. The server binds **127.0.0.1 only**, uses strict Host/Origin checks and no CORS. Without a token, public test reports work but privileged actions are disabled. Tokens must be distinct, at least 32 ASCII characters with no whitespace. A hospital token requires one configured directory ID; it cannot verify incidents or update another facility. Operator credentials cannot impersonate the hospital role. These are local test roles, not verified hospital affiliations.

Use the operator token in the dashboard's Access token field for review/routing; use the hospital token to demonstrate the facility-scoped portal. Browser tokens stay in tab memory and are cleared on logout/reload. A browser may offer password saving; decline it. Do not expose this HTTP prototype via a tunnel or public bind. Ctrl-C stops the server. No provider thread or SUMO child is created in live mode. Database default (if `--database` omitted): `~/.local/share/citybrain/v4/state.sqlite`, owner-only file permissions, 24-hour record retention enforced on activity and 1,000 incident / 100 hospital / 2,000 audit record limits.

Optional local normalized recording (V2 recording schema, maximum 2 MiB / 2,000 source records):

```sh
venv/bin/python -m citybrain.live --mode live --database "$V4_DEMO_DIR/recording.sqlite" --traffic-recording /absolute/path/to/recording.json
```

Original source timestamps are preserved. Old recordings will be STALE/EXPIRED and cannot influence route costs. No timestamp rewriting makes them live. `RECORDED_PROVIDER_DATA` is an input provenance declaration, **not independently authenticated evidence**. The interface labels it RECORDED_PROVIDER_REPLAY. Synthetic injection is disabled while a recording is selected.

Provider readiness: missing key → NOT_CONFIGURED; present key → CONFIGURED_NOT_VERIFIED. V4 never instantiates a network provider or returns LIVE_VERIFIED. Live provider activation requires a separate implementation/review and explicit provider, credential, licensing and billing authorization. Keys in the environment alone cannot enable requests.

Simulation stays on its existing path and viewer:

```sh
./tools/run_chennai.sh --mode simulation --seed 17
# Equivalent explicit mode entry point:
venv/bin/python -m citybrain.live --mode simulation --seed 17
```

The dashboard mode links target the default local ports: simulation 8770, V4 live 8784. A link opens the other viewer; it does not start its process. Run both services separately to switch between them. Custom ports require opening the printed URL directly.
