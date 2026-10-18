from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from citybrain.chennai.traffic.provider import FetchResult
from citybrain.chennai.traffic.verification import verification_report

NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


@pytest.mark.parametrize(('kwargs','expected'), [
    ({'configured':False},'NOT_CONFIGURED'),
    ({'configured':True},'CONFIGURED_NOT_VERIFIED'),
    ({'configured':True,'requested':True,'fetch_result':FetchResult(status='RATE_LIMITED')},'RATE_LIMITED'),
    ({'configured':True,'requested':True,'fetch_result':FetchResult(status='AUTHENTICATION_ERROR')},'INVALID_CREDENTIALS'),
    ({'configured':True,'requested':True,'fetch_result':FetchResult(status='TIMEOUT')},'PROVIDER_UNAVAILABLE'),
    ({'configured':True,'requested':True,'fetch_result':FetchResult(status='PROVIDER_UNAVAILABLE')},'PROVIDER_UNAVAILABLE'),
    ({'configured':True,'requested':True,'fetch_result':FetchResult(status='INVALID_RESPONSE')},'UNKNOWN'),
])
def test_status_classification_never_implies_unobserved_success(kwargs, expected):
    assert verification_report('HERE',now=NOW,**kwargs)['status'] == expected


def test_actual_fresh_provider_response_can_be_verified_without_printing_payload():
    row=SimpleNamespace(source_type='HERE_LIVE',observation_timestamp=NOW)
    report=verification_report('HERE',configured=True,requested=True,
        fetch_result=FetchResult([row],'FETCHED'),now=NOW)
    assert report['status']=='VERIFIED'
    assert report['observation_count']==1
    assert report['freshness']['FRESH']==1
    assert 'key' not in report


def test_stale_and_unknown_source_clock_are_not_reported_as_verified():
    stale=SimpleNamespace(source_type='HERE_LIVE',observation_timestamp=NOW-timedelta(hours=1))
    unknown=SimpleNamespace(source_type='TOMTOM_LIVE',observation_timestamp=None)
    assert verification_report('HERE',configured=True,requested=True,
        fetch_result=FetchResult([stale],'FETCHED'),now=NOW)['status']=='STALE'
    assert verification_report('TOMTOM',configured=True,requested=True,
        fetch_result=FetchResult([unknown],'FETCHED'),now=NOW)['status']=='UNKNOWN'


def test_replay_and_mock_rows_cannot_verify_live_provider():
    row=SimpleNamespace(source_type='MOCKED_PROVIDER',observation_timestamp=NOW)
    report=verification_report('HERE',configured=True,requested=True,
        fetch_result=FetchResult([row],'FETCHED'),now=NOW)
    assert report['status']=='UNKNOWN'
