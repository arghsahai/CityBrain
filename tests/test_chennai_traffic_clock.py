"""Implausible source clocks must not poison the current-stream watermark."""
from datetime import timedelta
from test_chennai_traffic import Provider, NOW, observation, matcher
from citybrain.chennai.traffic.provider import FetchResult
from citybrain.chennai.traffic.service import TrafficService


def test_exact_review_future_timestamp_cannot_block_correction():
    clock = [NOW]
    provider = Provider(FetchResult([observation()],'FETCHED'))
    service = TrafficService(provider,matcher(),clock=lambda:clock[0])
    service.poll_once()
    provider.result = FetchResult([observation(observation_id='bad-clock',observation_timestamp=NOW+timedelta(days=365))],'FETCHED')
    service.poll_once()
    assert service.snapshot()['observations'][0]['observation_id'] == 'o1'
    clock[0] += timedelta(seconds=30)
    provider.result = FetchResult([observation(observation_id='corrected',observation_timestamp=clock[0])],'FETCHED')
    service.poll_once()
    assert service.snapshot()['observations'][0]['observation_id'] == 'corrected'


import pytest
from citybrain.chennai.traffic.freshness import FreshnessPolicy


@pytest.mark.parametrize('skew,accepted',[(0,True),(5,True),(5.001,False),(365*86400,False),(-10,True)])
def test_future_clock_tolerance_boundary(skew,accepted):
    row = observation(observation_timestamp=NOW+timedelta(seconds=skew))
    service = TrafficService(Provider(FetchResult([row],'FETCHED')),matcher(),clock=lambda:NOW)
    service.poll_once()
    snapshot = service.snapshot()
    assert bool(snapshot['observations']) is accepted
    assert snapshot['quarantine_count'] == (0 if accepted else 1)
    if not accepted:
        assert snapshot['quarantine'][0]['freshness_status'] == 'UNKNOWN'
        assert snapshot['quarantine'][0]['reason'] == 'SOURCE_CLOCK_AHEAD'
        assert snapshot['display_status'] != 'LIVE DATA'


def test_future_first_record_then_valid_record_recovers():
    provider = Provider(FetchResult([observation(observation_id='future',observation_timestamp=NOW+timedelta(days=365))],'FETCHED'))
    service = TrafficService(provider,matcher(),clock=lambda:NOW)
    service.poll_once()
    assert not service.snapshot()['observations']
    provider.result = FetchResult([observation(observation_id='valid')],'FETCHED')
    service.poll_once()
    assert service.snapshot()['observations'][0]['observation_id'] == 'valid'
    assert service.snapshot()['out_of_order'] == 0


def test_quarantine_is_bounded_and_never_reclassified_as_fresh():
    provider = Provider(FetchResult([observation()],'FETCHED'))
    service = TrafficService(provider,matcher(),max_records=2,clock=lambda:NOW)
    service.poll_once()
    provider.result = FetchResult([observation(observation_id='future-'+str(i),
        observation_timestamp=NOW+timedelta(days=365,seconds=i)) for i in range(20)],'FETCHED')
    service.poll_once()
    snapshot = service.snapshot(NOW+timedelta(days=365))
    assert snapshot['quarantine_count'] == 2 and snapshot['quarantined_total'] == 20
    assert all(row['freshness_status']=='UNKNOWN' for row in snapshot['quarantine'])
    assert snapshot['observations'][0]['observation_id'] == 'o1'
    assert snapshot['observations'][0]['freshness_status'] == 'EXPIRED'
    snapshot['quarantine'][0]['freshness_status'] = 'FRESH'
    assert service.snapshot()['quarantine'][0]['freshness_status'] == 'UNKNOWN'


def test_custom_clock_tolerance_and_unknown_source_timestamp():
    provider = Provider(FetchResult([observation(observation_timestamp=NOW+timedelta(seconds=8))],'FETCHED'))
    service = TrafficService(provider,matcher(),freshness=FreshnessPolicy(future_tolerance=10),clock=lambda:NOW)
    service.poll_once()
    assert service.snapshot()['quarantine_count'] == 0
    provider.result = FetchResult([observation(observation_id='unknown',provider_segment_id='other',observation_timestamp=None,direction='UNKNOWN')],'FETCHED')
    service.poll_once()
    unknown = next(o for o in service.snapshot()['observations'] if o['provider_segment_id']=='other')
    assert unknown['freshness_status'] == 'UNKNOWN'
    assert unknown['matching_status'] == 'INSUFFICIENT_DATA'
    assert service.snapshot()['quarantine_count'] == 0
