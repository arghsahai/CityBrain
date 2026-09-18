# Controlled integration

Base: origin/main c43aeaf. Reference: feature/krishna-simulation 8d42c5f. No unrelated histories merged.

| Classification | Files | Decision |
|---|---|---|
| MAIN_ONLY | root test_*.py; main network/config/routes | Preserve unchanged |
| SHARED_COMPATIBLE | agents, models, replanner, validator | Preserve main unchanged |
| SHARED_CONFLICTING | emergency_planner.py, route_scorer.py | Preserve main; adapter supplies complete road values |
| SHARED_CONFLICTING | network nodes/edges | Preserve main paths; port Krishna network into network/regression |
| KRISHNA_ONLY | scenarios, runner, analysis, outcomes, five tests | Port current implementation |
| INTEGRATION_REQUIRED | state_adapter.py | Remove required core type import; optional opaque city_state argument supports future Argh integration |
| OBSOLETE_IN_KRISHNA | city.tll.xml, duplicate legacy controllers, old accident monitor, pre-fix CSVs | Do not port; validated runner provides static/dynamic paths |
| HISTORICAL_EVIDENCE | prior validation CSV/PNG/logs | Keep on historical branch; generate fresh integration measurements |

Argh dependency: main has no core package. The planner currently consumes roads/routes/ambulances/hospitals dictionaries. The adapter obtains these from SUMO without implementing CityState or VehicleState. Argh's branch is not merged or copied. Future core integration should supply its state through this boundary, reconciling empty-road travel-time semantics.

The independent Krishna branch remains unchanged. Main agents, planner, models and all ten teammate scripts are preserved byte-for-byte.
