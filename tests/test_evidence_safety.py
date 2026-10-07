"""Fault injection at the observability boundary; real planner/executor retained."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import citybrain.main as main
from citybrain.integration.evidence import EvidenceWriter
from test_final_runtime import runtime, dispatch, improve


class FailingWriter:
    def __init__(self, actions=None, error=None):
        self.actions = actions
        self.error = error or OSError(28, 'No space left on device')

    def append(self, event):
        if self.actions is None or event['action'] in self.actions:
            raise self.error

    def summary(self, value):
        raise self.error


def synchronized(r, revision):
    assert r.active_plan == r.replanner.active_plan
    assert r.active_plan.revision == revision
    assert r.active_plan.route == r.core.traci.route == r.core.get_active_route('amb')


@pytest.mark.parametrize('revision', [1, 2])
def test_verified_replan_accepts_despite_exact_review_disk_failure(runtime, revision):
    dispatch(runtime)
    if revision == 2:
        runtime.handle_replan_result(improve(runtime))
        runtime.core.city_state.roads['b'].travel_time = 5
        runtime.core.city_state.roads['c'].travel_time = 60
        runtime.core.city_state.simulation_time = 40
    else:
        improve(runtime)
    runtime.writer = FailingWriter({'ROUTE_EXECUTION', 'TERMINAL'})
    # Reproduce through step(), including its exception handling, not just accept().
    runtime.step()
    synchronized(runtime, revision)
    assert runtime.terminal_outcome is None
    failure = next(f for f in runtime.evidence_failures if f['event_type'] == 'ROUTE_EXECUTION')
    assert failure['failure_type'] == 'OSError' and failure['errno'] == 28
    assert failure['physical_execution_attempted'] and failure['physical_execution_verified']
    assert failure['logical_acceptance_completed'] and not failure['cleanup_completed']


@pytest.mark.parametrize('error', [OSError(28, 'No space left on device'),
                                  TypeError('serialization failed'), RuntimeError('writer failed')])
def test_p0_acceptance_survives_writer_errors(runtime, error):
    runtime.writer = FailingWriter(error=error)
    dispatch(runtime)
    synchronized(runtime, 0)
    assert runtime.terminal_outcome is None and runtime.evidence_failures
    assert any(f['event_type'] == 'INITIAL_EXECUTION' and f['logical_acceptance_completed']
               for f in runtime.evidence_failures)


@pytest.mark.parametrize('partial_change', [False, True])
def test_execution_failure_or_rollback_with_broken_evidence_preserves_p0(runtime, partial_change):
    dispatch(runtime); result = improve(runtime)
    before = deepcopy(runtime.active_plan)
    runtime.writer = FailingWriter()
    runtime.core.traci.extra_once = partial_change
    runtime.core.traci.fail = not partial_change
    runtime.handle_replan_result(result)
    synchronized(runtime, 0)
    assert runtime.active_plan == before and result.accepted_plan is None
    assert runtime.terminal_outcome is None
    if partial_change:
        execution = next(e['execution'] for e in runtime.runtime_evidence if e['action'] == 'ROUTE_EXECUTION')
        assert execution['rollback_verified']


@pytest.mark.parametrize('outcome', sorted(main.TERMINAL_OUTCOMES))
def test_all_terminal_cleanup_survives_event_and_summary_failures(runtime, outcome):
    dispatch(runtime); history = deepcopy(runtime.plan_history)
    runtime.writer = FailingWriter()
    runtime._finalize(outcome, 'injected finalization')
    assert runtime.terminal_outcome == outcome
    assert runtime.active_plan is None and runtime.replanner.active_plan is None
    assert not runtime.core.reserved_ambulances and not runtime.core._active_routes
    assert runtime.plan_history == history
    assert {f['event_type'] for f in runtime.evidence_failures} >= {'TERMINAL', 'SUMMARY'}
    assert all(f['cleanup_completed'] for f in runtime.evidence_failures)
    count = len(runtime.runtime_evidence)
    runtime.core.step = MagicMock(side_effect=AssertionError('must not advance'))
    for _ in range(3):
        runtime.step()
        runtime._finalize('ERROR', 'must not replace terminal result')
    assert runtime.terminal_outcome == outcome and len(runtime.runtime_evidence) == count
    runtime.core.step.assert_not_called()


@pytest.mark.parametrize('observed,expected', [('TELEPORTED', 'TELEPORTED'), ('ARRIVED', 'SUCCESS')])
def test_lifecycle_observation_failure_cannot_replace_real_outcome(runtime, observed, expected):
    dispatch(runtime); runtime.writer = FailingWriter()
    if observed == 'ARRIVED':
        vehicle = runtime.core.city_state.vehicles['amb']
        vehicle.edge_id = 'z'; vehicle.route_index = 2
    runtime.core.city_state.terminal_vehicles['amb'] = observed
    runtime.step()
    assert runtime.terminal_outcome == expected
    assert runtime.active_plan is None and not runtime.core.reserved_ambulances
    runtime.core.city_state.terminal_vehicles['amb'] = 'ARRIVED'
    runtime.step()
    assert runtime.terminal_outcome == expected


def test_unreachable_with_broken_writer_still_finalizes_no_route(runtime):
    dispatch(runtime); runtime.writer = FailingWriter()
    runtime.core.city_state.roads['b'].blocked = True
    runtime.core.city_state.roads['c'].blocked = True
    runtime.step()
    assert runtime.terminal_outcome == 'NO_ROUTE'
    assert runtime.active_plan is None and not runtime.core.reserved_ambulances


def test_snapshot_failure_is_nonfatal_and_diagnostics_do_not_recurse(runtime, monkeypatch):
    dispatch(runtime); result = improve(runtime)
    def broken_snapshot(value):
        raise ValueError('cannot serialize evidence')
    monkeypatch.setattr(main, 'snapshot', broken_snapshot)
    runtime.handle_replan_result(result)
    synchronized(runtime, 1)
    runtime._finalize('TIMEOUT', 'horizon')
    assert runtime.terminal_outcome == 'TIMEOUT' and runtime.active_plan is None
    assert not runtime.core.reserved_ambulances
    assert all(f['cleanup_completed'] for f in runtime.evidence_failures)


def test_unavailable_output_directory_retains_diagnostics(monkeypatch, tmp_path):
    def unavailable(path): raise PermissionError(13, 'Permission denied')
    monkeypatch.setattr(main, 'EvidenceWriter', unavailable)
    r = main.CityBrainRuntime(MagicMock(), output=tmp_path/'unavailable')
    assert r.writer is None and r.evidence_failures[0]['event_type'] == 'WRITER_INIT'
    r._finalize('TIMEOUT', 'horizon')
    assert r.evidence_failures[0]['cleanup_completed']


def test_no_overwrite_or_protected_directory_contract_is_preserved(tmp_path):
    with pytest.raises(FileExistsError): main.CityBrainRuntime(MagicMock(), output=tmp_path)
    with pytest.raises(ValueError):
        main.CityBrainRuntime(MagicMock(), output=Path('experiments/results/forbidden-hotfix'))


def test_summary_only_failure_occurs_after_cleanup(runtime, tmp_path):
    runtime.writer = EvidenceWriter(tmp_path/'evidence'); dispatch(runtime)
    runtime.writer.summary = FailingWriter().summary
    runtime._finalize('TIMEOUT', 'horizon')
    assert runtime.active_plan is None and not runtime.core.reserved_ambulances
    assert runtime.evidence_failures[-1]['event_type'] == 'SUMMARY'
    assert runtime.evidence_failures[-1]['cleanup_completed']
    terminal = json.loads(runtime.writer.events.read_text().splitlines()[-1])
    assert terminal['action'] == 'TERMINAL' and terminal['active_plan'] is None
    assert terminal['last_accepted_plan']['revision'] == 0


def test_verifier_checks_survive_optimized_python(tmp_path):
    (tmp_path/'smokes.json').write_text('[]')
    result = subprocess.run([sys.executable, '-O', '-m', 'citybrain.integration.verify', str(tmp_path)],
        capture_output=True, text=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    assert result.returncode != 0 and 'No smoke results to verify' in result.stderr


def test_smoke_persists_failed_result_and_returns_nonzero(monkeypatch, tmp_path):
    from citybrain.integration import smoke
    import experiments.runners.compare as compare
    monkeypatch.setattr(compare, 'prepare_config', lambda *args: 'unused')
    failed = SimpleNamespace(active_plan=None, replanner=SimpleNamespace(active_plan=None),
        core=SimpleNamespace(_active_routes={}, reserved_ambulances=set()),
        summary=lambda: dict(terminal_outcome='ERROR', evidence_failures=[], accepted_plans=[], route_changes=0))
    monkeypatch.setattr(smoke, 'run', lambda *args, **kwargs: failed)
    monkeypatch.setattr(sys, 'argv', ['smoke', '--scenarios', 'S05', '--output', str(tmp_path/'smoke')])
    with pytest.raises(SystemExit, match='expected SUCCESS'): smoke.main()
    assert json.loads((tmp_path/'smoke/smokes.json').read_text())[0]['terminal_outcome'] == 'ERROR'


def test_failed_initial_execution_with_broken_writer_never_activates(runtime):
    from citybrain.models.emergency import Emergency
    runtime.core.traci.fail = True
    runtime.writer = FailingWriter()
    result = runtime.create_emergency_plan(Emergency('EM', 'J0', 'HIGH', 'MEDICAL'))
    assert not result.success and runtime.terminal_outcome == 'EXECUTION_FAILED'
    assert runtime.active_plan is None and runtime.plan_history == []
    assert not runtime.core._active_routes and not runtime.core.reserved_ambulances


def test_failed_physical_recovery_with_broken_writer_finalizes(runtime):
    dispatch(runtime); result = improve(runtime)
    original = runtime.core.traci.apply_route
    def corrupt_then_fail_restore(vehicle, route):
        if route == ['a', 'b', 'z']:
            raise RuntimeError('restoration unavailable')
        original(vehicle, route)
        runtime.core.traci.route.append('wrong_destination')
    runtime.core.traci.apply_route = corrupt_then_fail_restore
    runtime.writer = FailingWriter()
    runtime.handle_replan_result(result)
    assert result.accepted_plan is None
    assert runtime.terminal_outcome == 'EXECUTION_FAILED'
    assert runtime.active_plan is None and runtime.replanner.active_plan is None
    assert runtime.plan_history[-1].revision == 0
    assert not runtime.core.reserved_ambulances and not runtime.core._active_routes
