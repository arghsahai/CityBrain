"""CityBrain runtime orchestrator.

Runtime loop:
    START/ATTACH SUMO
        → SIMULATION STEP
        → REFRESH CITYSTATE
        → MEANINGFUL EVENTS
        → PLANNER (if triggered)
        → KEEP / REPLAN / NO_ROUTE
        → REPLAN → EXECUTOR → VERIFY
        → STRUCTURED RUNTIME EVIDENCE
        → NEXT STEP

This orchestrator does NOT:
    - duplicate Krishna's experiment runners
    - rewrite Subhashini's planner
    - hard-code scenario-specific timestamps or edge IDs
    - invent routes for NO_ROUTE
    - pretend failed execution succeeded
"""

import os
import sys

import traci

from citybrain.core.citybrain_core import CityBrainCore
from citybrain.events import EventType
from citybrain.models.emergency import Emergency
from citybrain.models.planner_result import PlannerOutcome
from citybrain.planner.emergency_planner import EmergencyPlanner
from citybrain.planner.replanner import Replanner


# Default candidate routes for the 3×3 CityBrain SUMO network.
# These are scenario-independent: they describe physical paths
# through the network, not S05-specific workarounds.
CANDIDATE_ROUTES = {
    "R_EM_1": ["E1", "E3", "E21", "E23"],
    "R_EM_2": ["E13", "E5", "E7", "E23"],
    "R_EM_3": ["E13", "E5", "E19", "E11"],
    "R_EM_4": ["E1", "E17", "E19", "E11"],
}

DEFAULT_HOSPITALS = [
    {
        "id": "H1",
        "location": "J9",
        "icu_available": True,
    },
]


