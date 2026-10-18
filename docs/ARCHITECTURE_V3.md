# CityBrain V3.0 prototype architecture

## Runtime and data flow

```mermaid
flowchart LR
  SUMO[SUMO: vehicles, roads, signals] --> CORE[Existing Core and TraCI]
  CORE --> PLANNER[Existing planner / validator / stability policy]
  PLANNER --> EXEC[Route executor and read-back]
  EXEC --> CORE
  CORE --> TELEMETRY[Failure-isolated local telemetry]
  TRAFFIC[HERE / TomTom / synthetic replay] --> ADAPTER[Normalized advisory evidence]
  ADAPTER --> MATCH[Directed geometry matcher]
  MATCH --> CACHE[Bounded freshness-aware cache]
  CACHE --> TELEMETRY
  TELEMETRY --> SERVER[Local read-only dashboard server]
  SERVER --> CESIUM[Cesium or SVG fallback]
  TRAFFIC -. offline experiment only .-> EVAL[Opt-in candidate evaluator]
  EVAL -. comparison output only .-> EXP[Controlled experiment harness]
  DEVICE[User-consented browser location] --> LOCAL[Browser memory and local map match]
  LOCAL -. no server upload or planner input .-> CESIUM
```

## Authority boundaries

SUMO and the existing Core provide canonical vehicle, road and signal state.
The existing planner, validator, Chennai 20-second soft-change guard, hard-failure
path, route executor and physical read-back remain the only route commitment path.
Provider observations remain advisory; the optional evaluator produces a separate
candidate cost comparison and is disabled by default. It neither mutates canonical
measurements nor calls the planner or executor. The browser GPS marker is kept in
the tab and never enters the runtime.

## Provenance labels

| Label | Meaning |
|---|---|
| `SUMO_SIMULATED` | Ground-truth state observed from the local SUMO simulation |
| `SYNTHETIC_SAMPLE` | Invented fixture used to exercise the offline traffic pipeline |
| `REPLAY` | Recorded observations shown from a saved file; not live |
| `MOCKED_PROVIDER` | Test-only provider response |
| `HERE_LIVE` / `TOMTOM_LIVE` | Genuine adapter response only; unavailable until explicitly authorized and observed |
| `CONSENTED_DEVICE_LOCAL` | Browser geolocation held in tab memory; never a SUMO vehicle state |

Unknown, stale, expired, unmatched and ambiguous evidence remains visibly distinct.
No genuine provider response was obtained during this implementation.
