from datetime import datetime, timezone

import pytest

from citybrain.chennai.traffic.evaluation import (TrafficEvaluationConfig, advisory_route_recommendation,
    evaluate_candidates, validate_evidence)

NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


def observation(**updates):
    row = dict(provider='FIXTURE', observation_id='obs-1', provider_segment_id='seg-1',
        road_geometry=((80.1500, 12.8400), (80.1510, 12.8400)), direction='FORWARD',
        retrieved_at=NOW, source_type='MOCKED_PROVIDER', current_speed=5.0, free_flow_speed=10.0,
        observation_timestamp=NOW, freshness_status='FRESH', matching_status='MATCHED',
        matched_sumo_edges=('edge-a',), matching_confidence=.95, matching_coverage=.99)
    row.update(updates)
    return row


def test_disabled_is_baseline_and_records_no_used_evidence():
    result = evaluate_candidates({'fast':['edge-a'], 'other':['edge-b']}, {'fast':10,'other':11}, [observation()], NOW)
    assert result['adjusted_scores'] == result['baseline_scores']
    assert result['selected_candidate'] == 'fast'
    assert result['evidence'][0]['rejection_reason'] == 'FEATURE_DISABLED'
    assert result['canonical_measurements_modified'] is False
    assert result['planner_invoked'] is False and result['route_committed'] is False


def test_enabled_fresh_high_confidence_observation_adjusts_only_sidecar_cost():
    result = evaluate_candidates({'fast':['edge-a'],'safe':['edge-b']}, {'fast':10,'safe':11}, [observation()], NOW,
        TrafficEvaluationConfig(enabled=True))
    assert result['evidence'][0]['accepted'] is True
    assert result['adjusted_scores']['fast'] > result['baseline_scores']['fast']
    assert result['selected_candidate'] == 'safe'
    assert result['evidence_used_by_candidate']['fast'] == ['obs-1']
    assert result['planner_invoked'] is False and result['route_committed'] is False


@pytest.mark.parametrize(('changes','reason'), [
    ({'freshness_status':'STALE'},'OBSERVATION_NOT_FRESH'),
    ({'matching_status':'UNMATCHED','matched_sumo_edges':()},'ROAD_MATCH_NOT_VERIFIED'),
    ({'matching_status':'AMBIGUOUS','matched_sumo_edges':()},'ROAD_MATCH_NOT_VERIFIED'),
    ({'direction':'UNKNOWN'},'UNKNOWN_OR_UNSUPPORTED_DIRECTION'),
    ({'direction':'REVERSE'},'UNKNOWN_OR_UNSUPPORTED_DIRECTION'),
    ({'matching_confidence':.79},'LOW_MATCH_CONFIDENCE'),
    ({'matching_coverage':.94},'INSUFFICIENT_GEOGRAPHIC_COVERAGE'),
    ({'observation_timestamp':None},'UNKNOWN_SOURCE_TIME'),
    ({'observation_timestamp':NOW.replace(year=2027)},'FUTURE_SOURCE_TIME'),
    ({'observation_timestamp':NOW.replace(day=17)},'OBSERVATION_NOT_FRESH'),
    ({'retrieved_at':None},'INVALID_RETRIEVAL_TIME'),
    ({'current_speed':None},'MISSING_OR_INVALID_SPEED'),
    ({'source_type':'UNTRUSTED'},'UNSUPPORTED_PROVENANCE'),
])
def test_ineligible_observations_never_adjust_routes(changes, reason):
    result = evaluate_candidates({'r':['edge-a']}, {'r':7}, [observation(**changes)], NOW,
        TrafficEvaluationConfig(enabled=True))
    assert result['evidence'][0]['accepted'] is False
    assert result['evidence'][0]['rejection_reason'] == reason
    assert result['adjusted_scores'] == {'r':7.0}


def test_opposite_or_disconnected_matches_are_rejected():
    rows = [observation(observation_id='opposite',matching_status='UNMATCHED',matched_sumo_edges=()),
            observation(observation_id='fragment',matching_status='INSUFFICIENT_DATA',matched_sumo_edges=())]
    result = evaluate_candidates({'r':['edge-a']}, {'r':1}, rows, NOW, TrafficEvaluationConfig(enabled=True))
    assert [row['rejection_reason'] for row in result['evidence']] == ['ROAD_MATCH_NOT_VERIFIED']*2


def test_conflicting_provider_estimates_exclude_edge():
    result = evaluate_candidates({'r':['edge-a']}, {'r':1},
        [observation(observation_id='slow',current_speed=2), observation(observation_id='fast',current_speed=9)], NOW,
        TrafficEvaluationConfig(enabled=True))
    assert result['conflicting_edges'] == {'edge-a':'CONFLICTING_PROVIDER_ESTIMATES'}
    assert result['adjusted_scores'] == {'r':1.0}


