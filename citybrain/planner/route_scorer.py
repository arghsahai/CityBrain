"""Deterministic edge-cost scoring; no measurement collection or route execution."""
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real


def finite_number(value):
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


@dataclass
class RouteScore:
    usable: bool
    reason: str
    base_travel_time: float | None = None
    congestion_penalty: float = 0.0
    final_score: float = float("inf")
    invalidated_edge: str | None = None
    components: list[dict] = field(default_factory=list)
    route: list[str] = field(default_factory=list)
    estimated_cost: float | None = None
    blocked: bool = False
    unreachable: bool = False

    @property
    def available(self):
        return self.usable


class RouteScorer:
    def calculate_score(self, route, state):
        """Legacy numeric interface, also used by PR #4's ScoreRecorder."""
        return self.explain_score(route, state).final_score

    def explain_score(self, route, state):
        """Seconds + legacy congestion penalties (LOW=0, MEDIUM=5, HIGH=15).

        For NO_TRAFFIC and zero time only, estimate seconds as road_length
        (metres) / speed_limit (metres/second), using supplied positive finite
        values. This is a free-flow estimate, not a new sensor measurement.
        Unknown/missing congestion adds no penalty but is explicitly recorded.
        Missing, negative, nonfinite or otherwise unusable times cannot win.
        """
        if not isinstance(route, (list, tuple)) or not route:
            return RouteScore(False, "empty_or_invalid_route")
        normalized_route = list(route)
        roads = state.get("roads", {}) if isinstance(state, Mapping) else None
        if not isinstance(roads, Mapping):
            return RouteScore(False, "invalid_road_mapping", route=normalized_route)
        total, penalty, components = 0.0, 0.0, []
        for edge in route:
            if not isinstance(edge, str) or not edge:
                return RouteScore(False, "invalid_edge_id", components=components,
                                  route=normalized_route)
            road = roads.get(edge)
            reason = None
            if not isinstance(road, Mapping):
                reason = "road_unavailable"
            elif road.get("blocked", False):
                reason = "blocked_edge"
            elif "travel_time" not in road or road["travel_time"] is None:
                reason = "travel_time_unavailable"
            if reason:
                components.append(dict(
                    edge=edge, travel_time=None, cost_source=None,
                    congestion=road.get("congestion") if isinstance(road, Mapping) else None,
                    congestion_penalty=0, available=False,
                    blocked=reason == "blocked_edge", reason=reason,
                ))
                return RouteScore(
                    False, reason, invalidated_edge=edge, components=components,
                    route=normalized_route, blocked=reason == "blocked_edge",
                )
            cost = road["travel_time"]
            congestion = road.get("congestion")
            source = "supplied_travel_time"
            if not finite_number(cost) or cost < 0:
                reason = "unreachable_edge" if cost == float("inf") else "invalid_travel_time"
            elif cost == 0:
                length, limit = road.get("road_length"), road.get("speed_limit")
                if (congestion == "NO_TRAFFIC" and finite_number(length) and length > 0
                        and finite_number(limit) and limit > 0):
                    cost = length / limit
                    source = "free_flow_estimate"
                    if not finite_number(cost) or cost <= 0:
                        reason = "invalid_free_flow_estimate"
                else:
                    reason = "zero_time_without_physical_estimate"
            if reason:
                components.append(dict(
                    edge=edge, travel_time=road["travel_time"], cost_source=source,
                    congestion=congestion, congestion_penalty=0, available=False,
                    blocked=False, reason=reason,
                ))
                return RouteScore(
                    False, reason, invalidated_edge=edge, components=components,
                    route=normalized_route, unreachable=reason == "unreachable_edge",
                )
            extra = 5 if congestion == "MEDIUM" else 15 if congestion == "HIGH" else 0
            known = congestion in ("LOW", "MEDIUM", "HIGH", "NO_TRAFFIC")
            components.append(dict(edge=edge, travel_time=cost, cost_source=source,
                                   congestion=congestion, congestion_penalty=extra,
                                   available=True, blocked=False,
                                   reason="known_congestion" if known else "unknown_congestion_no_penalty"))
            total += cost
            penalty += extra
            if not isfinite(total + penalty):
                return RouteScore(False, "route_cost_overflow", components=components,
                                  route=normalized_route, unreachable=True)
        return RouteScore(True, "route_scorable", total, penalty, total + penalty,
                          components=components, route=normalized_route,
                          estimated_cost=total if any(
                              component["cost_source"] == "free_flow_estimate"
                              for component in components
                          ) else None)

    # Descriptive additive alias for callers that prefer an action name.
    score_route = explain_score


RouteScoreResult = RouteScore
