# SUMO signal-priority safety review

Decision: **ADVISORY_ONLY at both retained pilot signals. No phase controller, phase intervention or comparative priority trial was implemented.** This follows the user’s explicit gate to implement actuation only where movement and clearance contracts are verified. Real signals are never controlled.

Read-only reproducible inventory:

```sh
venv/bin/python -m citybrain.live.signal_audit > /tmp/citybrain-v4-signal-audit.json
```

Source network SHA-256: `56df2c21ece2915a6c7c98c498b5f387336f73e498d7d19c30f9f280a6212433`. Inventory includes every controlled connection’s incoming/outgoing edge/lane, turn direction, via lane and linkIndex, plus exact phase states/durations. It does not confer a safety certification.

| Intersection / program 0 | Existing phase sequence (seconds: state) | Missing prerequisites |
|---|---|---|
| `7732945699`, static | `40:GgrrGG → 5:yyrrGy → 40:rrGGGr → 5:rryyGr` | Four external controlled connections in XML against six phase indices; indices 2/3 need full internal-movement mapping review. No explicit minDur contract or all-red phase. Conflict/clearance/exception restoration unverified. |
| `cluster_1945600982_308878067`, static | `35:rrrgGGgrrrgGGg → 5:rrrgyygrrrgyyg → 6:rrrGrrgrrrGrrg → 5:rrryrryrrryrry → 34:GGgrrrrGGgrrrr → 5:yyyrrrryyyrrrr` | Fourteen external controlled connections mapped. Explicit minimum-green, movement-conflict review, permitted clearance/transition and restoration contract remain unverified; no all-red phase. |

Existing normal programs contain yellow durations; their presence alone does not establish a safe priority transition. Absence of an all-red phase is not a claim normal SUMO operation is inherently invalid; it means this task lacks a reviewed movement-specific clearance contract for interventions. Junction request/foe data and internal movements need a dedicated review.

Before implementing a controller: map all incoming/outgoing/internal movements and conflicts; establish minimum green and clearance requirements; permit only validated transitions; define bounded interventions and restoration of program, phase and remaining time. Test completion, cancellation, invalid turn, conflicts, disappearance, controller exception and shutdown, with read-back restoration assertions. Only then conduct matched normal/priority experiments in a separate output folder. All such controller tests/comparisons are **NOT_RUN**, not passing claims. The unchanged V3 normal-operation smoke verifies changing simulated signal telemetry, not priority intervention safety or benefit.
