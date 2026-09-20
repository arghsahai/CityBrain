"""Tests for CityBrain event detection."""

import unittest

from citybrain.core.vehicle_state import VehicleState
from citybrain.core.road_state import RoadState
from citybrain.core.city_state import CityState
from citybrain.events import EventType
from citybrain.events.detector import EventDetector


def _vehicle(vid, edge="E1", speed=10.0, vtype=""):
    return VehicleState(
        vehicle_id=vid, edge_id=edge, lane_id=f"{edge}_0",
        speed=speed, position=(0.0, 0.0), vehicle_type=vtype,
    )


def _road(rid, congestion="LOW", blocked=False):
    return RoadState(
        road_id=rid, vehicle_count=5, average_speed=10.0,
        road_length=100.0, speed_limit=20.0, lane_count=1,
        occupancy=0.1, travel_time=10.0, congestion=congestion,
        blocked=blocked, halting_count=0, measurement_status="MEASURED",
    )


class TestEventDetector(unittest.TestCase):
    def setUp(self):
        self.detector = EventDetector()

    def test_road_blocked(self):
        prev = CityState(roads={"E1": _road("E1", blocked=False)})
        curr = CityState(simulation_time=1.0, roads={"E1": _road("E1", blocked=True)})
        events = self.detector.detect(prev, curr)
        blocked = [e for e in events if e.event_type == EventType.ROAD_BLOCKED]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0].data["road_id"], "E1")

    def test_road_unblocked(self):
        prev = CityState(roads={"E1": _road("E1", blocked=True)})
        curr = CityState(simulation_time=1.0, roads={"E1": _road("E1", blocked=False)})
        events = self.detector.detect(prev, curr)
        unblocked = [e for e in events if e.event_type == EventType.ROAD_UNBLOCKED]
        self.assertEqual(len(unblocked), 1)

    def test_congestion_changed(self):
        prev = CityState(roads={"E1": _road("E1", congestion="LOW")})
        curr = CityState(simulation_time=1.0, roads={"E1": _road("E1", congestion="HIGH")})
        events = self.detector.detect(prev, curr)
        changed = [e for e in events if e.event_type == EventType.CONGESTION_CHANGED]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0].data["previous"], "LOW")
        self.assertEqual(changed[0].data["current"], "HIGH")

    def test_no_event_congestion_unchanged(self):
        prev = CityState(roads={"E1": _road("E1", congestion="LOW")})
        curr = CityState(simulation_time=1.0, roads={"E1": _road("E1", congestion="LOW")})
        events = self.detector.detect(prev, curr)
        self.assertEqual(len(events), 0)

    def test_route_invalidation(self):
        prev = CityState(roads={"E7": _road("E7", blocked=False)})
        curr = CityState(simulation_time=1.0, roads={"E7": _road("E7", blocked=True)})
        active_routes = {"amb0": ["E1", "E7", "E23"]}
        events = self.detector.detect(prev, curr, active_routes=active_routes)
        invalid = [e for e in events if e.event_type == EventType.ROUTE_INVALIDATED]
        self.assertEqual(len(invalid), 1)
        self.assertEqual(invalid[0].data["vehicle_id"], "amb0")
        self.assertIn("E7", invalid[0].data["blocked_edges"])

    def test_no_route_invalidation_no_blocked(self):
        prev = CityState(roads={"E7": _road("E7", blocked=False)})
        curr = CityState(simulation_time=1.0, roads={"E7": _road("E7", blocked=False)})
        active_routes = {"amb0": ["E1", "E7", "E23"]}
        events = self.detector.detect(prev, curr, active_routes=active_routes)
        invalid = [e for e in events if e.event_type == EventType.ROUTE_INVALIDATED]
        self.assertEqual(len(invalid), 0)

    def test_vehicle_arrived(self):
        prev = CityState(vehicles={"car0": _vehicle("car0")})
        curr = CityState(simulation_time=1.0)
        events = self.detector.detect(prev, curr, removals={"car0": "ARRIVED"})
        arrived = [e for e in events if e.event_type == EventType.VEHICLE_ARRIVED]
        self.assertEqual(len(arrived), 1)
        self.assertEqual(arrived[0].data["vehicle_id"], "car0")

    def test_vehicle_teleported(self):
        prev = CityState(vehicles={"car0": _vehicle("car0")})
        curr = CityState(simulation_time=1.0)
        events = self.detector.detect(prev, curr, removals={"car0": "TELEPORTED"})
        teleported = [e for e in events if e.event_type == EventType.VEHICLE_TELEPORTED]
        self.assertEqual(len(teleported), 1)

    def test_ambulance_state_changed(self):
        prev = CityState(
            vehicles={"amb0": _vehicle("amb0", edge="E1", vtype="ambulance")},
        )
        curr = CityState(
            simulation_time=1.0,
            vehicles={"amb0": _vehicle("amb0", edge="E2", vtype="ambulance")},
        )
        events = self.detector.detect(prev, curr)
        changed = [e for e in events if e.event_type == EventType.AMBULANCE_STATE_CHANGED]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0].data["previous_edge"], "E1")
        self.assertEqual(changed[0].data["current_edge"], "E2")

    def test_no_ambulance_event_for_car(self):
        prev = CityState(
            vehicles={"car0": _vehicle("car0", edge="E1", vtype="car")},
        )
        curr = CityState(
            simulation_time=1.0,
            vehicles={"car0": _vehicle("car0", edge="E2", vtype="car")},
        )
        events = self.detector.detect(prev, curr)
        ambulance = [e for e in events if e.event_type == EventType.AMBULANCE_STATE_CHANGED]
        self.assertEqual(len(ambulance), 0)

    def test_multiple_simultaneous(self):
        prev = CityState(
            vehicles={"amb0": _vehicle("amb0", edge="E1", vtype="ambulance")},
            roads={"E7": _road("E7", blocked=False, congestion="LOW")},
        )
        curr = CityState(
            simulation_time=1.0,
            vehicles={"amb0": _vehicle("amb0", edge="E2", vtype="ambulance")},
            roads={"E7": _road("E7", blocked=True, congestion="HIGH")},
        )
        events = self.detector.detect(
            prev, curr,
            active_routes={"amb0": ["E1", "E7", "E23"]},
        )
        types = {e.event_type for e in events}
        self.assertIn(EventType.ROAD_BLOCKED, types)
        self.assertIn(EventType.CONGESTION_CHANGED, types)
        self.assertIn(EventType.ROUTE_INVALIDATED, types)
        self.assertIn(EventType.AMBULANCE_STATE_CHANGED, types)


if __name__ == "__main__":
    unittest.main()
