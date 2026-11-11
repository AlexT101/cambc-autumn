"""Pooled read of fgate batch runs over a list of pool batches (segments the gate cannot walk in one go).

    python3 report.py CAND REF 32-34,38-53 [--fuel N]

Units as tools/fgate_batch.py: a fresh map's 0.5 + CAND's mean minus REF's over its paired games. Prints the pooled
fresh read, Fish and Mite, one-site and multi-site, the ladder side read, both SPRT LLRs over the units in batch
order, and each bot's win rate and out-of-fuel turns a game against each body.
"""
import json, math, os, random, sys
from pathlib import Path
import numpy as np

ROOT = Path('/home/ubuntu/cambc-autumn')
sys.path.insert(0, str(ROOT / 'tools'))
import fgate_batch as fb  # noqa: E402

fg = fb.load('fgate_blocks', ROOT / 'research/ideas-2026-11-09/freshgate-tools/fgate.py')
fg.local.R = f'{ROOT}/'
BODIES = {'F': 'Flp4', 'M': 'Mt3q'}


def batches(spec):
    out = []
    for part in spec.split(','):
        a, _, b = part.partition('-')
        out += range(int(a), int(b or a) + 1)
    return out


def main():
    cand, ref, spec = sys.argv[1:4]
    fuel = f'-fuel{sys.argv[sys.argv.index("--fuel") + 1]}' if '--fuel' in sys.argv else ''
    maps, lad = fb.pool(), set(fb.ladder())
    name = lambda bot, o, j: f'fb{fg.ENG}-{os.path.basename(bot).removeprefix("oc-")}-{BODIES[o]}-m2560b{j:03d}{fuel}'
    U = {'fresh': {g: [] for g in ('all', 'F', 'M', 'one', 'multi')}, 'L': {g: [] for g in ('all', 'F', 'M')}}
    tot = {(b, o): [0, 0, 0, 0] for b in (cand, ref) for o in 'FM'}  # games, wins, oof turns, errors
    used, flips = [], 0
    for j in batches(spec):
        s = fb.suite(maps, 2560, j)
        runs = {(b, o): fb.read_summary(name(b, o, j)) for b in (cand, ref) for o in 'FM'}
        if s is None or any(x is None or x['games'] + x['errors'] < s['games'] for x in runs.values()):
            continue
        used.append(j)
        diff = {'fresh': {}, 'L': {}}
        for o in 'FM':
            x, y = fg.local.cells(name(cand, o, j)), fg.local.cells(name(ref, o, j))
            for c in x.keys() & y.keys():
                key = 'L' if c[0] in lad else 'fresh'
                diff[key].setdefault(c[0], {}).setdefault(o, []).append(x[c] - y[c]); flips += x[c] != y[c]
        for (b, o), x in runs.items():
            t = tot[(b, o)]; t[0] += x['games']; t[1] += x['cand_wins']; t[2] += x['oof']['cand'][0]; t[3] += x['errors']
        rng = random.Random(j + 1)
        for key in ('fresh', 'L'):
            order = sorted(diff[key]); rng.shuffle(order)
            for m in order:
                v = [d for o in diff[key][m] for d in diff[key][m][o]]
                U[key]['all'].append(0.5 + float(np.mean(v)))
                for o in diff[key][m]: U[key][o].append(0.5 + float(np.mean(diff[key][m][o])))
                cls = s['maps'].get(m) if key == 'fresh' else None
                if cls is not None: U[key]['one' if cls else 'multi'].append(0.5 + float(np.mean(v)))
    print(f'{os.path.basename(cand)} against {os.path.basename(ref)}: batches {used} ({len(used)}), {flips} paired games differ')
    for label, u, per in (('fresh', U['fresh']['all'], 8), ('fresh Fish', U['fresh']['F'], 4), ('fresh Mite', U['fresh']['M'], 4),
                          ('fresh one-site', U['fresh']['one'], 8), ('fresh multi-site', U['fresh']['multi'], 8), ('ladder', U['L']['all'], 8)):
        e = fb.est(u)
        if e: print(f'  {label:17s} {e[0]:+.2f} ±{e[1]:.2f}  ({50 + e[0]:.2f}%, {50 + e[0] - e[1]:.2f}-{50 + e[0] + e[1]:.2f}) of {len(u):,} maps, {per * len(u):,} games')
    u = U['fresh']['all']
    if u:
        print(f'  LLR high (0.505/0.5075) {fg.ab.llr(u, 0.505, 0.5075):+.2f}, low (0.4975/0.50) {fg.ab.llr(u, 0.4975, 0.50):+.2f} [-2.94 | +2.94 | live 4.60]')
    for (b, o), (g, w, oof, err) in tot.items():
        if g: print(f'  {os.path.basename(b):14s} against {BODIES[o]}: {100 * w / g:.2f}% of {g:,} (ladder maps included), out-of-fuel turns {oof / g:.2f} a game, failed {err}')
    for b in (cand, ref):
        g = sum(tot[(b, o)][0] for o in 'FM'); oof = sum(tot[(b, o)][2] for o in 'FM')
        if g: print(f'  {os.path.basename(b):14s} both bodies: out-of-fuel turns {oof / g:.3f} a game of {g:,}')


main()
