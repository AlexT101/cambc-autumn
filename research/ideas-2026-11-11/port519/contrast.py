"""The port519 arms and their paired contrasts, per fresh map, on the same fgate batch runs.

    python3 contrast.py REF 63-74 [--fuel N]

Each arm's unit on a map is CAND's mean minus REF's over the map's paired games (fresh maps only, cells all arms
share). A contrast is a signed sum of arms' units on each map; it prints the mean and 95% CI in points.
"""
import os, sys
from pathlib import Path
import numpy as np

ROOT = Path('/home/ubuntu/cambc-autumn')
sys.path.insert(0, str(ROOT / 'tools'))
import fgate_batch as fb  # noqa: E402

fg = fb.load('fgate_blocks', ROOT / 'research/ideas-2026-11-09/freshgate-tools/fgate.py')
fg.local.R = f'{ROOT}/'
BODIES = {'F': 'Flp4', 'M': 'Mt3q'}
ARMS = ['c519-cmps', 'c519-ps']
CONTRASTS = [
    ('cm+ps', {'c519-cmps': 1}),
    ('ps alone', {'c519-ps': 1}),
    ('cm given ps (cm+ps - ps)', {'c519-cmps': 1, 'c519-ps': -1}),
]


def batches(spec):
    out = []
    for part in spec.split(','):
        a, _, b = part.partition('-')
        out += range(int(a), int(b or a) + 1)
    return out


def main():
    ref, spec = sys.argv[1:3]
    fuel = f'-fuel{sys.argv[sys.argv.index("--fuel") + 1]}' if '--fuel' in sys.argv else ''
    arms = sys.argv[sys.argv.index('--arms') + 1].split(',') if '--arms' in sys.argv else ARMS
    maps, lad = fb.pool(), set(fb.ladder())
    name = lambda bot, o, j: f'fb{fg.ENG}-{os.path.basename(bot).removeprefix("oc-")}-{BODIES[o]}-m2560b{j:03d}{fuel}'
    per = {o: {a: [] for a in arms} for o in ('all', 'F', 'M')}
    used = []
    for j in batches(spec):
        if fb.suite(maps, 2560, j) is None: continue
        try:
            cells = {(a, o): fg.local.cells(name(a, o, j)) for a in [*arms, ref] for o in 'FM'}
        except Exception:
            continue
        if any(not c for c in cells.values()): continue
        used.append(j)
        for o in 'FM':
            common = set.intersection(*(set(cells[(a, o)]) for a in [*arms, ref]))
            common = {c for c in common if c[0] not in lad}
            bymap = {}
            for c in common: bymap.setdefault(c[0], []).append(c)
            for m, cs in bymap.items():
                for a in arms:
                    d = [cells[(a, o)][c] - cells[(ref, o)][c] for c in cs]
                    per[o][a].append((j, m, float(np.mean(d))))
    # all: mean of the two bodies on maps both have
    keyed = {o: {a: {(j, m): v for j, m, v in per[o][a]} for a in arms} for o in 'FM'}
    print(f'against {os.path.basename(ref)}: batches {used} ({len(used)}), fresh maps')
    for label, w in CONTRASTS:
        if any(a not in arms for a in w): continue
        row = []
        for o in ('all', 'F', 'M'):
            if o == 'all':
                ks = set.intersection(*(set(keyed['F'][a]) & set(keyed['M'][a]) for a in w))
                u = np.array([sum(c * (keyed['F'][a][k] + keyed['M'][a][k]) / 2 for a, c in w.items()) for k in ks])
            else:
                ks = set.intersection(*(set(keyed[o][a]) for a in w))
                u = np.array([sum(c * keyed[o][a][k] for a, c in w.items()) for k in ks])
            if len(u) < 2: row.append('-'); continue
            m, h = 100 * u.mean(), 196 * u.std(ddof=1) / np.sqrt(len(u))
            row.append(f'{m:+.2f} ±{h:.2f}' + (f' (n {len(u):,})' if o == 'all' else ''))
        print(f'  {label:48s} all {row[0]:24s} Fish {row[1]:14s} Mite {row[2]}')


main()