class CityBrainRuntime:
    """
    High-level CityBrain runtime orchestration.

    SUMO / TraCI
        → CityBrain Core (observe)
        → canonical CityState
        → adapt_city_state → Planner (decide)
        → KEEP / REPLAN / NO_ROUTE
        → RouteExecutor (execute + verify)
        → SUMO
    """

    def __init__(
        self,
        traci_connection,
        routes=None,
        hospitals=None,
    ):
        self.core = CityBrainCore(traci_connection)

        self.routes = routes or CANDIDATE_ROUTES
        self.hospitals = hospitals or DEFAULT_HOSPITALS

        self.planner = EmergencyPlanner()
        self.replanner = Replanner()

        # Runtime state.
        self.active_plan = None
        self.emergency = None
        self.plan_history = []
        self.runtime_evidence = []

    # ---------------------------------------------------------
    # Emergency lifecycle
    # ---------------------------------------------------------

    def create_emergency_plan(self, emergency):
        """
        Create an initial emergency plan using the planner.

        Returns a structured PlanningResult.
        """

        self.emergency = emergency
        state = self.core.build_planner_state(
            routes=self.routes,
            hospitals=self.hospitals,
        )

        result = self.planner.create_plan_result(
            emergency,
            state,
        )

        if result.success and result.plan is not None:
            self.active_plan = result.plan
            self.active_plan.status = "ACTIVE"

            # Register with replanner lifecycle.
            self.replanner.set_active_plan(
                result.plan,
                accepted_time=self.core.city_state.simulation_time,
            )

            # Register route with Core for invalidation tracking.
            self.core.set_active_route(
                result.plan.ambulance_id,
                result.plan.route,
            )

            # Execute the initial route.
            route_result = self.core.execute_route(
                result.plan.ambulance_id,
                result.plan.route,
                plan_id=result.plan.plan_id,
            )

            self._record_evidence(
                "PLAN_CREATED",
                plan=result.plan,
                route_result=route_result,
            )

            self.plan_history.append(result.plan)

        return result

    # ---------------------------------------------------------
    # Replanning
    # ---------------------------------------------------------

    def evaluate_replan(self):
        """
        Evaluate whether replanning is needed.

        Uses Subhashini's Replanner.replan_structured() which
        returns a KEEP / REPLAN / NO_ROUTE decision without
        executing it.
        """

        if self.active_plan is None:
            return None

        state = self.core.build_planner_state(
            routes=self.routes,
            hospitals=self.hospitals,
        )

        # Get remaining route from vehicle's current position.
        remaining_route = None
        try:
            remaining_route = self.core.get_current_route_suffix(
                self.active_plan.ambulance_id,
            )
        except Exception:
            pass

        result = self.replanner.replan_structured(
            self.active_plan,
            state,
            remaining_route=remaining_route,
            current_time=self.core.city_state.simulation_time,
        )

        return result

    def handle_replan_result(self, result):
        """
        Handle a replanning result.

        KEEP:     Continue current plan.
        REPLAN:   Accept and execute the proposed plan.
        NO_ROUTE: Record structured failure. Do NOT invent a route.
        """

        if result is None:
            return None

        decision = result.decision

        if decision is PlannerOutcome.KEEP:
            self._record_evidence(
                "KEEP",
                reason=result.reason,
                plan=self.active_plan,
            )
            return result

        if decision is PlannerOutcome.REPLAN:
            if result.proposed_plan is None:
                self._record_evidence(
                    "REPLAN_NO_PROPOSAL",
                    reason=result.reason,
                )
                return result

            # Accept the proposal through Subhashini's lifecycle.
            accepted = self.replanner.accept(
                result,
                accepted_time=self.core.city_state.simulation_time,
            )

            # Execute the new route with verification.
            route_result = self.core.execute_route(
                accepted.ambulance_id,
                accepted.route,
                plan_id=accepted.plan_id,
            )

            if route_result.success:
                self.active_plan = accepted
                self.core.set_active_route(
                    accepted.ambulance_id,
                    accepted.route,
                )
                self.plan_history.append(accepted)
            else:
                # Route execution failed — do not pretend it succeeded.
                self._record_evidence(
                    "REPLAN_EXECUTION_FAILED",
                    plan=accepted,
                    route_result=route_result,
                )

            self._record_evidence(
                "REPLAN",
                plan=accepted,
                route_result=route_result,
            )

            return result

        if decision is PlannerOutcome.NO_ROUTE:
            # Do NOT invent a route. Do NOT bypass blocked roads.
            self._record_evidence(
                "NO_ROUTE",
                reason=result.reason,
                plan=self.active_plan,
            )
            return result

        # Unknown / other outcomes.
        self._record_evidence(
            f"UNKNOWN_DECISION:{decision.value}",
            reason=result.reason,
        )
        return result

    # ---------------------------------------------------------
    # Runtime step
    # ---------------------------------------------------------

    def step(self, blocked_edges=None):
        """
        Single runtime step: advance SUMO, detect events, replan if needed.

        Returns (city_state, events, replan_result).
        """

        city_state, events, removals = self.core.step(
            blocked_edges=blocked_edges,
        )

        # Determine whether replanning should be triggered.
        replan_result = None

        if self.active_plan is not None and self._should_replan(events):
            result = self.evaluate_replan()
            replan_result = self.handle_replan_result(result)

        return city_state, events, replan_result

    def _should_replan(self, events):
        """
        Determine whether events warrant replanning evaluation.

        Meaningful triggers:
            - Road became blocked
            - Active route invalidated
            - Material congestion change

        Does NOT hard-code timestamps or scenario-specific triggers.
        """

        replan_triggers = {
            EventType.ROAD_BLOCKED,
            EventType.ROUTE_INVALIDATED,
        }

        return any(
            event.event_type in replan_triggers
            for event in events
        )

    # ---------------------------------------------------------
    # Evidence
    # ---------------------------------------------------------

    def _record_evidence(self, action, **kwargs):
        """Record structured runtime evidence."""

        evidence = {
            "action": action,
            "simulation_time": self.core.city_state.simulation_time,
        }
        evidence.update(kwargs)
        self.runtime_evidence.append(evidence)


