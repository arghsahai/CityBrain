"""Core orchestration layer between SUMO/TraCI and CityBrain.

CityBrainCore owns:
    - TraCI interface
    - CityState (canonical snapshot)
    - State refresh
    - Event detection
    - Route execution (verified)
    - Signal execution boundary (advisory)

CityBrainCore does NOT own:
    - Planning decisions (Subhashini's planner decides)
    - Simulation configuration (Krishna's scenarios)
    - Experiment evaluation (Krishna's experiment runners)
"""

from copy import deepcopy

from citybrain.core.city_state import CityState
from citybrain.core.state_refresh import refresh_city_state
from citybrain.core.traci_interface import TraCIInterface
from citybrain.core.route_executor import RouteAction, RouteExecutor, RouteResult
from citybrain.core.signal_executor import SignalExecutor
from citybrain.events.detector import EventDetector
from citybrain.perception.state_adapter import adapt_city_state


class CityBrainCore:
    """
    Core orchestration layer between SUMO/TraCI and CityBrain.

    SUMO remains the source of truth for the live simulation state.
    CityState stores the current canonical snapshot.

    Architecture:
        SUMO → TraCI → CityBrainCore → CityState
        CityState → adapt_city_state → Planner
        Planner → KEEP/REPLAN/NO_ROUTE → RouteExecutor → TraCI → SUMO
    """

    def __init__(self, traci):
        self.traci = TraCIInterface(traci)
        self.city_state = CityState()
        self.event_detector = EventDetector()
        self.route_executor = RouteExecutor()
        self.signal_executor = SignalExecutor()

        # Per-vehicle active routes for route invalidation detection.
        self._active_routes = {}

    # ---------------------------------------------------------
    # State refresh
    # ---------------------------------------------------------

    def refresh_state(self, blocked_edges=None):
        """Refresh CityState from current SUMO state."""

        city_state, removals = refresh_city_state(
            self.traci.traci,
            self.city_state,
            blocked_edges=blocked_edges,
        )

        # Clean up active routes for removed vehicles.
        for vehicle_id in removals:
            self._active_routes.pop(vehicle_id, None)

        return city_state, removals

    def refresh_state_with_events(self, blocked_edges=None):
        """Refresh CityState and detect meaningful events."""

        previous_state = self._copy_state()

        city_state, removals = self.refresh_state(
            blocked_edges=blocked_edges,
        )

        events = self.event_detector.detect(
            previous_state,
            self.city_state,
            active_routes=self._active_routes if self._active_routes else None,
            removals=removals if removals else None,
        )

        return self.city_state, events, removals

    def step(self, blocked_edges=None):
        """Advance SUMO by one step and refresh state with events."""

        self.traci.step()

        return self.refresh_state_with_events(
            blocked_edges=blocked_edges,
        )

    # ---------------------------------------------------------
    # Vehicle state
    # ---------------------------------------------------------

    def get_vehicle_state(self, vehicle_id: str):
        return self.city_state.get_vehicle(vehicle_id)

    def get_road_state(self, road_id: str):
        return self.city_state.get_road(road_id)

    def get_current_route(self, vehicle_id: str):
        return self.traci.current_route(vehicle_id)

    def get_current_route_suffix(self, vehicle_id: str):
        return self.traci.current_route_suffix(vehicle_id)

    # ---------------------------------------------------------
    # Planner state adapter
    # ---------------------------------------------------------

    def build_planner_state(
        self,
        routes=None,
        hospitals=None,
        ambulances=None,
        blocked_edges=None,
    ):
        """
        Convert current CityState into the dictionary expected by
        Subhashini's planner using the authoritative adapt_city_state.

        This is the ONLY planner state adapter.
        """

        # Collect road topology for from/to junctions.
        road_topology = {}
        for road_id in self.city_state.roads:
            try:
                road_topology[road_id] = self.traci.edge_topology(
                    road_id
                )
            except Exception:
                pass

        # Collect blocked edges from CityState.
        detected_blocked = set()
        if blocked_edges is not None:
            detected_blocked = set(blocked_edges)
        else:
            for road_id, road in self.city_state.roads.items():
                if road.blocked:
                    detected_blocked.add(road_id)

        # Build ambulance list from CityState if not provided.
        if ambulances is None:
            ambulances = []
            for vehicle in self.city_state.vehicles.values():
                if vehicle.vehicle_type == "ambulance":
                    ambulances.append({
                        "id": vehicle.vehicle_id,
                        "available": True,
                        "edge": vehicle.edge_id,
                        "speed": vehicle.speed,
                    })

        return adapt_city_state(
            self.city_state,
            blocked_edges=detected_blocked,
            road_topology=road_topology,
            ambulances=ambulances,
            hospitals=hospitals,
            routes=routes,
            simulation_time=self.city_state.simulation_time,
        )

    # ---------------------------------------------------------
    # Route execution
    # ---------------------------------------------------------

    def execute_route(
        self,
        vehicle_id: str,
        route: list,
        plan_id: str = None,
    ) -> RouteResult:
        """
        Apply a planner-selected route to SUMO with verification.

        Returns a structured RouteResult — does not fake success.
        """

        action = RouteAction(
            vehicle_id=vehicle_id,
            route=list(route),
            simulation_time=self.city_state.simulation_time,
            plan_id=plan_id,
        )

        result = self.route_executor.execute(
            self.traci,
            action,
        )

        if result.success:
            self._active_routes[vehicle_id] = list(route)

        return result

    # ---------------------------------------------------------
    # Active routes
    # ---------------------------------------------------------

    def set_active_route(self, vehicle_id: str, route: list):
        """Register a route as actively being followed."""
        self._active_routes[vehicle_id] = list(route)

    def get_active_route(self, vehicle_id: str):
        """Get the active route for a vehicle, if any."""
        return self._active_routes.get(vehicle_id)

    def clear_active_route(self, vehicle_id: str):
        """Remove the active route for a vehicle."""
        self._active_routes.pop(vehicle_id, None)

    # ---------------------------------------------------------
    # Internal
    # ---------------------------------------------------------

    def _copy_state(self) -> CityState:
        """Create a shallow copy for event detection."""
        return CityState(
            simulation_time=self.city_state.simulation_time,
            vehicles=dict(self.city_state.vehicles),
            roads=dict(self.city_state.roads),
        )