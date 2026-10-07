"""Physical execution with exact active-suffix verification and failure recovery."""
from dataclasses import dataclass, field
from typing import List, Optional
from citybrain.integration.routing import validate_route


@dataclass
class RouteAction:
    vehicle_id: str
    route: List[str]
    simulation_time: float = 0.0
    plan_id: Optional[str] = None
    hospital: Optional[dict] = None


@dataclass
class RouteResult:
    success: bool
    vehicle_id: str
    requested_route: List[str]
    observed_route: List[str] = field(default_factory=list)
    observed_suffix: List[str] = field(default_factory=list)
    simulation_time: float = 0.0
    reason: str = ''
    verification: str = 'UNVERIFIED'
    plan_id: Optional[str] = None
    intended_suffix: List[str] = field(default_factory=list)
    physical_edge: str = ''
    route_index: Optional[int] = None
    previous_suffix: List[str] = field(default_factory=list)
    safe_to_continue: bool = True
    rollback_attempted: bool = False
    rollback_verified: bool = False


class RouteExecutor:
    def execute(self, interface, action):
        result = RouteResult(False, action.vehicle_id, list(action.route),
                             simulation_time=action.simulation_time, plan_id=action.plan_id)
        if not action.route:
            result.reason = 'empty_route'; result.verification = 'PREFLIGHT_FAILED'; return result
        if not all(isinstance(e, str) and e for e in action.route):
            result.reason = 'invalid_edge_in_route'; result.verification = 'PREFLIGHT_FAILED'; return result
        if not interface.vehicle_exists(action.vehicle_id):
            result.reason = 'vehicle_not_found'; result.verification = 'PREFLIGHT_FAILED'; return result
        try:
            before = interface.route_position(action.vehicle_id)
            route = list(action.route)
            # Legacy full-route requests are allowed only with an exact observed
            # travelled prefix. Runtime callers always submit an active suffix.
            index = before['route_index']
            if route[0] != before['edge'] and index > 0:
                if route[:index] == before['route'][:index] and route[index:index+1] == [before['edge']]:
                    route = route[index:]
            result.previous_suffix = list(before['remaining_route'])
            result.intended_suffix = route
            result.physical_edge = before['edge']
            validation = validate_route(interface, action.vehicle_id, route, action.hospital, before)
            if not validation.valid:
                result.reason = validation.reason
                result.verification = 'DEFERRED' if validation.deferred else 'PREFLIGHT_FAILED'
                return result
        except Exception as error:
            result.reason = f'preflight_failed: {error}'; result.verification = 'PREFLIGHT_FAILED'; return result
        try:
            interface.apply_route(action.vehicle_id, route)
        except Exception as error:
            result.reason = f'setRoute_failed: {error}'; result.verification = 'EXECUTION_FAILED'
            self._recover(interface, action.vehicle_id, before, result)
            return result
        try:
            after = interface.route_position(action.vehicle_id)
            result.observed_route = after['route']
            result.observed_suffix = after['remaining_route']
            result.route_index = after['route_index']
            # There is no simulationStep between action and read-back. Physical
            # movement cannot justify accepting a shorter route or extra edges.
            matched = after['edge'] == before['edge'] and self._verify_suffix(route, after['remaining_route']) == 'VERIFIED'
            result.verification = 'VERIFIED' if matched else 'SUFFIX_MISMATCH'
            result.reason = 'route_applied' if matched else 'suffix_mismatch'
            result.success = matched
        except Exception as error:
            result.reason = f'readback_failed: {error}'; result.verification = 'READBACK_FAILED'
        if not result.success:
            self._recover(interface, action.vehicle_id, before, result)
        return result

    @staticmethod
    def _recover(interface, vehicle_id, before, result):
        """Reconcile possible partial physical changes before allowing retries."""
        result.safe_to_continue = False
        try:
            current = interface.route_position(vehicle_id)
            if current['edge'] != before['edge']:
                return
            if current['remaining_route'] == before['remaining_route']:
                result.safe_to_continue = True
                return
            result.rollback_attempted = True
            interface.apply_route(vehicle_id, before['remaining_route'])
            observed = interface.route_position(vehicle_id)
            result.rollback_verified = (observed['edge'] == before['edge'] and
                                        observed['remaining_route'] == before['remaining_route'])
            result.safe_to_continue = result.rollback_verified
        except Exception:
            pass

    @staticmethod
    def _verify_suffix(requested_route, observed_suffix):
        if not observed_suffix:
            return 'SUFFIX_EMPTY'
        return 'VERIFIED' if list(requested_route) == list(observed_suffix) else 'SUFFIX_MISMATCH'
