"""Tests for CityBrainCore orchestration layer with mocked TraCI."""

import unittest
from unittest.mock import MagicMock, PropertyMock


def _build_traci_mock():
    """Build a MagicMock that mimics the traci module structure."""
    traci = MagicMock()

    # simulation
    traci.simulation.getTime.return_value = 0.0
    traci.simulation.getArrivedIDList.return_value = ()
    traci.simulation.getStartingTeleportIDList.return_value = ()

    # vehicles
    traci.vehicle.getIDList.return_value = ()
    traci.vehicle.getRoadID.return_value = "E1"
    traci.vehicle.getLaneID.return_value = "E1_0"
    traci.vehicle.getSpeed.return_value = 10.0
    traci.vehicle.getPosition.return_value = (50.0, 50.0)
    traci.vehicle.getAcceleration.return_value = 0.0
    traci.vehicle.getTypeID.return_value = "car"
    traci.vehicle.getRoute.return_value = ("E1", "E2", "E3")
    traci.vehicle.getRouteIndex.return_value = 0
    traci.vehicle.setRoute.return_value = None

    # edges
    traci.edge.getIDList.return_value = ()
    traci.edge.getLaneNumber.return_value = 1
    traci.edge.getLastStepVehicleIDs.return_value = ()
    traci.edge.getLastStepOccupancy.return_value = 0.0
    traci.edge.getLastStepHaltingNumber.return_value = 0
    traci.edge.getLastStepMeanSpeed.return_value = 0.0
    traci.edge.getFromJunction.return_value = "J1"
    traci.edge.getToJunction.return_value = "J2"

    # lanes
    traci.lane.getLength.return_value = 200.0
    traci.lane.getMaxSpeed.return_value = 13.89

    # traffic lights
    traci.trafficlight.getIDList.return_value = ()

    return traci


class TestCityBrainCoreConstruction(unittest.TestCase):
    def test_construction(self):
        from citybrain.core.citybrain_core import CityBrainCore
        traci = _build_traci_mock()
        core = CityBrainCore(traci)

        self.assertIsNotNone(core.traci)
        self.assertIsNotNone(core.city_state)
        self.assertIsNotNone(core.event_detector)
        self.assertIsNotNone(core.route_executor)
        self.assertIsNotNone(core.signal_executor)
        self.assertEqual(core._active_routes, {})


class TestActiveRoutes(unittest.TestCase):
    def setUp(self):
        from citybrain.core.citybrain_core import CityBrainCore
        self.traci = _build_traci_mock()
        self.core = CityBrainCore(self.traci)

    def test_set_get_clear(self):
        self.core.set_active_route("amb0", ["E1", "E2", "E3"])
        self.assertEqual(self.core.get_active_route("amb0"), ["E1", "E2", "E3"])

        self.core.set_active_route("amb1", ["E4", "E5"])
        self.assertEqual(self.core.get_active_route("amb1"), ["E4", "E5"])

        self.core.clear_active_route("amb0")
        self.assertIsNone(self.core.get_active_route("amb0"))
        self.assertEqual(self.core.get_active_route("amb1"), ["E4", "E5"])

    def test_get_nonexistent(self):
        self.assertIsNone(self.core.get_active_route("nonexistent"))


class TestExecuteRouteIntegration(unittest.TestCase):
    def setUp(self):
        from citybrain.core.citybrain_core import CityBrainCore
        self.traci = _build_traci_mock()
        self.core = CityBrainCore(self.traci)

    def test_execute_route_success_registers_active(self):
        # Make vehicle exist in SUMO.
        self.traci.vehicle.getIDList.return_value = ("amb0",)
        self.traci.vehicle.getRoute.return_value = ("E1", "E2", "E3")
        self.traci.vehicle.getRouteIndex.return_value = 0

        result = self.core.execute_route("amb0", ["E1", "E2", "E3"], plan_id="P0")

        self.assertTrue(result.success)
        self.assertEqual(self.core.get_active_route("amb0"), ["E1", "E2", "E3"])

    def test_execute_route_failure_no_active(self):
        # Vehicle does NOT exist in SUMO.
        self.traci.vehicle.getIDList.return_value = ()

        result = self.core.execute_route("amb0", ["E1", "E2"], plan_id="P0")

        self.assertFalse(result.success)
        self.assertIsNone(self.core.get_active_route("amb0"))


class TestRefreshState(unittest.TestCase):
    def setUp(self):
        from citybrain.core.citybrain_core import CityBrainCore
        self.traci = _build_traci_mock()
        self.core = CityBrainCore(self.traci)

    def test_refresh_populates_state(self):
        self.traci.simulation.getTime.return_value = 42.0
        self.traci.vehicle.getIDList.return_value = ("v1",)
        self.traci.vehicle.getRoadID.return_value = "E1"
        self.traci.vehicle.getLaneID.return_value = "E1_0"
        self.traci.vehicle.getSpeed.return_value = 10.0
        self.traci.vehicle.getPosition.return_value = (50.0, 50.0)
        self.traci.vehicle.getAcceleration.return_value = 0.0
        self.traci.vehicle.getTypeID.return_value = "car"
        self.traci.vehicle.getRoute.return_value = ("E1", "E2")
        self.traci.vehicle.getRouteIndex.return_value = 0
        self.traci.edge.getIDList.return_value = ("E1", "E2")

        city_state, removals = self.core.refresh_state()

        self.assertEqual(city_state.simulation_time, 42.0)
        self.assertEqual(city_state.vehicle_count(), 1)
        self.assertIsNotNone(city_state.get_vehicle("v1"))
        self.assertEqual(city_state.road_count(), 2)

    def test_vehicle_removal_clears_active_route(self):
        # First refresh with vehicle present.
        self.traci.vehicle.getIDList.return_value = ("amb0",)
        self.traci.edge.getIDList.return_value = ()
        self.core.refresh_state()
        self.core.set_active_route("amb0", ["E1", "E2"])

        # Second refresh: vehicle gone.
        self.traci.vehicle.getIDList.return_value = ()
        self.traci.simulation.getArrivedIDList.return_value = ("amb0",)
        city_state, removals = self.core.refresh_state()

        self.assertIn("amb0", removals)
        self.assertIsNone(self.core.get_active_route("amb0"))


if __name__ == "__main__":
    unittest.main()
