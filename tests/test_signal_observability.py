from types import SimpleNamespace

from citybrain.core.traci_interface import TraCIInterface


def test_signal_clock_fields_derive_from_sumo_switch_time_without_actuation():
    calls=[]
    tls=SimpleNamespace(getPhase=lambda _:2,getRedYellowGreenState=lambda _:'rrG',
        getPhaseDuration=lambda _:30,getNextSwitch=lambda _:112.5)
    traci=SimpleNamespace(trafficlight=tls,simulation=SimpleNamespace(getTime=lambda:100.0))
    traci.trafficlight.setPhase=lambda *args:calls.append(args)
    state=TraCIInterface(traci).signal_state('junction')
    assert state['phase_elapsed_seconds']==17.5
    assert state['remaining_phase_seconds']==12.5
    assert state['phase_start_time']==82.5
    assert calls==[]


def test_missing_signal_timing_is_reported_as_unknown():
    tls=SimpleNamespace(getPhase=lambda _:0,getRedYellowGreenState=lambda _:'r',getPhaseDuration=lambda _:10)
    traci=SimpleNamespace(trafficlight=tls,simulation=SimpleNamespace(getTime=lambda:5))
    state=TraCIInterface(traci).signal_state('junction')
    assert state['phase_start_time'] is None
    assert state['phase_elapsed_seconds'] is None
    assert state['remaining_phase_seconds'] is None
