"""Safe status classification for explicit, non-automatic provider checks."""
from datetime import datetime, timezone
from .freshness import FreshnessPolicy


def verification_report(provider, *, configured, requested=False, fetch_result=None, now=None):
    """Classify status without treating configuration, mocks or replay as live proof."""
    now = now or datetime.now(timezone.utc)
    if not configured:
        status = 'NOT_CONFIGURED'
    elif not requested or fetch_result is None:
        status = 'CONFIGURED_NOT_VERIFIED'
    elif fetch_result.status == 'RATE_LIMITED':
        status = 'RATE_LIMITED'
    elif fetch_result.status == 'AUTHENTICATION_ERROR':
        status = 'INVALID_CREDENTIALS'
    elif fetch_result.status in {'TIMEOUT', 'PROVIDER_UNAVAILABLE'}:
        status = 'PROVIDER_UNAVAILABLE'
    elif fetch_result.status == 'FETCHED':
        rows = list(fetch_result.observations)
        if not rows or any(row.source_type != provider+'_LIVE' for row in rows):
            status = 'UNKNOWN'
        else:
            policy = FreshnessPolicy()
            states = [policy.classify(row.observation_timestamp, now)[0] for row in rows]
            status = ('VERIFIED' if states and all(value == 'FRESH' for value in states) else
                      'STALE' if states and all(value in {'STALE','EXPIRED'} for value in states) else 'UNKNOWN')
    else:
        status = 'UNKNOWN'
    counts = {'FRESH':0,'STALE':0,'EXPIRED':0,'UNKNOWN':0}
    for row in getattr(fetch_result, 'observations', ()) if fetch_result else ():
        counts[FreshnessPolicy().classify(row.observation_timestamp, now)[0]] += 1
    return dict(provider=provider, status=status, request_made=bool(requested and fetch_result is not None),
        observation_count=sum(counts.values()), freshness=counts,
        response_status=fetch_result.status if fetch_result else None,
        safe_errors=list(getattr(fetch_result, 'errors', ()))[:10] if fetch_result else [])
