"""When Fish places a carried altar lock (MISC.md section 2).

    python3 tools/fish/misc_lockplace.py OUT.json

Opportunities from misc_locks.mjs (replays/fish-misc/locks-v1.json.gz): completed turns of an alive
Fish champion that carries a lock at turn end (or placed one) with an altar within 2 of its final
tile, joined to misc_rows for the turn-start channel, stun, visible enemies and gems. Turns
starting in a tribute or teleport channel, or stunned, cannot place and are dropped, as are
opportunities where Fish's own lock is already on every near altar (a second is illegal).
Rule: place iff some near altar holds no lock of either team (observer lock table).
Baseline: never place. Per cohort.
"""
import argparse, gzip, json, sys
from collections import Counter, defaultdict
sys.path.insert(0, 'tools/fish')
from misc_common import *

LOCKS = 'replays/fish-misc/locks-v1.json.gz'
COH = {'manifest.json': 'model', 'confirmation-manifest.json': 'confirm', 'third-manifest.json': 'third',
       'fourth-manifest.json': 'fourth', 'fifth-manifest.json': 'fifth'}


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('out'); a = ap.parse_args()
    with gzip.open(LOCKS) as f: d = json.load(f)
    need = {(g['game'], r['r'], r['id']) for g in d['games'] for r in g['rows']}
    S = {}
    for g in games():
        for r in g['rows']:
            k = (g['game'], r['r'], r['id'])
            if k in need: S[k] = r
    R = defaultdict(Counter); EX = defaultdict(list); desc = Counter()
    for g in d['games']:
        side, coh = g['side'], COH[g['cohort']]
        for o in g['rows']:
            r = S.get((g['game'], o['r'], o['id']))
            if r is None: desc['no-row'] += 1; continue
            stun = any(b.get('type') == 1 for b in (r['s'].get('buffs') or []))
            if r['s'].get('channelType') in (2, 3, 4) or stun: desc['cannot-act'] += 1; continue
            if o['placed']:
                p = o['placed'][0]; locks = p['locks']; near = p['near']; placed = True
                # The table is read after placing: drop the placed lock itself.
                locks = [l for l in locks if not (l['team'] == side and [l['x'], l['y']] == p['to'])]
            else:
                if o['carryEnd'] <= 0: continue
                locks, near, placed = o['locks'], o['near'], False
            has = lambda alt, team: any((l['x'], l['y']) == tuple(alt) and (l['team'] == side) == team for l in locks)
            cand = [al for al in near if not has(al, True)]
            if not cand: desc['all-near-altars-already-ours'] += 1; continue
            empty = [al for al in cand if not has(al, False)]
            pred = bool(empty)
            ex = (g['game'], o['r'], o['id'], r['name'], o['pos'], cand, 'enemy-visible' if r['ne'] else '-', r['s'].get('gems'))
            for key, ok in (('rule_place_iff_lockless_altar_within_2', pred == placed), ('baseline_never_place', not placed)):
                R[key][(coh, ok)] += 1
                if not ok and key.startswith('rule') and len(EX[(pred, placed)]) < 10: EX[(pred, placed)].append(ex)
            desc[('placed' if placed else 'not', 'lockless-altar' if empty else 'enemy-lock-only', 'enemy-visible' if r['ne'] else '-', 'gems>0' if r['s'].get('gems') else 'gems0')] += 1
            if placed and empty: desc[('placed-on-lockless-altar', [list(x) for x in empty].count(p['to']) > 0)] += 1
    out = {'doc': __doc__, 'results': {}, 'breakdown': {' '.join(map(str, k)) if isinstance(k, tuple) else k: v for k, v in desc.items()},
           'counterexamples': {f'pred={k[0]} placed={k[1]}': v for k, v in EX.items()}}
    for k, v in R.items():
        per = {c: [v[(c, True)], v[(c, True)] + v[(c, False)]] for c in sorted({x[0] for x in v})}
        tot = [sum(x[0] for x in per.values()), sum(x[1] for x in per.values())]
        out['results'][k] = {'per_cohort': per, 'total': tot}
        print(f'{k:42s} {pct(*tot)}  ' + '  '.join(f'{c} {x[0]}/{x[1]}' for c, x in per.items()))
    for k, v in sorted(desc.items(), key=str): print(v, k)
    write_result(a.out, out)


if __name__ == '__main__':
    main()
