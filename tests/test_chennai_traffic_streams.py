"""A closure is state of a stable stream, not a separate stream identity."""
from datetime import timedelta
from test_chennai_traffic import Provider, NOW, observation, matcher
from citybrain.chennai.traffic.provider import FetchResult
from citybrain.chennai.traffic.service import TrafficService


def test_exact_review_reopening_supersedes_current_closure():
    clock = [NOW]
    provider = Provider(FetchResult([observation(incident_type='ROAD_CLOSURE')],'FETCHED'))
    service = TrafficService(provider,matcher(),clock=lambda:clock[0])
    service.poll_once()
    clock[0] += timedelta(seconds=30)
    provider.result = FetchResult([observation(observation_id='reopened',observation_timestamp=clock[0],incident_type=None)],'FETCHED')
    service.poll_once()
    rows = service.snapshot()['observations']
    assert len(rows) == 1 and rows[0]['observation_id'] == 'reopened'
    assert rows[0]['incident_type'] is None


from dataclasses import replace
from citybrain.chennai.traffic.normalization import here_rows
from test_chennai_traffic import here_payload


def test_closure_reopening_closure_and_old_states_cannot_resurrect():
    clock = [NOW]
    provider = Provider(FetchResult())
    service = TrafficService(provider,matcher(),clock=lambda:clock[0])
    for seconds,incident in [(0,'ROAD_CLOSURE'),(10,None),(20,'ROAD_CLOSURE')]:
        clock[0] = NOW+timedelta(seconds=seconds)
        provider.result = FetchResult([observation(observation_id=str(seconds),
            observation_timestamp=clock[0],incident_type=incident)],'FETCHED')
        service.poll_once()
        rows = service.snapshot()['observations']
        assert len(rows) == 1 and rows[0]['incident_type'] == incident
        # Late delivery of an older state never changes the current stream.
        provider.result = FetchResult([observation(observation_id='late-'+str(seconds),
            observation_timestamp=clock[0]-timedelta(seconds=1),
            incident_type=None if incident else 'ROAD_CLOSURE')],'FETCHED')
        service.poll_once()
        assert service.snapshot()['observations'][0]['observation_id'] == str(seconds)
    assert service.snapshot()['out_of_order'] == 3


def test_independent_incident_and_flow_do_not_overwrite_each_other():
    flow = observation()
    incident = replace(flow,observation_id='event',observation_kind='INCIDENT',incident_type='construction')
    provider = Provider(FetchResult([flow,incident],'FETCHED'))
    service = TrafficService(provider,matcher(),clock=lambda:NOW)
    service.poll_once()
    assert len(service.snapshot()['observations']) == 2


def test_here_incident_versions_keep_original_stream_identity():
    payload = here_payload()
    item = payload['results'][0]
    item['incidentDetails'] = dict(id='version-1',originalId='stable-event',type='construction')
    first = here_rows(payload,NOW,incidents=True)[0][0]
    item['incidentDetails'].update(id='version-2',type='accident')
    payload['sourceUpdated'] = (NOW+timedelta(seconds=1)).isoformat()
    second = here_rows(payload,NOW+timedelta(seconds=1),incidents=True)[0][0]
    assert first.provider_segment_id != second.provider_segment_id
    assert first.stream_key == second.stream_key
    assert first.observation_kind == 'INCIDENT'
    provider = Provider(FetchResult([first,second],'FETCHED'))
    service = TrafficService(provider,matcher(),clock=lambda:NOW+timedelta(seconds=1))
    service.poll_once()
    rows = service.snapshot()['observations']
    assert len(rows) == 1 and rows[0]['incident_type'] == 'accident'


def test_tomtom_unknown_time_flow_reopening_replaces_closure():
    from citybrain.chennai.traffic.normalization import tomtom_row
    from test_chennai_traffic import tomtom_payload
    data = tomtom_payload()
    first = tomtom_row(data,NOW)
    data['flowSegmentData']['roadClosure'] = False
    second = tomtom_row(data,NOW+timedelta(seconds=30))
    provider = Provider(FetchResult([first,second],'FETCHED'))
    service = TrafficService(provider,matcher(),clock=lambda:NOW+timedelta(seconds=30))
    service.poll_once()
    rows = service.snapshot()['observations']
    assert len(rows) == 1 and rows[0]['incident_type'] is None
    assert rows[0]['freshness_status'] == 'UNKNOWN'
    assert rows[0]['matching_status'] == 'INSUFFICIENT_DATA'


def test_reused_record_id_cannot_hide_new_state_or_bypass_ordering():
    clock = [NOW]
    row = observation(incident_type='ROAD_CLOSURE')
    provider = Provider(FetchResult([row],'FETCHED'))
    service = TrafficService(provider,matcher(),clock=lambda:clock[0])
    service.poll_once()
    clock[0] += timedelta(seconds=30)
    # Even if a recording reuses an ID, a newer actual observation supersedes it.
    reopened = replace(row,observation_timestamp=clock[0],incident_type=None)
    provider.result = FetchResult([reopened],'FETCHED')
    service.poll_once()
    assert service.snapshot()['observations'][0]['incident_type'] is None
    provider.result = FetchResult([row],'FETCHED')
    service.poll_once()
    assert service.snapshot()['observations'][0]['incident_type'] is None
    assert service.snapshot()['out_of_order'] == 1
    provider.result = FetchResult([reopened],'FETCHED')
    service.poll_once()
    assert service.snapshot()['duplicates'] == 1
