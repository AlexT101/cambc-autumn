"""Explicit per-map REF-only runtime inputs for native opponent experiments."""
import hashlib
import json
from pathlib import Path


def load(path, maps):
    if path is None:
        return None, None
    path = Path(path).resolve()
    raw = path.read_bytes()
    data = json.loads(raw)
    if set(data) != {'schema', 'opponent_index', 'maps'} or data['schema'] != 1 or data['opponent_index'] != 1:
        raise ValueError('experiment config requires schema1 and logical REF opponent_index1')
    if not isinstance(data['maps'], dict):
        raise ValueError('experiment maps must be an object')
    for p in maps:
        c = data['maps'].get(Path(p).stem)
        if not isinstance(c, dict) or set(c) != {'seed', 'salt', 'unmetered'}:
            raise ValueError(f'missing/invalid experiment config for {Path(p).stem}')
        if any(type(c[k]) is not int or not 0 <= c[k] < 2**64 for k in ('seed', 'salt')) or type(c['unmetered']) is not bool:
            raise ValueError('seed/salt must be uint64 and unmetered boolean')
    return data['maps'], {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'schema': 1, 'opponent_index': 1}


def teams(config, path, order):
    if config is None:
        return None
    return {side: config[Path(path).stem] if logical == 1 else None for side, logical in zip(('a', 'b'), order)}


def suffix(config, path, order):
    value = teams(config, path, order)
    return '' if value is None else ' --runtime-config ' + json.dumps(value, separators=(',', ':'))
