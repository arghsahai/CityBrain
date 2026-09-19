from types import SimpleNamespace

from citybrain.agents.ambulance_agent import AmbulanceAgent
from citybrain.agents.hospital_agent import HospitalAgent
from citybrain.agents.police_agent import PoliceAgent
from citybrain.agents.signal_agent import SignalAgent
from citybrain.agents.traffic_agent import TrafficAgent


def test_traffic_agent_structures_every_supplied_road():
    result = TrafficAgent().assess({"roads": {
        "low": {"congestion": "LOW"},
        "medium": {"congestion": "MEDIUM"},
        "high": {"congestion": "HIGH"},
        "unknown": {"congestion": "UNKNOWN"},
    }})
    assert [item.road_id for item in result.assessments] == [
        "low", "medium", "high", "unknown",
    ]
    assert result.assessments[-1].assessment == "UNKNOWN"
    assert result.recommendations == ["Use an alternative route instead of high"]


def test_ambulance_agent_structured_success_and_no_resource():
    agent = AmbulanceAgent()
    state = {"ambulances": [
        {"id": "busy", "available": False},
        {"id": "ready", "available": True, "edge": "e1"},
    ]}
    selected = agent.select(None, state)
    assert selected.success and selected.selected["id"] == "ready"
    assert agent.select(None, {"ambulances": []}).reason == "no_available_ambulance"


def test_ambulance_agent_does_not_invent_availability():
    result = AmbulanceAgent().select(None, {"ambulances": [{"id": "a"}]})
    assert not result.success and result.selected is None


def test_hospital_agent_structured_success_and_no_resource():
    agent = HospitalAgent()
    state = {"hospitals": [
        {"id": "full", "icu_available": False},
        {"id": "open", "icu_available": True},
    ]}
    selected = agent.select(None, state)
    assert selected.success and selected.selected["id"] == "open"
    assert agent.select(None, {"hospitals": []}).reason == "no_suitable_hospital"


def test_hospital_agent_does_not_invent_icu_capacity():
    result = HospitalAgent().select(None, {"hospitals": [{"id": "h"}]})
    assert not result.success and result.selected is None


def test_signal_agent_output_is_explicitly_advisory():
    result = SignalAgent().recommend(
        ["e1", "e2"], {"roads": {"e1": {"to": "j2"}, "e2": {"to": "j3"}}},
    )
    assert result.advisory_only
    assert [item.target for item in result.recommendations] == ["j2", "j3"]
    assert all(item.action == "REQUEST_SIGNAL_PRIORITY" for item in result.recommendations)


def test_police_agent_output_is_logical_advice_only():
    emergency = SimpleNamespace(emergency_id="incident", location="j5")
    result = PoliceAgent().recommend(emergency)
    assert result.advisory_only
    assert result.recommendations[0].target == "j5"
    assert result.recommendations[0].action == "ACCIDENT_RESPONSE_REQUIRED"


def test_legacy_agent_interfaces_are_preserved():
    emergency = SimpleNamespace(emergency_id="incident", location="j5")
    state = {
        "roads": {"e": {"congestion": "HIGH", "to": "j"}},
        "ambulances": [{"id": "a", "available": True}],
        "hospitals": [{"id": "h", "icu_available": True}],
    }
    assert TrafficAgent().run(state) == ["Use an alternative route instead of e"]
    assert AmbulanceAgent().run(emergency, state)["id"] == "a"
    assert HospitalAgent().run(emergency, state)["id"] == "h"
    assert SignalAgent().run(["e"], state) == ["j"]
    assert PoliceAgent().run(emergency)["action"] == "ACCIDENT_RESPONSE_REQUIRED"
