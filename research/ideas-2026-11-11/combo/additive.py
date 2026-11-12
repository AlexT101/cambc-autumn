"""Additivity of the combination arms, per fresh map, on the same fgate batch runs.

    python3 additive.py REF 16-31 [--fuel N]

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
ARMS = ['cbx-cm', 'cbx-gp', 'cbx-cmgp', 'cbx-cmck', 'cbx-cmgpck']
CONTRASTS = [
    ('cm alone', {'cbx-cm': 1}),
    ('gp alone', {'cbx-gp': 1}),
    ('cm+gp', {'cbx-cmgp': 1}),
    ('cm+ck', {'cbx-cmck': 1}),
    ('cm+gp+ck', {'cbx-cmgpck': 1}),
    ('gp given cm (cm+gp - cm)', {'cbx-cmgp': 1, 'cbx-cm': -1}),
    ('ck given cm (cm+ck - cm)', {'cbx-cmck': 1, 'cbx-cm': -1}),
    ('ck given cm+gp (all - cm+gp)', {'cbx-cmgpck': 1, 'cbx-cmgp': -1}),
    ('cm x gp interaction (cm+gp - cm - gp)', {'cbx-cmgp': 1, 'cbx-cm': -1, 'cbx-gp': -1}),
    ('gp x ck interaction (all - cm+gp - cm+ck + cm)', {'cbx-cmgpck': 1, 'cbx-cmgp': -1, 'cbx-cmck': -1, 'cbx-cm': 1}),
    ('all minus sum of parts (all - gp - cm+ck)', {'cbx-cmgpck': 1, 'cbx-gp': -1, 'cbx-cmck': -1}),
    ('all minus best single (all - cm)', {'cbx-cmgpck': 1, 'cbx-cm': -1}),
    ('cm+gp minus best single (cm+gp - cm)', {'cbx-cmgp': 1, 'cbx-cm': -1}),
    ('ps alone', {'cbx-ps': 1}),
    ('cm+ps', {'cbx-cmps': 1}),
    ('cm+gp+ck+ps', {'cbx-allps': 1}),
    ('ps given cm (cm+ps - cm)', {'cbx-cmps': 1, 'cbx-cm': -1}),
    ('ps given cm+gp+ck (all+ps - all)', {'cbx-allps': 1, 'cbx-cmgpck': -1}),
    ('cm x ps interaction (cm+ps - cm - ps)', {'cbx-cmps': 1, 'cbx-cm': -1, 'cbx-ps': -1}),
    ('cm+ps minus best single (cm+ps - ps)', {'cbx-cmps': 1, 'cbx-ps': -1}),
    ('all+ps minus cm+ps', {'cbx-allps': 1, 'cbx-cmps': -1}),
    ('all+ps minus sum (all+ps - all - ps)', {'cbx-allps': 1, 'cbx-cmgpck': -1, 'cbx-ps': -1}),
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
