# Network inventory

The active research baseline is regression/, not the retained initial team network at simulation/network/. Coordinates are synthetic metres. Each road pair is two directed edges; internal junction edges are excluded from counts.

## regression: 9 junctions, 24 directed external edges, 9 signal programs

| Junction | x (m) | y (m) | Configured type | Compiled signal |
|---|---|---|---|---|
| J1 | 0 | 0 | traffic_light | True |
| J2 | 100 | 0 | traffic_light | True |
| J3 | 200 | 0 | traffic_light | True |
| J4 | 0 | 100 | traffic_light | True |
| J5 | 100 | 100 | traffic_light | True |
| J6 | 200 | 100 | traffic_light | True |
| J7 | 0 | 200 | traffic_light | True |
| J8 | 100 | 200 | traffic_light | True |
| J9 | 200 | 200 | traffic_light | True |

| Edge | From | To | Lanes | Speed m/s | Lane length m |
|---|---|---|---|---|---|
| E1 | J1 | J2 | 1 | 13.90 | 89.60 |
| E2 | J2 | J1 | 1 | 13.90 | 89.60 |
| E3 | J2 | J3 | 1 | 13.90 | 89.60 |
| E4 | J3 | J2 | 1 | 13.90 | 89.60 |
| E5 | J4 | J5 | 1 | 13.90 | 85.60 |
| E6 | J5 | J4 | 1 | 13.90 | 85.60 |
| E7 | J5 | J6 | 1 | 13.90 | 85.60 |
| E8 | J6 | J5 | 1 | 13.90 | 85.60 |
| E9 | J7 | J8 | 1 | 13.90 | 89.60 |
| E10 | J8 | J7 | 1 | 13.90 | 89.60 |
| E11 | J8 | J9 | 1 | 13.90 | 89.60 |
| E12 | J9 | J8 | 1 | 13.90 | 89.60 |
| E13 | J1 | J4 | 1 | 13.90 | 89.60 |
| E14 | J4 | J1 | 1 | 13.90 | 89.60 |
| E15 | J4 | J7 | 1 | 13.90 | 89.60 |
| E16 | J7 | J4 | 1 | 13.90 | 89.60 |
| E17 | J2 | J5 | 1 | 13.90 | 85.60 |
| E18 | J5 | J2 | 1 | 13.90 | 85.60 |
| E19 | J5 | J8 | 1 | 13.90 | 85.60 |
| E20 | J8 | J5 | 1 | 13.90 | 85.60 |
| E21 | J3 | J6 | 1 | 13.90 | 89.60 |
| E22 | J6 | J3 | 1 | 13.90 | 89.60 |
| E23 | J6 | J9 | 1 | 13.90 | 89.60 |
| E24 | J9 | J6 | 1 | 13.90 | 89.60 |

## research: 12 junctions, 34 directed external edges, 12 signal programs

| Junction | x (m) | y (m) | Configured type | Compiled signal |
|---|---|---|---|---|
| J1 | 0 | 0 | traffic_light | True |
| J2 | 100 | 0 | traffic_light | True |
| J3 | 200 | 0 | traffic_light | True |
| J4 | 0 | 100 | traffic_light | True |
| J5 | 100 | 100 | traffic_light | True |
| J6 | 200 | 100 | traffic_light | True |
| J7 | 0 | 200 | traffic_light | True |
| J8 | 100 | 200 | traffic_light | True |
| J9 | 200 | 200 | traffic_light | True |
| J10 | 0 | 300 | traffic_light | True |
| J11 | 100 | 300 | traffic_light | True |
| J12 | 200 | 300 | traffic_light | True |

