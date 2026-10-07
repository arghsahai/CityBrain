"""Immutable JSON snapshots and atomic summaries for integration runs only."""
from dataclasses import asdict, is_dataclass
from enum import Enum
import json
import math
from pathlib import Path


def snapshot(value):
    if is_dataclass(value):
        return snapshot(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            raise ValueError('NaN cannot be runtime evidence')
        return 'Infinity' if value > 0 else '-Infinity'
    if isinstance(value, dict):
        return {str(k): snapshot(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [snapshot(v) for v in value]
    return value


class EvidenceWriter:
    def __init__(self, directory):
        self.directory = Path(directory)
        protected = Path(__file__).resolve().parents[2] / 'experiments' / 'results'
        if self.directory.resolve().is_relative_to(protected):
            raise ValueError('Integration evidence must be outside experimental results')
        self.directory.mkdir(parents=True, exist_ok=False)
        self.events = self.directory / 'events.jsonl'

    def append(self, record):
        with self.events.open('a') as stream:
            stream.write(json.dumps(snapshot(record), allow_nan=False, sort_keys=True) + '\n')

    def summary(self, value):
        temporary = self.directory / 'summary.json.tmp'
        temporary.write_text(json.dumps(snapshot(value), allow_nan=False, indent=2) + '\n')
        temporary.replace(self.directory / 'summary.json')
