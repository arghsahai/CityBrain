"""Observation-only S08 evidence; never choose or apply a route here."""
import copy
import math

INCIDENT_EDGES = ('E7', 'E11')


class ScoreRecorder:
    """Wrap the team's scorer to capture actual calls without changing scores."""
    def __init__(self, scorer):
        self.scorer = scorer
        self.records = []

    def calculate_score(self, route, state):
        score = self.scorer.calculate_score(route, state)
        self.records.append(dict(route=list(route), score=score, valid=math.isfinite(score)))
        return score


class S08Audit:
    def __init__(self):
        self.reference = None
        self.detected = []
        self.candidate_evaluations = 0

    def observe_changes(self, now, roads):
        """Latch each declared incident edge's first deterioration vs dispatch state.

        This is an observational definition, not a new replanning trigger.
        Both strategies receive identical monitoring. Finite increases must
        exceed max(5 s, 15%); a newly blocked/non-finite edge also qualifies.
        """
        if self.reference is None:
            self.reference = copy.deepcopy(roads)
            return []
        events = []
        for edge in INCIDENT_EDGES:
            if edge in self.detected:
                continue
            before, after = self.reference[edge], roads[edge]
            old, new = before['travel_time'], after['travel_time']
            threshold = max(5, old * .15)
            changed = (after['blocked'] and not before['blocked']) or (
                math.isfinite(old) and (not math.isfinite(new) or new-old >= threshold))
            if changed:
                self.detected.append(edge)
                events.append(dict(kind='MEANINGFUL_ENVIRONMENT_CHANGE', time=now,
                    edge=edge, change_ordinal=len(self.detected), reference=copy.deepcopy(before),
                    observed=copy.deepcopy(after), threshold_seconds=threshold,
                    definition='first incident-edge deterioration versus dispatch observation'))
        return events


def decision_reason(candidate, current, invalid, benefit, threshold, elapsed):
    if candidate is None:
        return 'no_valid_reachable_candidate'
    if candidate.route == current:
        return 'candidate_matches_active_route'
    if invalid:
        return 'active_route_blocked'
    if benefit < threshold:
        return 'predicted_benefit_below_threshold'
    if elapsed < 10:
        return 'minimum_commitment_not_elapsed'
    return 'material_benefit_and_commitment_satisfied'


def validate_evidence(row, events):
    """Check evidence against the checkpoint, not desired research outcomes."""
    checks = [e for e in events if e.get('kind') == 'EVALUATION']
    applied = [e for e in checks if e.get('decision') == 'APPLY']
    if row['strategy'] == 'static' and (checks or applied or row['replan_checks'] or row['successful_route_changes']):
        raise ValueError('Static strategy contains CityBrain replanning')
    if row['completion_status'] == 'ERROR':
        return  # Partial evidence remains available; no complete-trip claim.
    if len(checks) != row['replan_checks'] or len(applied) != row['successful_route_changes']:
        raise ValueError('Route-change/check counts disagree with decision evidence')
    if sum(len(e['candidate_evaluations']) for e in checks) != row['candidate_evaluations']:
        raise ValueError('Candidate count disagrees with recorded scorer calls')
    for event in applied:
        if not event['gate_passed'] or event['application']['remaining_route_after'] != event['candidate_route']:
            raise ValueError('Applied route lacks a passed gate and matching TraCI read-back')
        application = event['application']
        if application['route_after'][application['route_index_after']:] != application['remaining_route_after']:
            raise ValueError('Full SUMO route and remaining suffix disagree')
        if event['physical_edge'] != event['candidate_route'][0] or event['distance_travelled_m'] <= 0:
            raise ValueError('Applied route is not grounded in a dispatched, travelling ambulance')
        if any(event['observed_roads'][edge]['blocked'] for edge in event['candidate_route']):
            raise ValueError('Applied route contains an observed blocked edge')
        if not event['current_route_invalid'] and event['predicted_benefit'] < event['threshold_seconds']:
            raise ValueError('Applied route does not meet the declared benefit threshold')
        if event['application']['time'] != event['time']:
            raise ValueError('Application time disagrees with decision time')
