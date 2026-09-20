"""Tests for CityBrain Core state models and perception functions."""

import math
import unittest

from citybrain.core.vehicle_state import VehicleState
from citybrain.core.road_state import RoadState, MEASURED, EMPTY, BLOCKED, UNKNOWN
from citybrain.core.city_state import CityState
from citybrain.core.traffic_perception import (
    calculate_congestion,
    calculate_travel_time,
    _determine_measurement_status,
)


class TestVehicleState(unittest.TestCase):
    def test_creation_all_fields(self):
        v = VehicleState(
            vehicle_id="v1",
            edge_id="E1",
            lane_id="E1_0",
            speed=15.0,
            position=(10.0, 20.0),
            route=["E1", "E2", "E3"],
            route_index=1,
            acceleration=1.5,
            vehicle_type="ambulance",
        )
        self.assertEqual(v.vehicle_id, "v1")
        self.assertEqual(v.edge_id, "E1")
        self.assertEqual(v.lane_id, "E1_0")
        self.assertEqual(v.speed, 15.0)
        self.assertEqual(v.position, (10.0, 20.0))
        self.assertEqual(v.route, ["E1", "E2", "E3"])
        self.assertEqual(v.route_index, 1)
        self.assertEqual(v.acceleration, 1.5)
        self.assertEqual(v.vehicle_type, "ambulance")

    def test_defaults(self):
        v = VehicleState(
            vehicle_id="v2",
            edge_id="E5",
            lane_id="E5_0",
            speed=0.0,
            position=(0.0, 0.0),
        )
        self.assertEqual(v.route, [])
        self.assertEqual(v.route_index, 0)
        self.assertEqual(v.acceleration, 0.0)
        self.assertEqual(v.vehicle_type, "")

    def test_edge_lane_aliases(self):
        v = VehicleState(
            vehicle_id="v3", edge_id="E7", lane_id="E7_1",
            speed=5.0, position=(0.0, 0.0),
        )
        self.assertEqual(v.edge, "E7")
        self.assertEqual(v.lane, "E7_1")


class TestRoadState(unittest.TestCase):
    def test_creation_all_fields(self):
        r = RoadState(
            road_id="E1",
            vehicle_count=5,
            average_speed=10.0,
            road_length=100.0,
            speed_limit=20.0,
            lane_count=2,
            occupancy=0.3,
            travel_time=10.0,
            congestion="MEDIUM",
            blocked=False,
            halting_count=2,
            measurement_status=MEASURED,
        )
        self.assertEqual(r.road_id, "E1")
        self.assertEqual(r.vehicle_count, 5)
        self.assertEqual(r.average_speed, 10.0)
        self.assertEqual(r.road_length, 100.0)
        self.assertEqual(r.speed_limit, 20.0)
        self.assertEqual(r.lane_count, 2)
        self.assertEqual(r.occupancy, 0.3)
        self.assertEqual(r.travel_time, 10.0)
        self.assertEqual(r.congestion, "MEDIUM")
        self.assertFalse(r.blocked)
        self.assertEqual(r.halting_count, 2)
        self.assertEqual(r.measurement_status, MEASURED)

    def test_queue_length_alias(self):
        r = RoadState(
            road_id="E1",
            vehicle_count=3,
            average_speed=5.0,
            road_length=100.0,
            speed_limit=20.0,
            lane_count=1,
            occupancy=0.5,
            travel_time=20.0,
            congestion="HIGH",
            halting_count=3,
        )
        self.assertEqual(r.queue_length, 3)
        self.assertEqual(r.queue_length, r.halting_count)

    def test_blocked_transition(self):
        r = RoadState(
            road_id="E1", vehicle_count=0, average_speed=0.0,
            road_length=100.0, speed_limit=20.0, lane_count=1,
            occupancy=0.0, travel_time=5.0, congestion="LOW",
            blocked=False,
        )
        self.assertFalse(r.blocked)
        r.blocked = True
        self.assertTrue(r.blocked)

    def test_unblocked_transition(self):
        r = RoadState(
            road_id="E1", vehicle_count=0, average_speed=0.0,
            road_length=100.0, speed_limit=20.0, lane_count=1,
            occupancy=0.0, travel_time=float("inf"), congestion="LOW",
            blocked=True,
        )
        self.assertTrue(r.blocked)
        r.blocked = False
        self.assertFalse(r.blocked)


