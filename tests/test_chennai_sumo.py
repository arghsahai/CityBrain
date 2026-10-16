"""Actual SUMO startup, signal observation and fail-closed Chennai execution."""
import shutil

import pytest
import sumolib
import traci

from citybrain.chennai.scenario import prepare
from citybrain.chennai.telemetry import observe
from citybrain.main import CityBrainRuntime, RuntimeConfig
from citybrain.chennai.stability import ChennaiRuntime
from citybrain.models.emergency import Emergency


@pytest.mark.skipif(not shutil.which('sumo'), reason='SUMO executable unavailable')
@pytest.mark.parametrize('runtime_class',[CityBrainRuntime,ChennaiRuntime])
@pytest.mark.parametrize('closure',['destination','divertible_edge'])
def test_chennai_dispatch_then_road_closure(tmp_path,runtime_class,closure):
    cfg, metadata = prepare(tmp_path/'inputs')
    label='chennai-pytest'
    traci.start([sumolib.checkBinary('sumo'),'-c',str(cfg),'--no-step-log','true',
                 '--end','150','--xml-validation','never'],label=label)
    connection=traci.getConnection(label)
    runtime=runtime_class(connection,metadata['routes'],[metadata['hospital']],
        config=RuntimeConfig(horizon=150),output=tmp_path/'runtime')
    signal_states={}
    observations=[]
    try:
        runtime.core.refresh_state()
        for _ in range(110):
            state,_,_=runtime.step()
            frame=observe(runtime,metadata['hospitals'])
            observations.append(frame)
            for signal in frame['signals']:
                signal_states.setdefault(signal['signal_id'],set()).add(signal['state'])
            if not runtime.emergency and any(v.vehicle_type=='ambulance' for v in state.vehicles.values()):
                runtime.create_emergency_plan(Emergency('TEST-CHENNAI',metadata['origin_edge'],'HIGH','ROAD_ACCIDENT'))
            if runtime.active_plan:
                break
        assert runtime.active_plan is not None
        executions=[e for e in runtime.runtime_evidence if e['action']=='INITIAL_EXECUTION']
        assert executions[-1]['execution']['verification']=='VERIFIED'
        assert executions[-1]['execution']['observed_suffix']==runtime.active_plan.route
        assert any(len(frame['vehicles'])>10 for frame in observations)
        assert all(len(states)>1 for states in signal_states.values())
        ambulance_id=runtime.ambulance_id
        if closure=='destination':
            runtime.step(blocked_edges=[metadata['hospital']['destination_edge']])
            assert runtime.terminal_outcome=='NO_ROUTE'
            assert runtime.arrival_time is None
            assert runtime.active_plan is None
            assert runtime.core.get_active_route(ambulance_id) is None
            assert ambulance_id not in runtime.core.reserved_ambulances
        else:
            position=runtime.core.traci.route_position(ambulance_id)
            candidates=[p for p in metadata['routes'].values() if position['edge'] in p]
            target=next(edge for edge in runtime.active_plan.route[2:-1]
                        if any(edge not in path for path in candidates))
            # A physical emergency-vehicle restriction and explicit Core closure
            # flag are scenario input, not inferred from a queued vehicle.
            for index in range(connection.edge.getLaneNumber(target)):
                connection.lane.setDisallowed(f'{target}_{index}',['emergency'])
            for _ in range(10):
                runtime.step(blocked_edges=[target])
                if runtime.applied_replans or runtime.terminal_outcome:
                    break
            assert runtime.terminal_outcome is None
            assert runtime.applied_replans==1
            assert target not in runtime.active_plan.route
            assert list(connection.vehicle.getRoute(ambulance_id)) == runtime.active_plan.route
            execution=next(e['execution'] for e in reversed(runtime.runtime_evidence) if e['action']=='ROUTE_EXECUTION')
            assert execution['verification']=='VERIFIED'
            if runtime_class is ChennaiRuntime:
                decision=next(e for e in reversed(runtime.runtime_evidence) if e['action']=='STABILITY_DECISION')
                assert decision['stability']['outcome']=='HARD_FAILURE_BYPASS'
    finally:
        connection.close()


@pytest.mark.parametrize('profile',['HEAVY','PEAK'])
@pytest.mark.skipif(not shutil.which('sumo'), reason='SUMO executable unavailable')
def test_demand_profile_starts_in_actual_sumo(tmp_path,profile):
    cfg,_=prepare(tmp_path/'inputs',profile)
    label='chennai-'+profile
    traci.start([sumolib.checkBinary('sumo'),'-c',str(cfg),'--no-step-log','true',
                 '--end','10','--xml-validation','never'],label=label)
    connection=traci.getConnection(label)
    try:
        for _ in range(6):connection.simulationStep()
        assert len(connection.vehicle.getIDList())>=5
        assert connection.trafficlight.getIDList()
        assert any(connection.vehicle.getSpeed(v)>0 for v in connection.vehicle.getIDList())
    finally:
        connection.close()
