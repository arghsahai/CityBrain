"""Verified route execution through TraCI.

Flow:
    planner decision
        → RouteAction
        → Executor pre-flight checks
        → TraCI setRoute
        → TraCI getRoute read-back
        → suffix verification
        → RouteResult

The executor does NOT decide which route is best.
The planner decides; the executor applies and verifies.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RouteAction:
    """Structured request to apply a route to a vehicle."""

    vehicle_id: str
    route: List[str]
    simulation_time: float = 0.0
    plan_id: Optional[str] = None


@dataclass
class RouteResult:
    """Structured outcome of a route execution attempt."""

    success: bool
    vehicle_id: str
    requested_route: List[str]
    observed_route: List[str] = field(default_factory=list)
    observed_suffix: List[str] = field(default_factory=list)
    simulation_time: float = 0.0
    reason: str = ""
    verification: str = "UNVERIFIED"
    plan_id: Optional[str] = None


class RouteExecutor:
    """
    Structured route execution with read-back verification.

    Supports successive replanning (P0 → P1 → P2 → ...).
    Every new route is applied from the vehicle's CURRENT position.

    The executor does NOT call an action successful merely because
    setRoute didn't throw an exception.  It verifies the route
    was actually applied by reading it back.

    Travelled-prefix handling:
        SUMO may preserve the already-travelled route prefix.
        Therefore the requested entire route ≠ necessarily the
        returned entire route.  Verification checks the remaining
        suffix from the vehicle's current route index.
    """

    def execute(self, traci_interface, action: RouteAction) -> RouteResult:
        """
        Execute a route action with pre-flight checks and verification.

        Pre-flight:
            1. Vehicle exists in SUMO
            2. Route is non-empty
            3. Route contains only strings

        Execution:
            setRoute(vehicle_id, route)

        Verification:
            getRoute() → compare suffix from current position
        """

        vehicle_id = action.vehicle_id
        route = list(action.route)

        # ---------------------------------------------------------
        # Pre-flight checks
        # ---------------------------------------------------------

        if not route:
            return RouteResult(
                success=False,
                vehicle_id=vehicle_id,
                requested_route=route,
                simulation_time=action.simulation_time,
                reason="empty_route",
                verification="PREFLIGHT_FAILED",
                plan_id=action.plan_id,
            )

        if not all(isinstance(e, str) and e for e in route):
            return RouteResult(
                success=False,
                vehicle_id=vehicle_id,
                requested_route=route,
                simulation_time=action.simulation_time,
                reason="invalid_edge_in_route",
                verification="PREFLIGHT_FAILED",
                plan_id=action.plan_id,
            )

        if not traci_interface.vehicle_exists(vehicle_id):
            return RouteResult(
                success=False,
                vehicle_id=vehicle_id,
                requested_route=route,
                simulation_time=action.simulation_time,
                reason="vehicle_not_found",
                verification="PREFLIGHT_FAILED",
                plan_id=action.plan_id,
            )

        # ---------------------------------------------------------
        # Apply route
        # ---------------------------------------------------------

        try:
            traci_interface.apply_route(vehicle_id, route)
        except Exception as exc:
            return RouteResult(
                success=False,
                vehicle_id=vehicle_id,
                requested_route=route,
                simulation_time=action.simulation_time,
                reason=f"setRoute_failed: {exc}",
                verification="EXECUTION_FAILED",
                plan_id=action.plan_id,
            )

        # ---------------------------------------------------------
        # Read-back verification
        # ---------------------------------------------------------

        try:
            observed_route = traci_interface.current_route(
                vehicle_id
            )
            observed_suffix = traci_interface.current_route_suffix(
                vehicle_id
            )
        except Exception as exc:
            return RouteResult(
                success=False,
                vehicle_id=vehicle_id,
                requested_route=route,
                simulation_time=action.simulation_time,
                reason=f"readback_failed: {exc}",
                verification="READBACK_FAILED",
                plan_id=action.plan_id,
            )

        # Verify the remaining suffix contains the requested route's
        # forward portion.  SUMO may prepend already-traversed edges.
        verification = self._verify_suffix(
            requested_route=route,
            observed_suffix=observed_suffix,
        )

        return RouteResult(
            success=verification == "VERIFIED",
            vehicle_id=vehicle_id,
            requested_route=route,
            observed_route=observed_route,
            observed_suffix=observed_suffix,
            simulation_time=action.simulation_time,
            reason="route_applied" if verification == "VERIFIED" else "suffix_mismatch",
            verification=verification,
            plan_id=action.plan_id,
        )

    @staticmethod
    def _verify_suffix(
        requested_route: List[str],
        observed_suffix: List[str],
    ) -> str:
        """
        Verify that the observed suffix matches the requested route.

        The vehicle's current edge may already be the first edge
        of the requested route.  SUMO preserves the travelled
        prefix, so the observed suffix should end with the
        requested route or match it from the vehicle's current
        position.

        A direct suffix match is the strictest check.  If the
        observed suffix contains all requested edges in order
        (possibly with the current-edge prefix already consumed),
        the route is considered verified.
        """

        if not requested_route:
            return "VERIFIED"

        if not observed_suffix:
            return "SUFFIX_EMPTY"

        # Check if the requested route appears as a suffix of
        # the observed suffix (handles travelled prefix).
        if observed_suffix[-len(requested_route):] == requested_route:
            return "VERIFIED"

        # Check if the observed suffix itself is a suffix of the
        # requested route (vehicle has already passed first edges).
        for i in range(len(requested_route)):
            if requested_route[i:] == observed_suffix:
                return "VERIFIED"

        # Check if the observed suffix starts with a subset of
        # the requested route (partial overlap from current position).
        for i in range(len(requested_route)):
            remaining = requested_route[i:]
            if (
                len(observed_suffix) >= len(remaining)
                and observed_suffix[:len(remaining)] == remaining
            ):
                return "VERIFIED"

        return "SUFFIX_MISMATCH"
