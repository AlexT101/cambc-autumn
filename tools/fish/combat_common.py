"""Shared kit table and one-turn damage reach for the Fish combat study.

Approximations, not engine-exact: items (Skirmish, Durability, Collectors) are not in the
cached contexts, and walking/dash reach is Chebyshev, ignoring terrain and blockers.
"""
import gzip
import json
from pathlib import Path

from breadth import RANGED, dist, xy

# Cohorts, in creation order. Discovery is the first three, held out the rest.
COHORTS = [
    ('model', 'research/fish-2026-11-05/manifest.json', 'replays/fish-model'),
    ('confirm', 'research/fish-2026-11-05/confirmation-manifest.json', 'replays/fish-confirm'),
    ('third', 'research/fish-2026-11-05/third-manifest.json', 'replays/fish-third'),
    ('fourth', 'research/fish-2026-11-05/fourth-manifest.json', 'replays/fish-fourth'),
    ('fifth', 'research/fish-2026-11-05/fifth-manifest.json', 'replays/fish-fifth'),
    ('sixth', 'research/fish-2026-11-05/sixth-manifest.json', 'replays/fish-sixth'),
    ('seventh', 'research/fish-2026-11-05/seventh-manifest.json', 'replays/fish-seventh'),
]
DISCOVERY = {'model', 'confirm', 'third'}

# type -> (reset slot, dash slot, [(slot, multiplier x Focus, kind)]) for damage abilities.
# kind: 'unit' (range 4, excludes walking), 'ground' (range 4, 3x3, excludes walking),
# 'hor' (Heart of Ruin's dash: lands within 2, hits within 1).
KIT = {
    0: (1, None, [(0, 1.0, 'ground')]),
    1: (0, 1, []),
    2: (0, 1, []),
    3: (None, None, [(0, 2.0, 'unit')]),
    4: (0, 1, []),
    5: (None, None, [(0, 2.0, 'unit'), (1, 1.4, 'ground')]),
    6: (None, None, [(0, 1.5, 'unit'), (1, 1.0, 'ground')]),
    7: (0, None, [(1, 2.0, 'unit')]),
    8: (1, None, []),
    9: (None, 1, [(0, 1.1, 'unit')]),
    10: (0, None, []),
    11: (0, None, [(1, 1.6, 'unit')]),
    12: (None, None, [(1, 1.5, 'hor')]),
}
STUN_SLOTS = {0: 0, 3: 1, 6: 0, 7: 0, 9: 0, 11: 1, 12: 1}


def shield(c):
    return sum(b['mag'] for b in c.get('buffs', []) if b['type'] == 0)


def stun_timer(c):
    return max((b['timer'] for b in c.get('buffs', []) if b['type'] == 1), default=-1)


def stunned_next(c):
    # A positive-timer stun removes its next turn.
    return stun_timer(c) > 0


def ehp(c):
    return c['hp'] + shield(c)


def scale(c):
    # Heart of Ruin's passive; shields do not count as health.
    return 1 + 0.5 * (1 - c['hp'] / c['maxHp']) if c['type'] == 12 else 1.0


def one_turn_damage(c, d, ready=None):
    """Most damage champion c can deal in one turn to a unit at Chebyshev distance d.

    ready: cooldown pair override; default c['cd']. One successful cast per turn.
    """
    cd = ready if ready is not None else c['cd']
    reset, dash, spells = KIT.get(c['type'], (None, None, []))
    rng = 3 if c['type'] in RANGED else 1
    walk = 0 if c['type'] in RANGED else 1  # a ranged walk spends the attack
    s, f = c['strength'], c['focus']
    best = 0.0
    if d <= rng + walk:
        best = s
        if reset is not None and cd[reset] == 0:
            best = 2 * s
    if dash is not None and cd[dash] == 0 and d <= rng + walk + 2:
        best = max(best, s)
    for slot, mult, kind in spells:
        if cd[slot] != 0:
            continue
        if kind in ('unit', 'ground') and d <= 4 + (1 if kind == 'ground' else 0):
            best = max(best, mult * f + (s if d <= rng else 0))
        if kind == 'hor' and d <= 4:
            best = max(best, mult * f + s)
    return best * scale(c)


def load(cache, entry):
    with gzip.open(Path(cache) / f"{entry['sha256'][:16]}.json.gz") as f:
        return json.load(f)


def contexts(t):
    return [t['start']] + [a['before'] for a in t['actions'] if 'before' in a] + ([t['end']] if 'end' in t else [])


def hits(t, actor_type):
    """Damaging/stunning actions on enemy champions this turn: list of (kind, slot, ability, target ids)."""
    out = []
    for a in t['actions']:
        s = a.get('before')
        if not s:
            continue
        es = s['enemies']
        if a['kind'] == 'Attack':
            ids = [e['id'] for e in es if [e['x'], e['y']] == a['to']]
            if ids:
                out.append(('basic', None, None, ids))
        elif a['kind'] == 'Cast ability':
            ab = a['ability']
            if ab in (2, 4):
                ids = [e['id'] for e in es if [e['x'], e['y']] == a['to']]
            elif ab == 3 or (ab == 6 and actor_type == 12):
                ids = [e['id'] for e in es if dist(xy(e), a['to']) <= 1]
            else:
                ids = []
            if ids:
                out.append(('cast', a['slot'], ab, ids))
    return out