class TestCityState(unittest.TestCase):
    def _make_vehicle(self, vid="v1", edge="E1"):
        return VehicleState(
            vehicle_id=vid, edge_id=edge, lane_id=f"{edge}_0",
            speed=10.0, position=(0.0, 0.0),
        )

    def _make_road(self, rid="E1"):
        return RoadState(
            road_id=rid, vehicle_count=0, average_speed=0.0,
            road_length=100.0, speed_limit=20.0, lane_count=1,
            occupancy=0.0, travel_time=5.0, congestion="LOW",
        )

    def test_vehicle_crud(self):
        cs = CityState()
        v = self._make_vehicle("v1")
        cs.update_vehicle(v)
        self.assertEqual(cs.vehicle_count(), 1)
        self.assertIs(cs.get_vehicle("v1"), v)
        self.assertIsNone(cs.get_vehicle("v2"))
        cs.remove_vehicle("v1")
        self.assertEqual(cs.vehicle_count(), 0)
        self.assertIsNone(cs.get_vehicle("v1"))

    def test_road_crud(self):
        cs = CityState()
        r = self._make_road("E1")
        cs.update_road(r)
        self.assertEqual(cs.road_count(), 1)
        self.assertIs(cs.get_road("E1"), r)
        self.assertIsNone(cs.get_road("E2"))
        cs.remove_road("E1")
        self.assertEqual(cs.road_count(), 0)

    def test_simulation_time(self):
        cs = CityState()
        cs.set_simulation_time(42.5)
        self.assertEqual(cs.simulation_time, 42.5)

    def test_remove_nonexistent(self):
        cs = CityState()
        cs.remove_vehicle("nonexistent")
        cs.remove_road("nonexistent")
        self.assertEqual(cs.vehicle_count(), 0)
        self.assertEqual(cs.road_count(), 0)


class TestTravelTime(unittest.TestCase):
    def test_empty_road(self):
        # Empty road uses free-flow: road_length / speed_limit.
        tt = calculate_travel_time(100.0, 20.0, 0.0, 0)
        self.assertEqual(tt, 5.0)

    def test_empty_road_not_zero(self):
        tt = calculate_travel_time(100.0, 20.0, 0.0, 0)
        self.assertNotEqual(tt, 0.0)

    def test_free_flow(self):
        tt = calculate_travel_time(100.0, 20.0, 18.0, 3)
        self.assertAlmostEqual(tt, 100.0 / 18.0)

    def test_congested(self):
        tt = calculate_travel_time(100.0, 20.0, 3.0, 10)
        self.assertAlmostEqual(tt, 100.0 / 3.0)

    def test_stopped(self):
        tt = calculate_travel_time(100.0, 20.0, 0.0, 10)
        self.assertTrue(math.isinf(tt))

    def test_blocked(self):
        tt = calculate_travel_time(100.0, 20.0, 10.0, 5, blocked=True)
        self.assertTrue(math.isinf(tt))

    def test_invalid_road_length(self):
        tt = calculate_travel_time(0.0, 20.0, 10.0, 5)
        self.assertTrue(math.isinf(tt))

    def test_invalid_speed_limit_empty(self):
        tt = calculate_travel_time(100.0, 0.0, 0.0, 0)
        self.assertTrue(math.isinf(tt))


class TestCongestion(unittest.TestCase):
    def test_empty_road(self):
        self.assertEqual(calculate_congestion(0.0, 20.0, 0), "NO_TRAFFIC")

    def test_high(self):
        self.assertEqual(calculate_congestion(5.0, 20.0, 10), "HIGH")

    def test_medium(self):
        self.assertEqual(calculate_congestion(10.0, 20.0, 10), "MEDIUM")

    def test_low(self):
        self.assertEqual(calculate_congestion(15.0, 20.0, 10), "LOW")

    def test_unknown_speed_limit(self):
        self.assertEqual(calculate_congestion(10.0, 0.0, 5), "UNKNOWN")


class TestMeasurementStatus(unittest.TestCase):
    def test_blocked(self):
        self.assertEqual(
            _determine_measurement_status(0, True, 100.0, 20.0), BLOCKED
        )

    def test_empty(self):
        self.assertEqual(
            _determine_measurement_status(0, False, 100.0, 20.0), EMPTY
        )

    def test_measured(self):
        self.assertEqual(
            _determine_measurement_status(5, False, 100.0, 20.0), MEASURED
        )

    def test_unknown_bad_length(self):
        self.assertEqual(
            _determine_measurement_status(5, False, 0.0, 20.0), UNKNOWN
        )

    def test_unknown_bad_speed(self):
        self.assertEqual(
            _determine_measurement_status(5, False, 100.0, 0.0), UNKNOWN
        )


if __name__ == "__main__":
    unittest.main()
