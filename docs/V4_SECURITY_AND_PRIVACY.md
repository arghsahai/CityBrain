# V4 security and privacy boundary

**Local, single-team research prototype only.** No production emergency operations, patient records, authenticated fleet feed or verified institutional identities. Internet deployment is unsupported: it needs TLS, individual identity/MFA, revocation/session controls, deployment hardening, external abuse protection, privacy/legal review and operational safety validation.

## Access controls

- Loopback bind; exact local Host and same-origin Origin allowlist; no CORS; JSON-only writes prevent browser simple-form CSRF. No credential cookies. CSP prohibits frames, third-party scripts and base-URL injection. Only optional OSM imagery tiles are allowed off-origin.
- Independent high-entropy operator and facility-scoped hospital bearer credentials from environment; minimum 32 ASCII characters, distinct roles, no public role-selection parameter. Constant-time comparison. Never returned in errors, logs or URLs. No provider credential is sent to browser.
- Public callers can submit confirmed TEST reports only and cannot read the queue, ambulance fix, routes or history. Operators verify/reject/delete test incidents and request/review recommendations. Hospital credentials update only the configured facility; they cannot verify or route incidents.
- Recommendation approval/acknowledgement requires the exact currently reviewed ID. Revalidation before approval rejects a changed ID. Changed position, costs or suitability require review again. These states never execute a real route.
- Five public submissions/minute, ten failed privileged-auth attempts/minute and 120 writes/minute, process-wide for this loopback prototype. Counters are fixed bounded deques, no retained IP logs. Limits reset on restart; they are basic abuse protection, not Internet-scale defense.
- JSON body ≤16 KiB, 5-second socket timeout, finite WGS84 coordinates, supported-region checks, whitelisted test types, 300-character descriptions, 200-character hospital notes, strict booleans and integer bed limits. Parameterized SQLite statements. UI uses textContent for untrusted text, not HTML injection. No uploads.

## Data minimization and retention

Reports contain a selected location, test type, optional short description, timestamps and provenance; do not enter personal/patient details. A browser location lookup happens only after an explicit click, runs once, and stays in the form until confirmation and submission. AUTHORIZED_GPS is reserved and rejected, not silently emulated by USER_SELECTED pins. OSM/hospital source links use no-referrer.

SQLite is owner-readable/writable (0600); new storage parent is 0700, symlinks rejected for the DB, secure_delete enabled. No keys or patient identifiers are stored. Descriptions/notes can still contain sensitive information if a user ignores the form guidance; there is no claim of automatic personal-data detection. Do not use real patient information.

Incident/status/audit records expire 24 hours after last update, pruned on service activity. Pruning is not a wall-clock deletion daemon while the program is stopped. Bounds: 1,000 incidents, 100 hospital statuses, 2,000 minimal audit events. Operator deletion removes a report; the audit retains action/opaque target ID/time/role, not coordinates or description. Hospital public responses omit notes/operator identity. Ambulance position, active recommendation and up to 50 reassessment events stay in process memory and disappear on restart. Traffic cache ≤256; invalid-future diagnostics ≤64; no provider recording is automatically written.

Use a fresh `/tmp` database for demonstrations. Stop the service before disposing of your test folder. Filesystem snapshots, backups, OS logs and third-party browser extensions are outside this application’s deletion guarantee. Browser password managers may offer to save a token; decline. Tokens are only in app memory, but browser/OS extensions and local privileged processes are trusted in this prototype.

## Failure isolation

No V4 imports of Core, TraCI or route executor. The explicit simulation CLI delegates to the unchanged V3 launcher; the live CLI does not. Provider access is disabled. Existing normalized offline records pass original direction/geometry/freshness/quarantine checks plus reverse full-edge coverage validation before becoming costs. Future source clocks >5 seconds ahead are quarantined before ordering, unknown times/directions never become measurements, stale data falls back to explicitly estimated roads. Invalid speed >70 m/s is rejected; fresh zero-speed roads are unavailable for routing, not free-flow. The 70 m/s cap is a conservative prototype input gate, not a calibrated physical model.

Recommended-route changes require human review, not physical dispatch. ETA never generates arrival. ARRIVAL_REPORTED is explicitly operator-reported. Police/signal outputs are logical advisories. Production deployment and genuine provider use remain external gates.
