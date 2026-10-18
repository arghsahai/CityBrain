from datetime import datetime, timezone
from types import SimpleNamespace

from citybrain.chennai.run import _experimental_traffic_advice


NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


class Edge:
    def __init__(self, length, speed, outgoing=()):
        self.length, self.speed, self.outgoing = length, speed, outgoing

    def getLength(self): return self.length
    def getSpeed(self): return self.speed
    def getOutgoing(self): return [SimpleNamespace(getID=lambda edge=e: edge) for e in self.outgoing]


class Network:
    edges = {'current':Edge(800,10,('alt','bad')), 'alt':Edge(200,50), 'bad':Edge(10000,10)}
    def getEdges(self): return [SimpleNamespace(getID=lambda edge=k:edge,getOutgoing=e.getOutgoing) for k,e in self.edges.items()]
    def getEdge(self, edge_id): return self.edges[edge_id]


def runtime():
    plan=SimpleNamespace(created_time=0)
    traci=SimpleNamespace(route_position=lambda _:dict(remaining_route=['current','bad']))
    return SimpleNamespace(active_plan=plan,core=SimpleNamespace(traci=traci),
        routes={'alternate':['current','alt']},ambulance_id='amb',now=100,
        replanner=SimpleNamespace(last_replan_time=None))


def test_runtime_sidecar_emits_advice_without_route_execution():
    obs=dict(provider='fixture',observation_id='o1',road_geometry=((80.15,12.84),(80.151,12.84)),
        direction='FORWARD',retrieved_at=NOW,source_type='MOCKED_PROVIDER',current_speed=5,
        free_flow_speed=10,observation_timestamp=NOW,freshness_status='FRESH',
        matching_status='MATCHED',matched_sumo_edges=('alt',),matching_confidence=.95,
        matching_coverage=.99)
    result=_experimental_traffic_advice(runtime(),[obs],NOW,Network())
    assert result['action']=='ADVISORY_RECOMMENDATION'
    assert result['candidate']=='alternate'
    assert result['planner_invoked'] is False
    assert result['route_committed'] is False
    assert result['canonical_measurements_modified'] is False


def test_runtime_sidecar_contains_failures_and_missing_plan_without_raising():
    no_plan=runtime();no_plan.active_plan=None
    result=_experimental_traffic_advice(no_plan,[],NOW,Network())
    assert result['action']=='NO_ROUTE' and result['reason']=='NO_ACCEPTED_PLAN'
    broken=runtime();broken.core.traci.route_position=lambda _: (_ for _ in ()).throw(RuntimeError())
    result=_experimental_traffic_advice(broken,[],NOW,Network())
    assert result['action']=='UNAVAILABLE'
    assert result['planner_invoked'] is False and result['route_committed'] is False
