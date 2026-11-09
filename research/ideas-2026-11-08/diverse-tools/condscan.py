"""Can a pick-conditioned form of an arm keep its winning games? (diverse-panel.md "Flip analysis")
    python3 condscan.py CAND [CAND...]
Conditions a bot knows from round 1: a champion in our or their comp, the team size. A conditioned variant keeps the
arm's games where the condition holds and the base's elsewhere. The condition is chosen on odd seeds, then read on
even seeds against the whole arm: only a held-out gain counts."""
import sys, os, collections, numpy as np
T = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, T); sys.path.insert(0, os.path.join(T, '..', 'spar-tools'))
import flips, live
D = live.drafts()
CH = ['Ryth', 'Vesper Vale', 'Prism', 'Stellar', 'Vendetta', 'Marcella', 'Tavi', 'Willow', 'Ren', 'Varg', 'Heart of Ruin', 'Cassi & Issac']
conds = {'all': lambda p, o: True}
for c in CH:
    conds[f'we have {c}'] = lambda p, o, c=c: c in p[1]; conds[f'we lack {c}'] = lambda p, o, c=c: c not in p[1]
    conds[f'they have {c}'] = lambda p, o, c=c: c in p[0]; conds[f'they lack {c}'] = lambda p, o, c=c: c not in p[0]
for n in (3, 4, 5): conds[f'team size {n}'] = lambda p, o, n=n: len(p[1]) == n
for cand in sys.argv[1:]:
    G = flips.games(cand, 'variants/oc-base25')
    tot = {0: collections.Counter(), 1: collections.Counter()}; n = collections.Counter()
    for (k, o, mp, s), (cw, rw, *_) in G.items():
        p = D.get((mp, s, o), ((), ())); n[k % 2] += 1; d = int(cw) - int(rw)
        if d:
            for name, f in conds.items():
                if f(p, o): tot[k % 2][name] += d
    pts = {par: {c: 100 * tot[par][c] / n[par] for c in conds} for par in (0, 1)}
    best = sorted(conds, key=lambda c: -pts[1][c])[:5]  # chosen on odd seeds
    print(f'\n{cand} ({len(G)} games): whole arm odd {pts[1]["all"]:+.2f}, even {pts[0]["all"]:+.2f}')
    for c in best: print(f'  chosen on odd: {c:28s} odd {pts[1][c]:+.2f}  even (held out) {pts[0][c]:+.2f}')
