"""Opt-in advisory route evaluation. Never changes canonical state or executes routes."""
from dataclasses import dataclass
from datetime import datetime
import math
from .freshness import FreshnessPolicy


@dataclass(frozen=True)
class TrafficEvaluationConfig:
    enabled: bool = False
    minimum_confidence: float = 0.8
    minimum_coverage: float = 0.95
    maximum_edge_adjustment_seconds: float = 30.0
    maximum_route_adjustment_seconds: float = 60.0
    conflict_relative_spread: float = 0.5
    minimum_improvement_seconds: float = 5.0
    minimum_improvement_ratio: float = 0.05
    minimum_commitment_seconds: float = 20.0
    cooldown_seconds: float = 60.0

    def __post_init__(self):
        for name in ('minimum_confidence', 'minimum_coverage', 'conflict_relative_spread'):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'{name} must be between zero and one')
        for name in ('maximum_edge_adjustment_seconds', 'maximum_route_adjustment_seconds'):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f'{name} must be finite and nonnegative')
        for name in ('minimum_improvement_seconds', 'minimum_commitment_seconds', 'cooldown_seconds'):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f'{name} must be finite and nonnegative')
        value = self.minimum_improvement_ratio
        if isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('minimum_improvement_ratio must be between zero and one')


@dataclass(frozen=True)
class ExternalTrafficEvidence:
    provider: str
    observation_id: str
    matched_edges: tuple
    direction: str
    estimated_speed_mps: float | None
    free_flow_speed_mps: float | None
    source_timestamp: datetime | None
    retrieved_timestamp: datetime | None
    freshness: str
    match_confidence: float | None
    provenance: str
    uncertainty: tuple[str, ...]
    rejection_reason: str | None
    coverage: float | None


def _aware(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _get(row, key, default=None):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def _time(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return value if _aware(value) else None


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def validate_evidence(observation, now, config=TrafficEvaluationConfig()):
    """Normalize evidence and assign a fail-closed rejection reason."""
    if not _aware(now):
        raise ValueError('evaluation time must be timezone-aware')
    source = _time(_get(observation, 'observation_timestamp'))
    retrieved = _time(_get(observation, 'retrieved_at'))
    confidence, coverage = _get(observation, 'matching_confidence'), _get(observation, 'matching_coverage')
    edges = tuple(_get(observation, 'matched_sumo_edges', ()) or ())
    speed, free = _get(observation, 'current_speed'), _get(observation, 'free_flow_speed')
    provenance = _get(observation, 'source_type', _get(observation, 'provenance', 'UNKNOWN'))
    claimed_freshness, direction = _get(observation, 'freshness_status', 'UNKNOWN'), _get(observation, 'direction', 'UNKNOWN')
    freshness = FreshnessPolicy().classify(source, now)[0]
    if provenance not in {'HERE_LIVE', 'TOMTOM_LIVE', 'REPLAY', 'SYNTHETIC_SAMPLE', 'MOCKED_PROVIDER'}:
        reason = 'UNSUPPORTED_PROVENANCE'
    elif source is None:
        reason = 'UNKNOWN_SOURCE_TIME'
    elif freshness == 'UNKNOWN' and source > now:
        reason = 'FUTURE_SOURCE_TIME'
    elif freshness != 'FRESH' or claimed_freshness != 'FRESH':
        reason = 'OBSERVATION_NOT_FRESH'
    elif retrieved is None:
        reason = 'INVALID_RETRIEVAL_TIME'
    elif direction != 'FORWARD':
        reason = 'UNKNOWN_OR_UNSUPPORTED_DIRECTION'
    elif _get(observation, 'matching_status') != 'MATCHED' or not edges:
        reason = 'ROAD_MATCH_NOT_VERIFIED'
    elif not _number(confidence) or confidence < config.minimum_confidence:
        reason = 'LOW_MATCH_CONFIDENCE'
    elif not _number(coverage) or coverage < config.minimum_coverage:
        reason = 'INSUFFICIENT_GEOGRAPHIC_COVERAGE'
    elif not _number(speed) or speed <= 0 or not _number(free) or free <= 0:
        reason = 'MISSING_OR_INVALID_SPEED'
    else:
        reason = None
    uncertainty = []
    if source is None:
        uncertainty.append('SOURCE_TIME_UNKNOWN')
    if direction == 'UNKNOWN':
        uncertainty.append('DIRECTION_UNKNOWN')
    if freshness in {'STALE', 'EXPIRED', 'UNKNOWN'}:
        uncertainty.append('FRESHNESS_' + freshness)
    return ExternalTrafficEvidence(str(_get(observation, 'provider', 'UNKNOWN')),
        str(_get(observation, 'observation_id', 'UNKNOWN')), edges, str(direction),
        speed if _number(speed) else None, free if _number(free) else None, source, retrieved,
        str(freshness), confidence if _number(confidence) else None, str(provenance),
        tuple(uncertainty), reason, coverage if _number(coverage) else None)


def _length(geometry):
    if not isinstance(geometry, (list, tuple)) or len(geometry) < 2:
        return None
    total = 0.0
    try:
        for (lon1, lat1), (lon2, lat2) in zip(geometry, geometry[1:]):
            if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v)
                   for v in (lon1,lat1,lon2,lat2)):
                return None
            lat = math.radians((lat1 + lat2) / 2)
            total += math.hypot(math.radians(lon2-lon1)*6371008.8*math.cos(lat),
                                math.radians(lat2-lat1)*6371008.8)
    except (TypeError, ValueError):
        return None
    return total if math.isfinite(total) and total > 0 else None


