"""Chennai-only confirmation of soft route-change proposals.

Canonical Core readings and teammate policy/scoring are unchanged. A stopped
measurement is not promoted to a confirmed road closure by this acceptance guard.
"""
from dataclasses import dataclass, replace
import math

from citybrain.integration.routing import validate_route
from citybrain.main import CityBrainRuntime
from citybrain.models.planner_result import PlannerOutcome


@dataclass(frozen=True)
class StabilityConfig:
    confirmation_seconds: float = 20.0

    def __post_init__(self):
        if isinstance(self.confirmation_seconds, bool) or not math.isfinite(self.confirmation_seconds) or self.confirmation_seconds < 0:
            raise ValueError('confirmation_seconds must be finite and nonnegative')


class SoftRouteGuard:
    def __init__(self, config=None):
        self.config = config or StabilityConfig()
        self.reset()

    def reset(self):
        self.pending_route = None
        self.pending_since = None

    def consider(self, result, *, now, active_since, last_replan_time,
                 minimum_commitment, cooldown, hard_reason=None):
        details = dict(raw_decision=result.decision.value, hard_reason=hard_reason,
                       confirmation_seconds=self.config.confirmation_seconds)
        if result.decision is not PlannerOutcome.REPLAN or result.proposed_plan is None:
            self.reset()
            return result, dict(details, outcome='NOT_A_ROUTE_CHANGE')
        if hard_reason:
            self.reset()
            return result, dict(details, outcome='HARD_FAILURE_BYPASS')
        route = list(result.proposed_plan.route)
        # The vehicle's movement along a common prefix must not restart the timer.
        same = (self.pending_route and route and route[0] in self.pending_route and
                self.pending_route[self.pending_route.index(route[0]):] == route)
        if not same:
            self.pending_since = now
        self.pending_route = route
        elapsed = now-self.pending_since
        commitment = active_since is None or now-active_since >= minimum_commitment
        cooled = last_replan_time is None or now-last_replan_time >= cooldown
        confirmed = elapsed >= self.config.confirmation_seconds
        details.update(pending_since=self.pending_since, observed_duration=elapsed,
                       commitment_satisfied=commitment, cooldown_satisfied=cooled)
        if confirmed and commitment and cooled:
            return result, dict(details, outcome='SOFT_CHANGE_CONFIRMED')
        reason = ('soft_change_confirmation_pending' if not confirmed else
                  'soft_change_commitment_pending' if not commitment else 'soft_change_cooldown_pending')
        effective = replace(result, decision=PlannerOutcome.KEEP, reason=reason,
            commitment_satisfied=commitment, cooldown_satisfied=cooled,
            metadata={**result.metadata, 'upstream_reason': result.reason})
        return effective, dict(details, outcome='SOFT_CHANGE_DEFERRED')


def hard_invalidation(remaining_route, roads, physical_validation):
    """Only a specifically measured stopped-traffic invalidation is soft.

    Other missing/invalid input contracts are left to the existing runtime. No
    invented finite travel time, closure inference or topology change is made.
    """
    if not physical_validation.valid:
        return 'physical_route_invalid:'+physical_validation.reason
    if any(roads.get(edge, {}).get('blocked') for edge in remaining_route):
        return 'explicit_blockage_on_remaining_route'
    for edge in remaining_route:
        road = roads.get(edge)
        if not isinstance(road, dict):
            return 'missing_road_state'
        travel_time = road.get('travel_time')
        if not isinstance(travel_time, bool) and isinstance(travel_time, (float, int)) and math.isfinite(travel_time) and travel_time > 0:
            continue
        stopped = (travel_time == math.inf and road.get('vehicle_count', 0) > 0 and
                   road.get('average_speed') == 0 and road.get('road_length', 0) > 0 and
                   road.get('speed_limit', 0) > 0)
        if not stopped:
            return 'non_transient_invalid_measurement:'+edge
    return None


class ChennaiRuntime(CityBrainRuntime):
    """Only acceptance of soft proposals differs from the validated runtime."""
    def __init__(self, *args, stability_config=None, **kwargs):
        self.stability_guard = SoftRouteGuard(stability_config)
        super().__init__(*args, **kwargs)

    def handle_replan_result(self, result):
        if result is None or self.terminal_outcome:
            return super().handle_replan_result(result)
        context = self._last_context
        roads = context.get('planner_state', {}).get('roads', {})
        hard_reason = None
        if result.decision is PlannerOutcome.REPLAN:
            physical = validate_route(self.core.traci, self.ambulance_id, result.remaining_route,
                self.hospital, context.get('physical_position'))
            hard_reason = hard_invalidation(result.remaining_route, roads, physical)
        effective, details = self.stability_guard.consider(result, now=self.now,
            active_since=self.replanner.active_since, last_replan_time=self.replanner.last_replan_time,
            minimum_commitment=self.config.minimum_commitment, cooldown=self.config.cooldown,
            hard_reason=hard_reason)
        self._record_evidence('STABILITY_DECISION', planner_result=effective,
            remaining_route=result.remaining_route, stability=details)
        if details['outcome'] == 'SOFT_CHANGE_CONFIRMED':
            # Count the actual observation/confirmation delay, not just execution.
            self._pending_since = details['pending_since']
        previous = self.active_plan
        handled = super().handle_replan_result(effective)
        if self.active_plan is not previous:
            self.stability_guard.reset()
        return handled

    def _finalize(self, outcome, reason):
        self.stability_guard.reset()
        return super()._finalize(outcome, reason)

    def summary(self):
        result = super().summary()
        result['stability_guard'] = dict(confirmation_seconds=self.stability_guard.config.confirmation_seconds,
                                         pending=self.stability_guard.pending_route is not None)
        return result
