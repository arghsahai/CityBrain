# CityBrain V3.0 prototype setup

## Local prerequisites

- Python and the repository `venv` dependencies in `requirements-chennai.txt`.
- Eclipse SUMO 1.27.1 and its Python bindings on PATH / `SUMO_HOME`.
- Chrome with WebGL for the 3D browser checks; the local SVG map remains a fallback.

From the repository root, run `venv/bin/python -m pytest -q` for the software
suite and `./tools/run_chennai.sh --help` for launcher options. The supported
local Chennai launch is:

```sh
./tools/run_chennai.sh --mode simulation --seconds-per-step 0.33
```

The default is SUMO simulation only. Synthetic traffic replay is:

```sh
./tools/run_chennai.sh --mode replay-assisted --seconds-per-step 0.33
```

Fast, headless, non-research smoke runs must use fresh `/tmp` destinations:

```sh
./tools/run_chennai.sh --mode simulation --seconds-per-step 0 --no-server --no-browser \
  --exit-on-complete --output /tmp/citybrain-smoke
venv/bin/python -m citybrain.chennai.validate --run /tmp/citybrain-smoke
```

Provider keys are optional and are never needed for simulation, tests or replay.
`.env.example` is a reference only; the application does not load it. Keep keys
in process environment or an approved local secret store. The safe status check
makes no network request:

```sh
venv/bin/python tools/verify_traffic_provider.py --provider here
venv/bin/python tools/verify_traffic_provider.py --provider tomtom
```

An actual provider request is potentially billable and requires a separate
authorization. Only after reviewing the account plan and obtaining that
authorization, an operator may run:

```sh
venv/bin/python tools/verify_traffic_provider.py --provider here --authorize-live-request
```

The flag causes one authenticated request. Output omits credentials and payloads.
This V3 implementation has **not** invoked that command. A successful live check
proves only the response observed in that request and area; it does not establish
city-wide coverage or routing benefit.

The launcher owns the SUMO child and local dashboard, catches interrupts and
closes its TraCI connection and server. `--exit-on-complete` is intended for
automation; without it, the browser server remains available after a completed
run until Ctrl-C. No launcher mode silently authorizes provider requests.
