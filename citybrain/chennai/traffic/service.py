"""One background fetcher, bounded last-valid cache and nonblocking snapshots.

No simulation/control references. stop() signals cancellation without waiting for
network completion; the daemon worker discards late results. HTTP calls have a
bounded timeout and a response size cap. No persistent provider recording.
"""
from collections import OrderedDict
from dataclasses import replace
from datetime import datetime, timezone
import math
import os
import threading
import time
from .freshness import FreshnessPolicy


class TrafficService:
    def __init__(self, provider, matcher, *, poll_seconds=60, max_records=256, freshness=None, clock=None):
        if isinstance(poll_seconds,bool) or not math.isfinite(poll_seconds) or poll_seconds <= 0:
            raise ValueError('Polling interval must be positive')
        if isinstance(max_records,bool) or not isinstance(max_records,int) or not 1 <= max_records <= 2000:
            raise ValueError('Cache size must be 1..2000')
        self.provider, self.matcher = provider,matcher
        self.poll_seconds, self.max_records = poll_seconds,max_records
        self.freshness = freshness or FreshnessPolicy()
        self.clock = clock or (lambda:datetime.now(timezone.utc))
        self._lock, self._fetch_lock = threading.Lock(),threading.Lock()
        self._stop, self._wake = threading.Event(),threading.Event()
        self._thread = None
        self._cache = OrderedDict()
        self._status = getattr(provider,'status','WAITING')
        self._errors, self._last_success, self._last_attempt = [],None,None
        self.successes = self.failures = self.duplicates = self.out_of_order = 0

    def start(self):
        if self._thread is not None:
            return  # Explicitly single-use; prevents overlap after stop/start.
        self._thread = threading.Thread(target=self._loop,name='chennai-advisory-traffic',daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def notify_clock(self):
        # Replay only: wake on simulation clock progress, never paid providers.
        if self.provider.name == 'REPLAY':
            self._wake.set()

    def _loop(self):
        while not self._stop.is_set():
            delay = self.poll_once()
            self._wake.wait(delay)
            self._wake.clear()

    def poll_once(self):
        if self._stop.is_set() or not self._fetch_lock.acquire(blocking=False):
            return self.poll_seconds
        try:
            now = self.clock()
            try:
                result = self.provider.fetch(now)
                matched = [self.matcher.match(o) for o in result.observations[:2000]]
            except Exception:
                # No exception text: third-party/custom transports may embed keys.
                from .provider import FetchResult
                result,matched = FetchResult(status='PROVIDER_UNAVAILABLE',errors=['FETCH_OR_MATCH_FAILED'],retry_after=60),[]
            with self._lock:
                if self._stop.is_set():
                    return self.poll_seconds
                self._last_attempt, self._status = now,result.status
                self._errors = list(result.errors[:20])
                if result.status in {'FETCHED','REPLAY','COVERAGE_UNVERIFIED_OR_INSUFFICIENT'}:
                    self.successes += 1
                    self._last_success = now
                elif result.status not in {'NOT_CONFIGURED','READY_BUT_NOT_TESTED'}:
                    self.failures += 1
                for observation in matched:
                    key = observation.stream_key
                    old = self._cache.get(key)
                    if old is not None:
                        if observation.observation_id == old.observation_id:
                            self.duplicates += 1
                            self._cache[key] = replace(old,retrieved_at=observation.retrieved_at)
                            continue
                        if old.observation_timestamp and (observation.observation_timestamp is None or observation.observation_timestamp < old.observation_timestamp):
                            self.out_of_order += 1
                            continue
                    self._cache[key] = observation
                    self._cache.move_to_end(key)
                    while len(self._cache) > self.max_records:
                        self._cache.popitem(last=False)
            return max(self.poll_seconds,result.retry_after)
        finally:
            self._fetch_lock.release()

    def snapshot(self, now=None):
        now = now or self.clock()
        with self._lock:
            records = list(self._cache.values())
            status, errors = self._status,list(self._errors)
            last_success,last_attempt = self._last_success,self._last_attempt
            counts = dict(successful_fetches=self.successes,failed_fetches=self.failures,
                          duplicates=self.duplicates,out_of_order=self.out_of_order)
        rows = []
        for observation in records:
            freshness,age,problem = self.freshness.classify(observation.observation_timestamp,now)
            row = replace(observation,freshness_status=freshness).to_dict()
            row.update(age_seconds=age,time_quality=problem)
            rows.append(row)
        matched = [o for o in rows if o['matching_status']=='MATCHED']
        # LIVE requires an actual successful adapter response, a verified match,
        # fresh source time, and a healthy latest poll. Running != live.
        verified_live = status=='FETCHED' and any(o['source_type'] in {'HERE_LIVE','TOMTOM_LIVE'} and o['freshness_status']=='FRESH' for o in matched)
        sources = {o['source_type'] for o in rows}
        source = next(iter(sources)) if len(sources)==1 else 'UNAVAILABLE'
        statuses = {name:('READY_BUT_NOT_TESTED' if os.environ.get(name+'_API_KEY') else 'NOT_CONFIGURED') for name in ('HERE','TOMTOM')}
        statuses['REPLAY'] = 'NOT_SELECTED'
        statuses[self.provider.name] = status
        return dict(provider=self.provider.name,provider_statuses=statuses,source=source,status=status,
            display_status='LIVE DATA' if verified_live else status.replace('_',' '),
            match_status='VERIFIED ROAD MATCHES' if matched else 'NO VERIFIED ROAD MATCHES',
            observations=rows,last_update=last_success.isoformat() if last_success else None,
            last_attempt=last_attempt.isoformat() if last_attempt else None,
            coverage_area=getattr(self.provider,'bounds',None),errors=errors,
            freshness_policy=dict(fresh_seconds=self.freshness.fresh_seconds,expired_seconds=self.freshness.expired_seconds,future_tolerance=self.freshness.future_tolerance),
            observation_count=len(rows),matched_roads=len({e for o in matched for e in o['matched_sumo_edges']}),
            unmatched_records=sum(o['matching_status']!='MATCHED' for o in rows),
            stale_records=sum(o['freshness_status'] in {'STALE','EXPIRED'} for o in rows),
            unknown_time_records=sum(o['freshness_status']=='UNKNOWN' for o in rows),
            applied_to_sumo=False,**counts)