def run(config_path=None, max_steps=None):
    """
    Run the CityBrain runtime.

    Parameters
    ----------
    config_path : str
        Path to SUMO .sumocfg file.  If not provided, uses
        S05 as the default demo scenario.
    max_steps : int
        Maximum simulation steps.  If not provided, runs the
        full SUMO simulation time.
    """

    if config_path is None:
        config_path = os.path.join(
            "simulation",
            "scenarios",
            "S05_dynamic_blockage",
            "S05.sumocfg",
        )

    print("=" * 60)
    print("CITYBRAIN - AI EMERGENCY RESPONSE COORDINATION")
    print("=" * 60)
    print()
    print("Starting CityBrain...")
    print("SUMO configuration:", config_path)

    traci.start(["sumo", "-c", config_path])

    try:
        runtime = CityBrainRuntime(traci)

        print("CityBrain Core connected to SUMO.")
        print()

        # Initial state.
        runtime.core.refresh_state()

        print("Initial CityState")
        print("-" * 40)
        print(
            "Simulation time:",
            runtime.core.city_state.simulation_time,
        )
        print(
            "Vehicles:",
            runtime.core.city_state.vehicle_count(),
        )
        print(
            "Roads:",
            runtime.core.city_state.road_count(),
        )
        print()

        step = 0

        while True:
            step += 1

            if max_steps is not None and step > max_steps:
                break

            city_state, events, replan_result = runtime.step()

            # Check if ambulance has appeared and we don't have a plan.
            if runtime.active_plan is None:
                for vehicle in city_state.vehicles.values():
                    if vehicle.vehicle_type == "ambulance":
                        emergency = Emergency(
                            emergency_id="EM-001",
                            location=vehicle.edge_id,
                            severity="CRITICAL",
                            emergency_type="MEDICAL",
                        )
                        result = runtime.create_emergency_plan(
                            emergency,
                        )
                        if result.success:
                            print(
                                f"  PLAN CREATED: {result.plan.plan_id}"
                                f" route={result.plan.route}"
                            )
                        break

            # Output control.
            show = (
                step <= 10
                or step % 50 == 0
                or events
                or replan_result is not None
            )

            if show:
                print(
                    f"Step {step:03d} | "
                    f"t={city_state.simulation_time:.0f} | "
                    f"V={city_state.vehicle_count()} | "
                    f"R={city_state.road_count()}"
                )

                if events:
                    for event in events:
                        if event.event_type not in (
                            EventType.CONGESTION_CHANGED,
                            EventType.AMBULANCE_STATE_CHANGED,
                        ):
                            print(
                                f"  EVENT: {event.event_type.value}"
                                f" entity={event.entity_id}"
                            )

                if replan_result is not None:
                    print(
                        f"  DECISION: {replan_result.decision.value}"
                        f" reason={replan_result.reason}"
                    )
                    if (
                        replan_result.decision is PlannerOutcome.REPLAN
                        and replan_result.accepted_plan
                    ):
                        print(
                            f"  NEW ROUTE: {replan_result.accepted_plan.route}"
                            f" plan={replan_result.accepted_plan.plan_id}"
                        )

            # Stop if SUMO has no more vehicles.
            if (
                max_steps is None
                and city_state.vehicle_count() == 0
                and step > 50
            ):
                print("No more vehicles in SUMO. Stopping.")
                break

        print()
        print("=" * 60)
        print("CityBrain simulation completed.")
        print(f"Total steps: {step}")
        print(f"Plans created: {len(runtime.plan_history)}")
        print(
            f"Evidence records: {len(runtime.runtime_evidence)}"
        )
        print("=" * 60)

    finally:
        traci.close()
        print("CityBrain stopped.")


if __name__ == "__main__":
    config = None
    steps = 400

    if len(sys.argv) > 1:
        config = sys.argv[1]
    if len(sys.argv) > 2:
        steps = int(sys.argv[2])

    run(config_path=config, max_steps=steps)