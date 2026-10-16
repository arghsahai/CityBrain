"""Small normalized JSON recordings. Invalid records are reported, never live."""
from dataclasses import replace
import json
from pathlib import Path
from .models import TrafficObservation
from .provider import FetchResult


class ReplayTrafficProvider:
    name = 'REPLAY'

    def __init__(self, path):
        path = Path(path)
        if path.stat().st_size > 2*1024*1024:
            raise ValueError('Replay exceeds 2 MiB')
        payload = json.loads(path.read_text())
        self.provenance = payload['provenance']
        if self.provenance not in {'SYNTHETIC_SAMPLE','RECORDED_PROVIDER_DATA','REPLAY'}:
            raise ValueError('Replay requires declared provenance')
        if len(payload['observations']) > 2000:
            raise ValueError('Too many replay records')
        self.records, self.errors = [], []
        for index, row in enumerate(payload['observations']):
            try:
                row = dict(row, source_type='SYNTHETIC_SAMPLE' if self.provenance=='SYNTHETIC_SAMPLE' else 'REPLAY',
                           recording_provenance=self.provenance)
                observation = TrafficObservation(**row)
                if observation.observation_timestamp is None:
                    raise ValueError('Replay ordering needs a source timestamp')
                self.records.append(observation)
            except (ValueError, TypeError, KeyError):
                self.errors.append(f'INVALID_REPLAY_RECORD:{index}')
        self.records.sort(key=lambda o:o.observation_timestamp)
        self._cursor = 0

    def fetch(self, now):
        rows = []
        while self._cursor < len(self.records) and self.records[self._cursor].observation_timestamp <= now:
            rows.append(replace(self.records[self._cursor],retrieved_at=now))
            self._cursor += 1
        return FetchResult(rows,'REPLAY',list(self.errors))
