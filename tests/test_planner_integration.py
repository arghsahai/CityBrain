"""Tests for planner integration boundary."""

import unittest

from citybrain.core.vehicle_state import VehicleState
from citybrain.core.road_state import RoadState
from citybrain.core.city_state import CityState
from citybrain.perception.state_adapter import adapt_city_state
from citybrain.models.planner_result import PlannerOutcome, ReplanningResult
from citybrain.models.plan import EmergencyPlan


class TestAdaptCityState(unittest.TestCase):
    """Test CityState → adapt_city_state mapping correctness."""

    def _make_city_state(self):
        cs = CityState(simulation_time=300.0)

        cs.update_vehicle(VehicleState(
            vehicle_id="amb0", edge_id="E5", lane_id="E5_0",
            speed=12.0, position=(50.0, 50.0),
            route=["E13", "E5", "E7", "E23"],
            route_index=1, vehicle_type="ambulance",
        ))
        cs.update_vehicle(VehicleState(
            vehicle_id="car0", edge_id="E1", lane_id="E1_0",
            speed=8.0, position=(10.0, 10.0),
            vehicle_type="car",
        ))

        cs.update_road(RoadState(
            road_id="E5", vehicle_count=3, average_speed=10.0,
            road_length=200.0, speed_limit=13.89, lane_count=1,
            occupancy=0.15, travel_time=20.0, congestion="LOW",
            blocked=False, halting_count=0, measurement_status="MEASURED",
        ))
        cs.update_road(RoadState(
            road_id="E7", vehicle_count=0, average_speed=0.0,
            road_length=200.0, speed_limit=13.89, lane_count=1,
            occupancy=0.0, travel_time=14.4, congestion="NO_TRAFFIC",
            blocked=True, halting_count=0, measurement_status="BLOCKED",
        ))

        return cs

    def test_basic_mapping(self):
        cs = self._make_city_state()
        result = adapt_city_state(
            cs,
            blocked_edges={"E7"},
            ambulances=[{"id": "amb0", "available": True, "edge": "E5", "speed": 12.0}],
            hospitals=[{"id": "H1", "location": "J9", "icu_available": True}],
            routes={"R1": ["E13", "E5", "E7", "E23"]},
            simulation_time=300.0,
        )

        self.assertIn("roads", result)
        self.assertIn("ambulances", result)
        self.assertIn("hospitals", result)
        self.assertIn("routes", result)

        # Roads should have travel_time and congestion from RoadState.
        self.assertIn("E5", result["roads"])
        self.assertEqual(result["roads"]["E5"]["travel_time"], 20.0)
        self.assertEqual(result["roads"]["E5"]["congestion"], "LOW")

        # Blocked edge.
        self.assertIn("E7", result["roads"])
        self.assertTrue(result["roads"]["E7"]["blocked"])

    def test_empty_city_state(self):
        cs = CityState()
        result = adapt_city_state(cs)
        self.assertEqual(result["roads"], {})
        self.assertEqual(result["ambulances"], [])
        self.assertEqual(result["hospitals"], [])
        self.assertEqual(result["routes"], {})

    def test_blocked_edges_propagated(self):
        cs = CityState()
        result = adapt_city_state(cs, blocked_edges={"E7"})
        self.assertTrue(result["roads"]["E7"]["blocked"])


class TestDecisionHandling(unittest.TestCase):
    """Test KEEP / REPLAN / NO_ROUTE decision semantics."""

    def _make_plan(self, route=None, plan_id="P0"):
        return EmergencyPlan(
            ambulance_id="amb0",
            hospital_id="H1",
            route=route or ["E13", "E5", "E7", "E23"],
            eta=30.0,
            plan_id=plan_id,
        )

    def test_keep_decision(self):
        result = ReplanningResult(
            decision=PlannerOutcome.KEEP,
            reason="improvement_below_threshold",
            current_plan=self._make_plan(),
        )
        self.assertEqual(result.decision, PlannerOutcome.KEEP)
        self.assertIsNone(result.proposed_plan)

    def test_replan_decision_has_proposal(self):
        current = self._make_plan()
        proposed = self._make_plan(
            route=["E13", "E5", "E19", "E11"],
            plan_id="P1",
        )
        result = ReplanningResult(
            decision=PlannerOutcome.REPLAN,
            reason="material_improvement_and_timing_satisfied",
            current_plan=current,
            proposed_plan=proposed,
        )
        self.assertEqual(result.decision, PlannerOutcome.REPLAN)
        self.assertIsNotNone(result.proposed_plan)
        self.assertEqual(result.proposed_plan.route, ["E13", "E5", "E19", "E11"])

    def test_no_route_decision(self):
        result = ReplanningResult(
            decision=PlannerOutcome.NO_ROUTE,
            reason="all_candidate_routes_unusable",
            current_plan=self._make_plan(),
        )
        self.assertEqual(result.decision, PlannerOutcome.NO_ROUTE)
        # NO_ROUTE must not invent a route.
        self.assertIsNone(result.proposed_plan)

    def test_planner_outcome_enum(self):
        self.assertEqual(PlannerOutcome.KEEP.value, "KEEP")
        self.assertEqual(PlannerOutcome.REPLAN.value, "REPLAN")
        self.assertEqual(PlannerOutcome.NO_ROUTE.value, "NO_ROUTE")
        self.assertEqual(PlannerOutcome.PLAN_CREATED.value, "PLAN_CREATED")
        self.assertEqual(PlannerOutcome.NO_RESOURCE.value, "NO_RESOURCE")

    def test_signal_action_validation(self):
        """SignalExecutor validates advisory recommendations."""
        from citybrain.core.signal_executor import SignalExecutor

        executor = SignalExecutor()

        # Valid advisory.
        from citybrain.models.agent_result import AdvisoryRecommendation
        rec = AdvisoryRecommendation(
            target="J5", action="REQUEST_SIGNAL_PRIORITY",
            reason="junction_follows_route_edge:E5",
        )
        results = executor.validate_actions([rec])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertTrue(results[0].advisory)
        self.assertFalse(results[0].executed)

    def test_signal_action_invalid(self):
        from citybrain.core.signal_executor import SignalExecutor

        executor = SignalExecutor()
        results = executor.validate_actions([{"target": None, "action": None}])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)


if __name__ == "__main__":
    unittest.main()
