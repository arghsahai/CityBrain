"""Strict artifacts, paired-row validation and atomic checkpoints."""
import csv
import hashlib
import json
import math
from pathlib import Path

STATUSES = {'SUCCESS','FAILED_BLOCKED','TELEPORTED','NO_ROUTE','TIMEOUT','ERROR','NOT_APPLICABLE'}


def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(item) for item in value]
    return value


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(finite(value), indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def fingerprint(root):
    """Hash execution code and SUMO inputs, excluding results and documentation."""
    digest = hashlib.sha256()
    paths = []
    for directory in ('citybrain', 'experiments/runners', 'simulation/network', 'simulation/scenarios'):
        paths += [p for p in (root/directory).rglob('*') if p.suffix in ('.py','.xml','.sumocfg')]
    paths.append(root/'experiments/outcomes.py')
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def is_true(value):
    return value is True or value == 'True'


def validate_row(row):
    status = row['completion_status']
    if status not in STATUSES:
        raise ValueError(f'Unknown completion status: {status}')
    success = status == 'SUCCESS'
    if is_true(row['completed']) != success or (success and is_true(row['teleported'])):
        raise ValueError('Inconsistent success/teleport flags')
    if (status == 'TELEPORTED') != is_true(row['teleported']):
        raise ValueError('Inconsistent teleport status')
    for key in ('ambulance_arrival_time','actual_travel_time','response_time','eta_error'):
        if success:
            if row[key] in ('',None) or not math.isfinite(float(row[key])) or float(row[key]) < 0:
                raise ValueError(f'Invalid successful metric: {key}')
        elif row[key] not in ('',None):
            raise ValueError(f'Failure contains successful-trip metric: {key}')


def validate_pairs(rows, require_complete=True):
    pairs = {}
    for row in rows:
        validate_row(row)
        key = (row['scenario'],row['profile'],str(row['seed']))
        strategies = pairs.setdefault(key,{})
        if row['strategy'] in strategies:
            raise ValueError(f'Duplicate trial: {key} {row["strategy"]}')
        strategies[row['strategy']] = row
    for key, pair in pairs.items():
        if require_complete and set(pair) != {'static','dynamic'}:
            raise ValueError(f'Incomplete pair: {key}')
        if set(pair) == {'static','dynamic'}:
            left,right = pair['static'],pair['dynamic']
            # Errors before dispatch remain recorded; agreement is checked where both dispatched.
            if left['initial_route'] and right['initial_route']:
                if left['initial_route'] != right['initial_route'] or not math.isclose(float(left['initial_eta']),float(right['initial_eta']),rel_tol=1e-9):
                    raise ValueError(f'Unmatched initial conditions: {key}')


def write_csv(path, rows):
    if not rows:
        return
    validate_pairs(rows, require_complete=False)
    path = Path(path)
    temporary = path.with_suffix('.csv.tmp')
    with temporary.open('w',newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
