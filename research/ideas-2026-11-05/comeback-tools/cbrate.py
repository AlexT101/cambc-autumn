#!/usr/bin/env python3
"""cbrate.py AB_NAME_OR_BATCH... [--level L]: comeback rates from CAND's CBK / CBE trace lines (bot 1 = CAND, with
params::comeback::def > 0). CBK: CAND's own cook (0 -> level), CBE: the enemy's by the same test. A side is cooked
from its first transition to a level >= L (default 1). Also counts CBH / CBC / CBL lines (hunt turns, chases, lost
fights taken) and cook rounds. Reads team-?.stdout from each replay zip; no extraction."""
import json, os, sys, zipfile, glob, collections, re, statistics as st

def batches(args):
    out = []
    for a in args:
        if os.path.isdir(a) and glob.glob(f'{a}/*.repl26a'): out.append(a); continue
        out += sorted(glob.glob(f'replays/batch-*-ab-{a}-*'))
    return out

def main():
    a = sys.argv[1:]
    L = 1
    if '--level' in a: i = a.index('--level'); L = int(a[i + 1]); del a[i:i + 2]
    c = collections.Counter()
    rounds = collections.defaultdict(list)
    for b in batches(a):
        res = json.load(open(f'{b}/results.json'))
        matches = res.get('matches', res.get('results', []))
        win = {}
        for m in matches:
            f = m.get('replay') or m.get('file') or ''
            win[os.path.basename(f)] = m.get('winner')
        for f in glob.glob(f'{b}/*.repl26a'):
            base = os.path.basename(f)
            cand_a = base[-10:-8] == '12'
            w = win.get(base)
            if w is None: continue
            cand_won = w == 0
            try:
                z = zipfile.ZipFile(f)
                out = z.read('team-a.stdout' if cand_a else 'team-b.stdout').decode(errors='replace')
            except Exception:
                continue
            own = enemy = None
            hunt = chase = lost = 0
            for line in out.splitlines():
                p = line.split()
                if not p: continue
                if p[0] == 'CBK' and own is None and int(p[4]) >= L: own = int(p[1])
                elif p[0] == 'CBE' and enemy is None and int(p[4]) >= L: enemy = int(p[1])
                elif p[0] == 'CBH': hunt += 1
                elif p[0] == 'CBC': chase += 1
                elif p[0] == 'CBL': lost += 1
            c['games'] += 1
            if own is not None:
                c['cand_cooked'] += 1; c['cand_back'] += cand_won; rounds['cand'].append(own)
                c['hunt'] += hunt; c['chase'] += chase; c['lost'] += lost
            if enemy is not None:
                c['ref_cooked'] += 1; c['ref_back'] += not cand_won; rounds['ref'].append(enemy)
            c['cand_wins'] += cand_won
    n = c['games']
    if not n: print('no games'); return
    print(f"games {n} cand win {100 * c['cand_wins'] / n:.1f}%")
    for who in ('cand', 'ref'):
        k = c[f'{who}_cooked']
        if k:
            print(f"{who} cooked {k} ({100 * k / n:.1f}%) comeback {c[f'{who}_back']} = {100 * c[f'{who}_back'] / k:.1f}%  cook round median {st.median(rounds[who])}")
    if c['cand_cooked']:
        k = c['cand_cooked']
        print(f"per cand-cooked game: hunt turns {c['hunt'] / k:.1f}, hunt chases {c['chase'] / k:.1f}, lost fights taken {c['lost'] / k:.1f}")

if __name__ == '__main__':
    main()
