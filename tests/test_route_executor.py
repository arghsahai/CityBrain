"""Tests for RouteExecutor with verified route application."""

import unittest
from unittest.mock import MagicMock

from citybrain.core.route_executor import RouteExecutor, RouteAction, RouteResult


class TestRouteExecutor(unittest.TestCase):
    def setUp(self):
        self.traci_mock = MagicMock()
        self.executor = RouteExecutor()

    def test_successful_execution(self):
        self.traci_mock.vehicle_exists.return_value = True
        self.traci_mock.current_route.return_value = ["E1", "E2", "E3"]
        self.traci_mock.current_route_suffix.return_value = ["E1", "E2", "E3"]

        action = RouteAction(vehicle_id="amb0", route=["E1", "E2", "E3"])
        result = self.executor.execute(self.traci_mock, action)

        self.assertTrue(result.success)
        self.assertEqual(result.verification, "VERIFIED")
        self.assertEqual(result.requested_route, ["E1", "E2", "E3"])
        self.assertEqual(result.observed_route, ["E1", "E2", "E3"])
        self.traci_mock.apply_route.assert_called_once_with("amb0", ["E1", "E2", "E3"])

    def test_empty_route_preflight_failed(self):
        action = RouteAction(vehicle_id="amb0", route=[])
        result = self.executor.execute(self.traci_mock, action)

        self.assertFalse(result.success)
        self.assertEqual(result.verification, "PREFLIGHT_FAILED")
        self.assertEqual(result.reason, "empty_route")

    def test_invalid_edge_preflight_failed(self):
        action = RouteAction(vehicle_id="amb0", route=["E1", "", "E3"])
        result = self.executor.execute(self.traci_mock, action)

        self.assertFalse(result.success)
        self.assertEqual(result.verification, "PREFLIGHT_FAILED")
        self.assertEqual(result.reason, "invalid_edge_in_route")

    def test_none_edge_preflight_failed(self):
        action = RouteAction(vehicle_id="amb0", route=["E1", None, "E3"])
        result = self.executor.execute(self.traci_mock, action)

        self.assertFalse(result.success)
        self.assertEqual(result.verification, "PREFLIGHT_FAILED")

    def test_vehicle_not_found_preflight_failed(self):
        self.traci_mock.vehicle_exists.return_value = False

        action = RouteAction(vehicle_id="amb0", route=["E1", "E2"])
        result = self.executor.execute(self.traci_mock, action)

        self.assertFalse(result.success)
        self.assertEqual(result.verification, "PREFLIGHT_FAILED")
        self.assertEqual(result.reason, "vehicle_not_found")

    def test_set_route_exception_execution_failed(self):
        self.traci_mock.vehicle_exists.return_value = True
        self.traci_mock.apply_route.side_effect = Exception("TraCI error")

        action = RouteAction(vehicle_id="amb0", route=["E1", "E2"])
        result = self.executor.execute(self.traci_mock, action)

        self.assertFalse(result.success)
        self.assertEqual(result.verification, "EXECUTION_FAILED")
        self.assertIn("setRoute_failed", result.reason)

    def test_readback_exception_readback_failed(self):
        self.traci_mock.vehicle_exists.return_value = True
        self.traci_mock.current_route.side_effect = Exception("TraCI disconnect")

        action = RouteAction(vehicle_id="amb0", route=["E1", "E2"])
        result = self.executor.execute(self.traci_mock, action)

        self.assertFalse(result.success)
        self.assertEqual(result.verification, "READBACK_FAILED")

    def test_suffix_mismatch(self):
        self.traci_mock.vehicle_exists.return_value = True
        self.traci_mock.current_route.return_value = ["X1", "X2"]
        self.traci_mock.current_route_suffix.return_value = ["X1", "X2"]

        action = RouteAction(vehicle_id="amb0", route=["E1", "E2"])
        result = self.executor.execute(self.traci_mock, action)

        self.assertFalse(result.success)
        self.assertEqual(result.verification, "SUFFIX_MISMATCH")

    def test_travelled_prefix_handling(self):
        """Vehicle already passed E1, E2 — suffix is [E3, E4]."""
        self.traci_mock.vehicle_exists.return_value = True
        self.traci_mock.current_route.return_value = ["E1", "E2", "E3", "E4"]
        self.traci_mock.current_route_suffix.return_value = ["E3", "E4"]

        action = RouteAction(vehicle_id="amb0", route=["E1", "E2", "E3", "E4"])
        result = self.executor.execute(self.traci_mock, action)

        self.assertTrue(result.success)
        self.assertEqual(result.verification, "VERIFIED")

    def test_suffix_is_tail_of_requested(self):
        """Observed suffix matches the tail of the requested route."""
        self.traci_mock.vehicle_exists.return_value = True
        self.traci_mock.current_route.return_value = ["E5", "E19", "E11"]
        self.traci_mock.current_route_suffix.return_value = ["E19", "E11"]

        action = RouteAction(vehicle_id="amb0", route=["E5", "E19", "E11"])
        result = self.executor.execute(self.traci_mock, action)

        self.assertTrue(result.success)
        self.assertEqual(result.verification, "VERIFIED")

    def test_successive_replanning_p0_p1_p2(self):
        """Successive replanning: P0 → P1 → P2 all succeed."""
        self.traci_mock.vehicle_exists.return_value = True

        # P0
        self.traci_mock.current_route.return_value = ["E13", "E5", "E7", "E23"]
        self.traci_mock.current_route_suffix.return_value = ["E13", "E5", "E7", "E23"]
        r0 = self.executor.execute(
            self.traci_mock,
            RouteAction(vehicle_id="amb0", route=["E13", "E5", "E7", "E23"], plan_id="P0"),
        )
        self.assertTrue(r0.success)

        # P1 — vehicle now on E5, rerouted
        self.traci_mock.current_route.return_value = ["E13", "E5", "E19", "E11"]
        self.traci_mock.current_route_suffix.return_value = ["E5", "E19", "E11"]
        r1 = self.executor.execute(
            self.traci_mock,
            RouteAction(vehicle_id="amb0", route=["E5", "E19", "E11"], plan_id="P1"),
        )
        self.assertTrue(r1.success)

        # P2 — vehicle now on E19
        self.traci_mock.current_route.return_value = ["E13", "E5", "E19", "E23"]
        self.traci_mock.current_route_suffix.return_value = ["E19", "E23"]
        r2 = self.executor.execute(
            self.traci_mock,
            RouteAction(vehicle_id="amb0", route=["E19", "E23"], plan_id="P2"),
        )
        self.assertTrue(r2.success)

    def test_route_action_fields(self):
        action = RouteAction(
            vehicle_id="amb0",
            route=["E1", "E2"],
            simulation_time=300.0,
            plan_id="EM-001-P1",
        )
        self.assertEqual(action.vehicle_id, "amb0")
        self.assertEqual(action.route, ["E1", "E2"])
        self.assertEqual(action.simulation_time, 300.0)
        self.assertEqual(action.plan_id, "EM-001-P1")

    def test_route_result_fields(self):
        result = RouteResult(
            success=True,
            vehicle_id="amb0",
            requested_route=["E1", "E2"],
            observed_route=["E1", "E2"],
            observed_suffix=["E1", "E2"],
            simulation_time=300.0,
            reason="route_applied",
            verification="VERIFIED",
            plan_id="P0",
        )
        self.assertTrue(result.success)
        self.assertEqual(result.vehicle_id, "amb0")
        self.assertEqual(result.verification, "VERIFIED")


if __name__ == "__main__":
    unittest.main()
