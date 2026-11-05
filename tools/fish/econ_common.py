"""Shared helpers for the econ_* analyses (ECONOMY.md): load econ_rows output, home events, writing.

Cohort roles: fit on the four oldest cohorts, report on fifth + sixth (whole cohorts held out).
"""
import gzip, json, os, sys
from collections import namedtuple

ROWS = 'replays/fish-econ/rows-v3.jsonl.gz'
FIT = ('model', 'confirm', 'third', 'fourth')
HELD = ('fifth', 'sixth')
MOVE, ATK_CAMP, ATK_CHAMP, ATK_OTHER, CAST, RECALL, CANCEL, SUBMIT, TRIB_OK, SHOP, LOCK, TELE, WARD, BLOCKED = (1 << i for i in range(14))
ROLE = {c: 'fit' for c in FIT} | {c: 'held' for c in HELD}


def games(path=ROWS):
    with gzip.open(path, 'rt') as f:
        for line in f:
            g = json.loads(line)
            R = namedtuple('R', g['cols'])
            g['actors'] = {int(k): [R(*r) for r in v] for k, v in g['actors'].items()}
            g['names'] = {int(k): v for k, v in g['names'].items()}
            yield g


def home_events(rows):
    """Completed home arrivals of one actor: list of dicts.

    kind 'recall': a recall channel kept through timer 1 whose next turn starts on spawn.
      i4: index of the turn starting with this channel at timer 4 (its first keep decision),
      i1: the timer-1 turn (the last cancel opportunity), start: the turn that started it,
      arrive: the arrival turn.
    kind 'walk': a turn starting off spawn that ends on spawn by walking (last), arrive: next turn.
    Arrivals by teleport are neither.
    """
    ev = []
    for i in range(1, len(rows)):
        p, t = rows[i - 1], rows[i]
        if not (t.alive and p.alive and p.ealive) or p.home_walk in (0, None) or t.home_walk != 0:
            continue
        if p.ch == 1 and p.tm == 1 and not p.acts & CANCEL:
            j = i - 1
            while j > 0 and rows[j].tm < 4 and rows[j - 1].alive and rows[j - 1].ch == 1 \
                    and rows[j - 1].tm == rows[j].tm + 1 and not rows[j - 1].acts & CANCEL:
                j -= 1
            if rows[j].ch == 1 and rows[j].tm == 4 and j > 0:
                ev.append(dict(kind='recall', i4=j, i1=i - 1, start=j - 1, arrive=i))
        elif (t.x, t.y) == (p.ex, p.ey) and p.ch != 3 and not p.acts & TELE:
            ev.append(dict(kind='walk', last=i - 1, arrive=i))
    return ev


def pct(k, n):
    return f'{k}/{n} ({100 * k / n:.2f}%)' if n else f'{k}/0'


def write_result(path, obj):
    if os.path.exists(path): sys.exit(f'refusing to overwrite {path}')
    with open(path, 'w') as f: json.dump(obj, f, indent=1, sort_keys=True)
    print(f'wrote {path}', file=sys.stderr)
