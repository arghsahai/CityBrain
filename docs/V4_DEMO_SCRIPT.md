# V4 demonstrations — keep data sources separate

Experimental research prototype. No real incident, dispatch, ambulance GPS, clinical admission or production-readiness claim. Genuine Tamil Nadu emergencies: 108 ([official Chennai District helpline](https://chennai.nic.in/helpline/)).

1. **Preserved SIMULATION.** `./tools/run_chennai.sh --mode simulation --seed 17`. Default viewer <http://127.0.0.1:8770>. Moving vehicles/ambulance, accepted plan, hospital road and changing signal telemetry are SIMULATED. Normal seed-17 response reaches SUCCESS at 704 s, not evidence of an applied replan. Use the preserved saved S08 demonstration for physical replan/read-back evidence (README Demo B), not this V4 recommendation path.
2. **Start LIVE DATA prototype.** Follow [setup](V4_LIVE_DATA_SETUP.md) in a separate terminal with fresh disposable DB and separate role credentials. Open <http://127.0.0.1:8784/?fallback=1> for offline 2D, or `/` for Cesium if WebGL works. Provider connection must say UNAVAILABLE. Default mode links require both viewers to be running.
3. **Public test incident.** Click Report Accident, select a pilot map point or enter longitude `80.1356635`, latitude `12.8605092`. Confirm TEST and submit. Optional one-time device location requires explicit button click; do not share a real person’s location for this demo. The selected point must be inside the pilot. Report is PENDING_VERIFICATION, no service contacted.
4. **Operator.** Sign in with the test operator token. Verify for testing. Rejection/deletion are available for disposable test reports. Public mode cannot view the queue or route.
5. **Dynamic start and recommendation.** Click Place test ambulance and a pilot road, or enter longitude `80.17076485`, latitude `12.82895182` then Use current coordinates as ambulance start. If ambiguous, choose intended directed road from the returned candidates. Select the verified incident and first journey leg; Assess route. Direction ambiguity at the incident also requires an explicit edge choice. Expect PENDING_OPERATOR_REVIEW, USER_SELECTED and ESTIMATE — NOT FIELD VALIDATED. Cyan partial-edge route begins/ends at snapped points. No ETA implies arrival.
6. **Offline reassessment.** Operator test panel chooses a route edge and a clearly SYNTHETIC condition. A matched/covered fresh closure on a usable alternative forces a new recommendation; reopening removes its active closure marker. A small soft improvement is kept during the separate 60-second cooldown / minimum 30-second and 10% improvement gate. Unsupported/ambiguous observations remain visible but cannot become road costs. “Future” quarantines invalid clocks; “Slow flow” recovers with valid time. “Outage” is an offline failure test, not an actual provider outage.
7. **Hospital portal.** Sign out; sign in with the independent facility token. Update its accepting/ICU/trauma/bed fields using test values, explicitly STAFF_REPORTED. Sign out and return to operator. Place the test ambulance at the incident road and explicitly confirm incident arrival before requesting the second leg; unknown, expired, unsuitable or unreachable facilities cannot win; reported beds must be a positive integer, not unknown or zero. Clinical services/driveways are unverified. Status expires after 15 minutes; transport choice belongs to emergency personnel.
8. **SUMO priority.** NOT_AVAILABLE — safety gate failed. Show [the signal inventory](V4_SIGNAL_PRIORITY_VALIDATION.md), not a fabricated intervention or performance comparison.
9. **Genuine provider.** NOT_AVAILABLE — no provider request is authorized or verified. Show readiness, offline fixtures and [provider evaluation](V4_TRAFFIC_PROVIDER_COMPARISON.md), not a fake LIVE demonstration.

## Repeatable scripted offline demo

In another terminal, use the same `CITYBRAIN_OPERATOR_TOKEN` value as the local server; never include it in command-line arguments or logs. Use a fresh empty demo DB for seed (nearby duplicates are deliberately rejected). This client is restricted to loopback HTTP and makes no provider requests.

```sh
venv/bin/python -m citybrain.live.demo --scenario seed
# The output prints demo_edge; for the retained graph it is -828326390#4.
venv/bin/python -m citybrain.live.demo --scenario closure --edge=-828326390#4
venv/bin/python -m citybrain.live.demo --scenario reopen --edge=-828326390#4
venv/bin/python -m citybrain.live.demo --scenario closure --edge=-828326390#4
venv/bin/python -m citybrain.live.demo --scenario future --edge=-828326390#4
venv/bin/python -m citybrain.live.demo --scenario recover --edge=-828326390#4
venv/bin/python -m citybrain.live.demo --scenario outage
```

The UI polls every five seconds. Active test closures should read 1 → 0 → 1; future quarantine preserves the last valid measurement. This deterministic fixture sequence is a synthetic software test, not real Chennai traffic. The default test pin may ask a direction choice in the manual UI; the scripted fixture explicitly selects retained directed IDs.

## Validation commands

```sh
venv/bin/python -m pytest -q
venv/bin/python -m pytest -q tests/test_live_graph.py tests/test_live_service.py tests/test_live_http.py tests/test_live_traffic.py tests/test_live_boundaries.py
venv/bin/python -m citybrain.live.signal_audit
./tools/run_chennai.sh --mode simulation --seed 17 --seconds-per-step 0 --no-server --no-browser --exit-on-complete --output /tmp/citybrain-v4-new-sim-UNUSED
venv/bin/python -m citybrain.chennai.validate --run /tmp/citybrain-v4-new-sim-UNUSED --historical
./tools/run_chennai.sh --mode replay-assisted --experimental-traffic-evaluation --seed 17 --seconds-per-step 0 --no-server --no-browser --exit-on-complete --output /tmp/citybrain-v4-new-replay-UNUSED
venv/bin/python -m citybrain.chennai.validate --run /tmp/citybrain-v4-new-replay-UNUSED
```

Use genuinely unused output paths. Do not regenerate the official experiments. Ctrl-C stops only the viewer/launcher you started. Offline fallback requires neither Internet imagery nor WebGL. Cesium 3D needs a functioning WebGL context; it failed initialization in this task environment and is not claimed browser-verified.
