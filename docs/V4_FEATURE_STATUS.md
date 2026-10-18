# V4 feature status

This is an experimental local recommendation prototype, not an operational emergency-response service.

## Verified first vertical slice

- Baseline V3: 447 tests passed in 33.95 s.
- Graph/backend: 19 focused tests passed; full suite **466 passed in 36.34 s**.
- Separate LIVE DATA server requires no SUMO process; simulation launcher/runtime remain separate.
- Public confirmed TEST incident → pending queue → authenticated operator verification.
- USER_SELECTED test ambulance → directed snap with explicit ambiguity handling → legal connected recommendation, partial-edge geometry and estimated ETA → operator approval lifecycle.
- Actual native Chrome UI: submitted test report, signed in, verified report, placed ambulance (0.0 m snap on `1254851247#0`), generated first-leg route to `384801126#5`: 70 estimated edges, zero observed edges, PENDING_OPERATOR_REVIEW, RECOMMENDATION_ONLY.
- SVG fallback visibility defect found and corrected during browser QA. Narrow-layout hardening added. Cesium initialization was attempted but Chrome reported WebGL context initialization failure. **3D rendering is NOT_TESTED in this environment**, not a passing claim. Existing simulation 3D code is unchanged.
- Four retained OSM hospital locations, no inherited simulated capacities. Facility-scoped status and 15-minute expiration tested; road-level second-leg routing tested with recent staff reports.

## Not yet complete

Offline traffic fixture integration/reassessment verification, final regressions, current signal safety artifact, provider licensing comparison and setup/demo/security documentation remain in progress. No authentic provider, authorized fleet GPS, real dispatch, citywide routing or signal actuation is implemented. Chennai-wide globe/optional OSM basemap is implemented but browser 3D coverage verification is blocked by WebGL.
