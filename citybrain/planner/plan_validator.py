"""Plan validation that is independent of execution and SUMO."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real


@dataclass
class ValidationResult:
    valid: bool
    reason: str
    invalidated_component: str | None = None
    replan_required: bool = False
    remaining_route: list[str] = field(default_factory=list)
    checked_components: list[dict] = field(default_factory=list)


def _finite_measurement(value):
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


class PlanValidator:
    def validate(self, plan, state, remaining_route=None):
        """Return a legacy boolean while preserving old measurement tolerance.

        The legacy API historically validated blockage only. It now also rejects
        missing road records, but does not require travel-time fields that older
        runtime callers never supplied. Use validate_structured for the complete
        measurement contract.
        """
        return self.validate_structured(
            plan, state, remaining_route=remaining_route,
            require_measurements=False,
        ).valid

    def validate_structured(
        self,
        plan,
        state,
        *,
        remaining_route=None,
        require_measurements=True,
    ):
        if plan is None or not hasattr(plan, "route"):
            return ValidationResult(False, "missing_or_invalid_plan", replan_required=False)
        if not isinstance(state, Mapping):
            return ValidationResult(False, "invalid_state", replan_required=True)
        roads = state.get("roads")
        if not isinstance(roads, Mapping):
            return ValidationResult(False, "invalid_road_mapping", replan_required=True)

        selected_route = plan.route if remaining_route is None else remaining_route
        if not isinstance(selected_route, (list, tuple)):
            return ValidationResult(False, "invalid_route", replan_required=True)
        route = list(selected_route)
        if not route:
            return ValidationResult(True, "route_completed", remaining_route=[])

        checked = []
        for edge in route:
            if not isinstance(edge, str) or not edge:
                return ValidationResult(
                    False, "invalid_edge_id", str(edge), True, route, checked,
                )
            road = roads.get(edge)
            if not isinstance(road, Mapping):
                return ValidationResult(
                    False, "missing_road_state", edge, True, route, checked,
                )
            if road.get("blocked", False):
                checked.append({"edge": edge, "valid": False, "reason": "blocked_edge"})
                return ValidationResult(False, "blocked_edge", edge, True, route, checked)

            if require_measurements:
                if "travel_time" not in road or road["travel_time"] is None:
                    checked.append({"edge": edge, "valid": False,
                                    "reason": "travel_time_unavailable"})
                    return ValidationResult(
                        False, "travel_time_unavailable", edge, True, route, checked,
                    )
                travel_time = road["travel_time"]
                if not _finite_measurement(travel_time):
                    reason = "unreachable_edge" if travel_time == float("inf") else "invalid_travel_time"
                    checked.append({"edge": edge, "valid": False, "reason": reason})
                    return ValidationResult(False, reason, edge, True, route, checked)
                if travel_time < 0:
                    checked.append({"edge": edge, "valid": False,
                                    "reason": "invalid_travel_time"})
                    return ValidationResult(
                        False, "invalid_travel_time", edge, True, route, checked,
                    )
                if travel_time == 0:
                    length, speed = road.get("road_length"), road.get("speed_limit")
                    estimate_valid = (
                        road.get("congestion") == "NO_TRAFFIC"
                        and _finite_measurement(length) and length > 0
                        and _finite_measurement(speed) and speed > 0
                    )
                    if not estimate_valid:
                        checked.append({"edge": edge, "valid": False,
                                        "reason": "unavailable_zero_travel_time"})
                        return ValidationResult(
                            False, "unavailable_zero_travel_time", edge, True,
                            route, checked,
                        )
            checked.append({"edge": edge, "valid": True, "reason": "edge_valid"})

        return ValidationResult(
            True, "remaining_route_valid", remaining_route=route,
            checked_components=checked,
        )

    validate_result = validate_structured
    validate_plan = validate_structured