def evaluate_candidates(routes, baseline_scores, observations, now, config=TrafficEvaluationConfig()):
    """Compare adjusted costs alongside baseline costs; no planner/executor call."""
    if not isinstance(config, TrafficEvaluationConfig):
        raise TypeError('config must be TrafficEvaluationConfig')
    if set(routes) != set(baseline_scores):
        raise ValueError('Every candidate route must have a baseline score')
    base = {}
    for route_id, score in baseline_scores.items():
        if not _number(score):
            raise ValueError(f'Invalid baseline score for {route_id}')
        base[str(route_id)] = float(score)
    normalized = [validate_evidence(row, now, config) for row in observations]
    rows, by_edge = [], {}
    for evidence, raw in zip(normalized, observations):
        reason, delay = evidence.rejection_reason, None
        if reason is None and config.enabled:
            length = _length(_get(raw, 'road_geometry', ()))
            if length is None:
                reason = 'MISSING_GEOMETRY'
            else:
                delay = min(config.maximum_edge_adjustment_seconds,
                    length*(1/evidence.estimated_speed_mps-1/evidence.free_flow_speed_mps))
                delay = max(0.0, delay)*(evidence.match_confidence or 0.0)
                for edge in evidence.matched_edges:
                    by_edge.setdefault(edge, []).append(delay)
        rows.append(dict(provider=evidence.provider, observation_id=evidence.observation_id,
            matched_edges=list(evidence.matched_edges), provenance=evidence.provenance,
            freshness=evidence.freshness,
            source_timestamp=evidence.source_timestamp.isoformat() if evidence.source_timestamp else None,
            confidence=evidence.match_confidence, coverage=evidence.coverage,
            uncertainty=list(evidence.uncertainty), accepted=reason is None and config.enabled,
            rejection_reason=reason or (None if config.enabled else 'FEATURE_DISABLED'),
            estimated_delay_seconds=delay if reason is None and config.enabled else None))
    penalties, conflicts = {}, {}
    if config.enabled:
        for edge, values in by_edge.items():
            spread, scale = max(values)-min(values), max(max(values), 1.0)
            if len(values) > 1 and spread/scale > config.conflict_relative_spread:
                conflicts[edge] = 'CONFLICTING_PROVIDER_ESTIMATES'
            else:
                penalties[edge] = sum(values)/len(values)
    adjusted, used = {}, {}
    for route_id, route in routes.items():
        rid, edge_set = str(route_id), set(route)
        amount = min(config.maximum_route_adjustment_seconds,
                     sum(penalties[e] for e in set(route) if e in penalties)) if config.enabled else 0.0
        adjusted[rid] = base[rid]+amount
        used[rid] = [row['observation_id'] for row in rows if row['accepted']
                     and any(edge in edge_set and edge not in conflicts for edge in row['matched_edges'])]
    return dict(enabled=config.enabled, baseline_scores=base, adjusted_scores=adjusted,
        selected_candidate=min(adjusted, key=adjusted.get) if adjusted else None,
        adjustments={key: adjusted[key]-base[key] for key in base}, evidence=rows,
        evidence_used_by_candidate=used, conflicting_edges=conflicts,
        canonical_measurements_modified=False, planner_invoked=False, route_committed=False)


