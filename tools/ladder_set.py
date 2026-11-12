"""The ladder map sets directly under maps/.

maps/ holds every published map: from 2026-11-12, the 128 of 2026-11-05 (tools/ladder128.txt) plus 42 `05*` maps.
Tools that treat maps/ as "the ladder" default to the 128, so caches, paired runs and seeded mapgen suites made
before stay comparable. `all` is every map directly under maps/; `new` is the maps outside the 128.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / 'maps'
LIST = ROOT / 'tools' / 'ladder128.txt'
SETS = ('128', 'new', 'all')


def names128():
    return LIST.read_text(encoding='utf-8').split()


def files(which='128'):
    if which not in SETS: raise ValueError(f'unknown ladder set {which!r}: one of {", ".join(SETS)}')
    every = sorted(MAPS.glob('*.map26a'))
    if which == 'all': return every
    keep = set(names128())
    if which == 'new': return [p for p in every if p.stem not in keep]
    missing = keep - {p.stem for p in every}
    if missing: raise ValueError(f'maps/ lacks {len(missing)} of the 128 ladder maps, e.g. {sorted(missing)[:3]}')
    return [p for p in every if p.stem in keep]


def names(which='128'):
    return [p.stem for p in files(which)]