def test_malformed_geometry_is_quarantined_without_exception():
    result=evaluate_candidates({'r':['edge-a']},{'r':1},
        [observation(road_geometry=((None,12.84),(80.15,12.84)))],NOW,TrafficEvaluationConfig(enabled=True))
    assert result['evidence'][0]['rejection_reason']=='MISSING_GEOMETRY'
    assert result['adjusted_scores']=={'r':1.0}


def test_adjustments_are_bounded_and_duplicate_route_edges_count_once():
    result = evaluate_candidates({'r':['edge-a','edge-a']}, {'r':0},
        [observation(current_speed=.01,free_flow_speed=100)], NOW,
        TrafficEvaluationConfig(enabled=True,maximum_edge_adjustment_seconds=4,maximum_route_adjustment_seconds=3))
    assert result['adjustments']['r'] == 3


def test_invalid_configuration_and_naive_clock_are_rejected():
    with pytest.raises(ValueError):
        TrafficEvaluationConfig(enabled=True,maximum_route_adjustment_seconds=float('inf'))
    with pytest.raises(ValueError):
        validate_evidence(observation(),datetime(2026,10,18),TrafficEvaluationConfig(enabled=True))


def route_evaluation(config=None):
    config = config or TrafficEvaluationConfig(enabled=True)
    routes = {'current':['edge-current'], 'alternate':['edge-a']}
    result = evaluate_candidates(routes, {'current':40,'alternate':20},
        [observation()], NOW, config)
    topology = {'edge-current':set(), 'edge-a':set()}
    return result, routes, topology, config


def test_opt_in_advisor_recommends_only_connected_route_with_eligible_evidence():
    result, routes, topology, config = route_evaluation()
    decision = advisory_route_recommendation(result, routes, 'current', NOW,
        edge_successors=topology, current_route_active_since=NOW.replace(hour=11,minute=30), config=config)
    assert decision['action']=='ADVISORY_RECOMMENDATION'
    assert decision['candidate']=='alternate'
    assert decision['reason']=='ELIGIBLE_EXPERIMENTAL_EVIDENCE'
    assert decision['planner_invoked'] is False and decision['route_committed'] is False


@pytest.mark.parametrize(('kwargs','reason'), [
    ({'current_route_active_since':None},'COMMITMENT_START_UNKNOWN'),
    ({'current_route_active_since':NOW},'COMMITMENT_PENDING'),
    ({'current_route_active_since':NOW.replace(hour=11,minute=30), 'last_route_change_at':NOW},'COOLDOWN_PENDING'),
    ({'current_route_active_since':NOW.replace(hour=11,minute=30), 'recent_route_ids':['alternate']},'RECENT_ROUTE_OSCILLATION'),
])
def test_opt_in_advisor_holds_for_commitment_cooldown_and_oscillation(kwargs,reason):
    result, routes, topology, config = route_evaluation()
    kwargs.setdefault('current_route_active_since',NOW.replace(hour=11,minute=30))
    decision=advisory_route_recommendation(result,routes,'current',NOW,
        edge_successors=topology,config=config,**kwargs)
    assert decision['action']=='KEEP' and decision['reason']==reason


def test_opt_in_advisor_rejects_disconnected_alternative_and_insufficient_improvement():
    result, routes, topology, config = route_evaluation()
    routes['alternate']=['edge-a','edge-not-connected']
    topology['edge-not-connected']=set()
    decision=advisory_route_recommendation(result,routes,'current',NOW,
        edge_successors=topology,current_route_active_since=NOW.replace(hour=11,minute=30),config=config)
    assert decision['action']=='KEEP'
    assert decision['candidate_rejections']['alternate']=='DISCONNECTED_ROUTE'
    routes={'current':['edge-current'],'alternate':['edge-a']}
    small=TrafficEvaluationConfig(enabled=True,minimum_improvement_seconds=100)
    result=evaluate_candidates(routes,{'current':40,'alternate':20},[observation()],NOW,small)
    decision=advisory_route_recommendation(result,routes,'current',NOW,
        edge_successors=topology,current_route_active_since=NOW.replace(hour=11,minute=30),config=small)
    assert decision['action']=='KEEP' and decision['reason']=='INSUFFICIENT_IMPROVEMENT'


def test_advisor_is_disabled_by_default_and_connectivity_is_fail_closed():
    result,routes,topology,_=route_evaluation()
    decision=advisory_route_recommendation(result,routes,'current',NOW,
        edge_successors=topology,current_route_active_since=NOW.replace(hour=11,minute=30))
    assert decision['reason']=='FEATURE_DISABLED'
    decision=advisory_route_recommendation(result,routes,'current',NOW,
        edge_successors={},current_route_active_since=NOW.replace(hour=11,minute=30),
        config=TrafficEvaluationConfig(enabled=True))
    assert decision['action']=='NO_ROUTE' and decision['reason']=='CURRENT_ROUTE_UNVERIFIED'