def advisory_route_recommendation(evaluation, routes, current_route_id, now, *,
                                  edge_successors, current_route_active_since=None,
                                  last_route_change_at=None, recent_route_ids=(),
                                  config=TrafficEvaluationConfig()):
    """Return an isolated, opt-in route suggestion; never execute or persist it.

    Connectivity is fail-closed: every candidate edge must have a verified
    outgoing-edge entry, and consecutive edges must be connected in that graph.
    The caller supplies commitment/cooldown/route-history facts from the
    experiment harness; this helper does not mutate production state.
    """
    if not isinstance(config, TrafficEvaluationConfig):
        raise TypeError('config must be TrafficEvaluationConfig')
    if not _aware(now):
        raise ValueError('recommendation time must be timezone-aware')
    connected, rejected = {}, {}
    for route_id, route in routes.items():
        rid, edges = str(route_id), tuple(route or ())
        if not edges:
            rejected[rid] = 'EMPTY_ROUTE'
        elif any(edge not in edge_successors for edge in edges):
            rejected[rid] = 'CONNECTIVITY_NOT_VERIFIED'
        elif any(right not in edge_successors[left] for left, right in zip(edges, edges[1:])):
            rejected[rid] = 'DISCONNECTED_ROUTE'
        else:
            connected[rid] = edges
    current = str(current_route_id)
    base_result = dict(action='KEEP', candidate=current, reason=None,
        candidate_rejections=rejected, evidence_used=[], improvement_seconds=0.0,
        planner_invoked=False, route_committed=False, canonical_measurements_modified=False)
    if not config.enabled:
        return dict(base_result, reason='FEATURE_DISABLED')
    if current not in connected or current not in evaluation.get('adjusted_scores', {}):
        return dict(base_result, action='NO_ROUTE', reason='CURRENT_ROUTE_UNVERIFIED')
    if not evaluation.get('enabled'):
        return dict(base_result, reason='EVALUATOR_DISABLED')
    eligible = [rid for rid in connected if rid in evaluation.get('adjusted_scores', {})]
    best = min(eligible, key=lambda rid: evaluation['adjusted_scores'][rid]) if eligible else current
    if best == current:
        return dict(base_result, reason='CURRENT_ROUTE_REMAINS_BEST')
    used = list(evaluation.get('evidence_used_by_candidate', {}).get(best, ()))
    if not used:
        return dict(base_result, reason='ALTERNATIVE_HAS_NO_ELIGIBLE_TRAFFIC_EVIDENCE')
    current_cost = evaluation['adjusted_scores'][current]
    best_cost = evaluation['adjusted_scores'][best]
    improvement = current_cost - best_cost
    ratio = improvement / max(abs(current_cost), 1.0)
    candidate = dict(base_result, candidate=best, evidence_used=used,
                     improvement_seconds=improvement, improvement_ratio=ratio)
    if improvement < config.minimum_improvement_seconds or ratio < config.minimum_improvement_ratio:
        return dict(candidate, reason='INSUFFICIENT_IMPROVEMENT')
    if not _aware(current_route_active_since):
        return dict(candidate, reason='COMMITMENT_START_UNKNOWN')
    if (now-current_route_active_since).total_seconds() < config.minimum_commitment_seconds:
        return dict(candidate, reason='COMMITMENT_PENDING')
    if last_route_change_at is not None:
        if not _aware(last_route_change_at):
            return dict(candidate, reason='COOLDOWN_TIME_INVALID')
        if (now-last_route_change_at).total_seconds() < config.cooldown_seconds:
            return dict(candidate, reason='COOLDOWN_PENDING')
    if best in {str(route_id) for route_id in recent_route_ids}:
        return dict(candidate, reason='RECENT_ROUTE_OSCILLATION')
    return dict(candidate, action='ADVISORY_RECOMMENDATION', reason='ELIGIBLE_EXPERIMENTAL_EVIDENCE')