| Edge | From | To | Lanes | Speed m/s | Lane length m |
|---|---|---|---|---|---|
| E1 | J1 | J2 | 1 | 13.90 | 89.60 |
| E2 | J2 | J1 | 1 | 13.90 | 89.60 |
| E3 | J2 | J3 | 1 | 13.90 | 89.60 |
| E4 | J3 | J2 | 1 | 13.90 | 89.60 |
| E5 | J4 | J5 | 1 | 13.90 | 85.60 |
| E6 | J5 | J4 | 1 | 13.90 | 85.60 |
| E7 | J5 | J6 | 1 | 13.90 | 85.60 |
| E8 | J6 | J5 | 1 | 13.90 | 85.60 |
| E9 | J7 | J8 | 1 | 13.90 | 85.60 |
| E10 | J8 | J7 | 1 | 13.90 | 85.60 |
| E11 | J8 | J9 | 1 | 13.90 | 85.60 |
| E12 | J9 | J8 | 1 | 13.90 | 85.60 |
| E13 | J1 | J4 | 1 | 13.90 | 89.60 |
| E14 | J4 | J1 | 1 | 13.90 | 89.60 |
| E15 | J4 | J7 | 1 | 13.90 | 85.60 |
| E16 | J7 | J4 | 1 | 13.90 | 85.60 |
| E17 | J2 | J5 | 1 | 13.90 | 85.60 |
| E18 | J5 | J2 | 1 | 13.90 | 85.60 |
| E19 | J5 | J8 | 1 | 13.90 | 85.60 |
| E20 | J8 | J5 | 1 | 13.90 | 85.60 |
| E21 | J3 | J6 | 1 | 13.90 | 89.60 |
| E22 | J6 | J3 | 1 | 13.90 | 89.60 |
| E23 | J6 | J9 | 1 | 13.90 | 85.60 |
| E24 | J9 | J6 | 1 | 13.90 | 85.60 |
| E25 | J7 | J10 | 1 | 13.90 | 89.60 |
| E26 | J10 | J7 | 1 | 13.90 | 89.60 |
| E27 | J8 | J11 | 1 | 13.90 | 85.60 |
| E28 | J11 | J8 | 1 | 13.90 | 85.60 |
| E29 | J9 | J12 | 1 | 13.90 | 89.60 |
| E30 | J12 | J9 | 1 | 13.90 | 89.60 |
| E31 | J10 | J11 | 1 | 13.90 | 89.60 |
| E32 | J11 | J10 | 1 | 13.90 | 89.60 |
| E33 | J11 | J12 | 1 | 13.90 | 89.60 |
| E34 | J12 | J11 | 1 | 13.90 | 89.60 |

## Text topology and hospital

```text
Research extension: J10 ↔ J11 ↔ J12
                      ↕     ↕     ↕
Regression top row:  J7  ↔  J8  ↔  J9 (H1)
                      ↕     ↕     ↕
                     J4  ↔  J5  ↔  J6
                      ↕     ↕     ↕
                     J1  ↔  J2  ↔  J3
```

Ambulance departs at J1 on E13 at scheduled time 300; observed dispatch is 301.
The research emergency object labels the incident J3. Routing here models transport to
H1/J9, not a complete dispatch-to-patient-to-hospital workflow. H1 is configured metadata,
not a physical hospital building or live bed feed. Regression incoming hospital edges are
E11 and E23; the research extension adds E30 from J12. All hospital availability is static.
S08 adds ten edges E25–E34 and J10–J12 to offer a bypass after E7/E11 disruption.

## Base demand route catalogue

| Route ID | Directed edge sequence |
|---|---|
| normalRoute1 | E1 E3 |
| normalRoute2 | E13 E5 |
| normalRoute3 | E17 E19 |
| normalRoute4 | E21 E23 |
| normalRoute5 | E14 E1 |
| normalRoute6 | E18 E2 |
| normalRoute7 | E20 E6 |
| normalRoute8 | E24 E8 |
| normalRoute9 | E15 E9 |
| accidentRoute | E3 |
| ambulanceInitialRoute | E13 E5 E7 E23 |
| dynamicBlockageRoute | E7 |


These declared routes are not all active background flows. The four actual flows use normalRoute3/4/5/7. The historical emergency candidate catalogue R_EM_1–4 is defined in citybrain/integration/state_adapter.py; S08 research adds R_EM_5 explicitly. The integrated runtime can instead generate live topology candidates.
