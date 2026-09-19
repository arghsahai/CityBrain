"""Adapter contracts tested without SUMO or changes to canonical classes."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from citybrain.agents.ambulance_agent import AmbulanceAgent
from citybrain.agents.hospital_agent import HospitalAgent
from citybrain.agents.signal_agent import SignalAgent
from citybrain.agents.traffic_agent import TrafficAgent
from citybrain.core.city_state import CityState
from citybrain.core.vehicle_state import VehicleState
from citybrain.models.emergency import Emergency
from citybrain.perception import adapt_city_state
from citybrain.planner.emergency_planner import EmergencyPlanner
from citybrain.planner.plan_validator import PlanValidator
from citybrain.planner.route_scorer import RouteScorer


@pytest.fixture
def city():
    state = CityState()
    state.update_vehicle(VehicleState("V1", "E1", 7.25, (1.5, 2.5), "E1_0", -0.75))
    return state


@pytest.fixture
def road():
    # Structural stand-in for Argh's remote RoadState, absent on this branch.
    return SimpleNamespace(
        road_id="E1", vehicle_count=2, average_speed=7.25,
        road_length=100.0, speed_limit=13.9, lane_count=1,
        occupancy=12.5, travel_time=14.0, congestion="HIGH",
    )


@pytest.mark.parametrize("field,expected", [
    ("id", "V1"), ("speed", 7.25), ("acceleration", -0.75),
    ("position", (1.5, 2.5)), ("lane", "E1_0"), ("edge", "E1"),
])
def test_vehicle_measurements(city, field, expected):
    assert adapt_city_state(city)["vehicles"]["V1"][field] == expected


def test_all_canonical_road_fields(road):
    state = adapt_city_state(SimpleNamespace(roads={"E1": road}))
    assert state["roads"]["E1"] == vars(road)


@pytest.mark.parametrize("congestion", ["LOW", "MEDIUM", "HIGH", "NO_TRAFFIC", "UNKNOWN"])
def test_congestion_is_not_reinterpreted(road, congestion):
    road.congestion = congestion
    assert adapt_city_state(SimpleNamespace(roads={"E1": road}))["roads"]["E1"]["congestion"] == congestion


@pytest.mark.parametrize("travel_time", [0, 14.0, float("inf")])
def test_travel_time_is_not_reinterpreted(road, travel_time):
    road.travel_time = travel_time
    assert adapt_city_state(SimpleNamespace(roads={"E1": road}))["roads"]["E1"]["travel_time"] == travel_time


def test_explicit_blockage_including_unmeasured_edge(road):
    state = adapt_city_state(SimpleNamespace(roads={"E1": road}), blocked_edges=["E1", "missing"])
    assert state["roads"]["E1"]["blocked"] is True
    assert state["roads"]["missing"] == {"blocked": True}


@pytest.mark.parametrize("blocked_edges", [None, []])
def test_no_inferred_blockage(road, blocked_edges):
    road.average_speed = 0
    road.travel_time = float("inf")
    state = adapt_city_state(SimpleNamespace(roads={"E1": road}), blocked_edges=blocked_edges)
    assert "blocked" not in state["roads"]["E1"]


def test_topology_only_copies_endpoints(road):
    state = adapt_city_state(
        SimpleNamespace(roads={"E1": road}),
        road_topology={"E1": {"from": "J1", "to": "J2", "travel_time": 999},
                       "E2": {"to": "J3"}},
    )
    assert state["roads"]["E1"]["from"] == "J1"
    assert state["roads"]["E1"]["to"] == "J2"
    assert state["roads"]["E1"]["travel_time"] == 14.0
    assert state["roads"]["E2"] == {"to": "J3"}


@pytest.mark.parametrize("source", [None, SimpleNamespace(), SimpleNamespace(vehicles=None, roads=None), CityState()])
def test_missing_optional_state(source):
    assert adapt_city_state(source) == {
        "simulation_time": None, "vehicles": {}, "roads": {},
        "ambulances": [], "hospitals": [], "routes": {},
    }


def test_partial_measurements_are_not_fabricated():
    state = adapt_city_state(SimpleNamespace(
        roads={"E1": SimpleNamespace(road_id="E1")},
        vehicles={"V1": SimpleNamespace(vehicle_id="V1")},
    ))
    assert state["roads"] == {"E1": {"road_id": "E1"}}
    assert state["vehicles"] == {"V1": {"id": "V1"}}


def test_context_preserved_and_missing_route_measurements_allowed(city):
    ambulances = [{"id": "AMB_1", "available": False}]
    hospitals = [{"id": "H1", "capabilities": ["ICU"]}]
    routes = {"R1": ["unmeasured"]}
    state = adapt_city_state(city, ambulances=ambulances, hospitals=hospitals,
                            routes=routes, simulation_time=0)
    assert state["ambulances"] == ambulances
    assert state["hospitals"] == hospitals
    assert state["routes"] == routes
    assert state["roads"] == {}
    assert state["simulation_time"] == 0
    assert "icu_available" not in state["hospitals"][0]
    assert adapt_city_state(city)["ambulances"] == []


def test_source_and_context_remain_independent(city, road):
    city.roads = {"E1": road}
    context = {
        "ambulances": [{"id": "A1", "metadata": {"tags": ["supplied"]}}],
        "hospitals": [{"id": "H1", "capabilities": ["ICU"]}],
        "routes": {"R1": ["E1"]}, "blocked_edges": ["E1"],
        "road_topology": {"E1": {"from": "J1", "to": "J2"}},
    }
    before_city, before_context = deepcopy(vars(city)), deepcopy(context)
    state = adapt_city_state(city, **context)
    assert vars(city) == before_city
    assert context == before_context
    state["vehicles"]["V1"]["speed"] = 999
    state["roads"]["E1"]["travel_time"] = 999
    state["roads"]["E1"]["to"] = "changed"
    state["ambulances"][0]["metadata"]["tags"].append("changed")
    state["hospitals"][0]["capabilities"].clear()
    state["routes"]["R1"].append("changed")
    assert vars(city) == before_city
    assert context == before_context
    road.congestion = "LOW"
    assert state["roads"]["E1"]["congestion"] == "HIGH"


def test_existing_agents_and_planner_consume_snapshot(city, road):
    city.roads = {"E1": road}
    emergency = Emergency("ACC1", "J1", "HIGH", "ACCIDENT")
    state = adapt_city_state(
        city, ambulances=[{"id": "V1", "available": True}],
        hospitals=[{"id": "H1", "icu_available": True}],
        routes={"R1": ["E1"]}, road_topology={"E1": {"to": "J2"}},
        simulation_time=12.5,
    )
    assert state["simulation_time"] == 12.5
    assert TrafficAgent().run(state) == ["Use an alternative route instead of E1"]
    assert AmbulanceAgent().run(emergency, state)["id"] == "V1"
    assert HospitalAgent().run(emergency, state)["id"] == "H1"
    assert SignalAgent().run(["E1"], state) == ["J2"]
    plan = EmergencyPlanner().create_plan(emergency, state)
    assert (plan.ambulance_id, plan.hospital_id, plan.route, plan.eta, plan.signal_priority) == (
        "V1", "H1", ["E1"], 14.0, ["J2"],
    )
    assert PlanValidator().validate(plan, state)
    blocked = adapt_city_state(city, blocked_edges=["E1"])
    assert not PlanValidator().validate(plan, blocked)
    assert RouteScorer().calculate_score(["E1"], blocked) == float("inf")


def test_import_and_adaptation_without_traci_or_sumo():
    # Fresh interpreter ensures an already-cached import cannot mask a dependency.
    code = '''
import sys
class NoTraci:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] == "traci":
            raise AssertionError("TraCI import attempted")
sys.meta_path.insert(0, NoTraci())
from citybrain.core.city_state import CityState
from citybrain.perception import adapt_city_state
assert adapt_city_state(CityState())["vehicles"] == {}
assert "traci" not in sys.modules
'''
    result = subprocess.run([sys.executable, "-B", "-c", code],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
