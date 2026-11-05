"""Shared helpers for the team/camp-fight study (research/fish-2026-11-05/TEAM.md).

Observer caches come from team_decode.mjs (replays/fish-team/<SHA16>.json.gz): labels and
diagnostics. Fish's own view comes from the earlier actor caches (combat_common.COHORTS).
"""
import gzip
import json
import math
from pathlib import Path

from combat_common import COHORTS

TEAM_CACHE = Path('replays/fish-team')
HELD_OUT = {'fifth', 'sixth'}
# Camp type index (engine CAMPS order: Wolf, Elk, Gem cluster, Gold cluster, Monolith, Golem).
CAMP_RANGE = {0: 3, 1: 4, 2: 0, 3: 0, 4: 5, 5: 4}
CAMP_STR = {0: 20, 1: 60, 2: 0, 3: 0, 4: 200, 5: 120}
CAMP_NAMES = ['Wolf', 'Elk', 'Gem', 'Gold', 'Monolith', 'Golem']
NAMES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
RANGED = {1, 3, 5, 6, 8, 11}
# cp champion state columns (team_decode.champState)
ID, ALIVE, X, Y, HP, MAXHP, SHIELD, GEMS, PRIO, NEXTPRIO, CHAN, CHANT, STUN, CD0, CD1, STR, FOC = range(17)


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def entries():
    """(cohort, manifest entry) for every pinned game, in cohort order, deduplicated."""
    seen = set()
    for name, manifest, cache in COHORTS:
        for e in json.loads(Path(manifest).read_text()):
            if e['sha256'] in seen:
                continue
            seen.add(e['sha256'])
            yield name, cache, e


def load_team(key):
    with gzip.open(TEAM_CACHE / f'{key}.json.gz') as f:
        return json.load(f)


def load_actor(cache, key):
    with gzip.open(Path(cache) / f'{key}.json.gz') as f:
        return json.load(f)


def decode_level(value, n):
    """priority = -rank - (n+1)*L, rank in [2, n+1]. Returns (rank, L); rank 1 marks a misfit."""
    r = (-value) % (n + 1)
    rank = r if r else n + 1
    return rank, (-value - rank) // (n + 1)


def mode_of(L, band=None):
    if L >= 50:
        return 'contact-'
    if L <= -50:
        return 'contact+'
    if L < 0:
        return 'early'
    if band is None:
        return 'quiet' if L <= 3 else 'late' if L <= 8 else 'other'
    return 'quiet' if L == band else 'late' if L == band + 5 else 'other'


def band(hp, shield, maxhp, gems):
    h = min(1.0, (hp + shield) / maxhp) * (0.65 if gems > 0 else 1.0)
    return max(0, math.floor(4 * (1 - h)))


def mirror(md, p):
    x, y = p
    s = md['symmetry']
    return (md['width'] - 1 - x if s != 'vertical' else x, md['height'] - 1 - y if s != 'horizontal' else y)


def spawn_tiles(md, side):
    # spawnA maxima are exclusive (HANDOFF trap).
    s = md['spawnA']
    tiles = {(x, y) for y in range(s['minY'], s['maxY']) for x in range(s['minX'], s['maxX'])}
    return tiles if side == 0 else {mirror(md, p) for p in tiles}


def starts(side, rnd):
    """Whether team `side` starts round `rnd` (team A odd rounds)."""
    return (rnd % 2 == 1) == (side == 0)


def write_json(path, obj):
    path = Path(path)
    if path.exists():
        raise SystemExit(f'refusing to overwrite {path}')
    path.write_text(json.dumps(obj, indent=1, sort_keys=False) + '\n')
