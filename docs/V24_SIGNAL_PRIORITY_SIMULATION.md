# V2.4 simulated signal-priority scope

SUMO signal phases and link states are observed and displayed in the Chennai
dashboard, with elapsed / remaining phase time only when TraCI supplies internally
consistent switch timing. They belong to synthetic signal programs at OSM junctions; their
presence does not verify real signal locations or municipal timing. Existing
SignalAgent recommendations are advisory and the current UI labels them as such.

## Implementation status

Signal priority is **not physically applied**, even inside the simulation. The
Core exposes a low-level TraCI `setPhase` method, but the planner recommendation
contains a junction target rather than a validated incoming/outgoing controlled
link, minimum-green contract, transition path, or restoration record. The imported
programs do not provide a reviewed phase-compatibility policy. Calling `setPhase`
directly could skip yellow/all-red clearance, conflict with a movement, or leave a
program altered after emergency departure. This milestone therefore keeps the
advisory-only boundary and does not add unsafe signal writes.

The dashboard reports signal ID, phase, link-state string, and up to four current
planner recommendations labeled `ADVISORY_ONLY · NOT APPLIED`. It does not invent
phase elapsed time or remaining green. To implement a future simulated
controller safely, first model each controlled link's from/to lane, enumerate
compatible phases and transition phases from the loaded SUMO program, define and
test minimum green / clearance / cooldown rules, and record the original program
for restoration. Each applied state must be checked against the actual controlled
links and reverted on missing telemetry, timeout, vehicle departure or controller
failure. Real municipal controllers remain out of scope.

## Current validation

Existing SUMO tests verify actual signal telemetry changes through multiple
program states. They verify observation only, not priority grant or actuation.
The advisory `REQUEST_SIGNAL_PRIORITY` entries stay distinguishable from applied
simulation state. No dashboard or provider callback writes a signal phase.

## V3.1 network capability audit

The loaded `simulation/chennai/network/chennai.net.xml` contains two SUMO traffic
lights. Its static programs expose 4 controlled connections across the first
light and 14 across the second. Program phases have fixed `duration` values but
`minDur` and `maxDur` are unset (`-1`). The phase strings contain green/yellow
transitions, but neither program establishes a reviewed per-movement emergency
compatibility table or a guaranteed all-red clearance/restoration contract. The
planner's signal recommendation identifies a junction, not an incoming-lane to
outgoing-lane movement and link index. The network is therefore insufficient to
activate even a SUMO-only priority controller under the V3.1 safety requirements.
Only telemetry and advisory display remain enabled; no phase or program writes
are introduced.
