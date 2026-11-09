"""Can a pick-conditioned form of an arm keep its winning games? (diverse-panel.md "Flip analysis")
    python3 condscan.py CAND [CAND...]
Conditions a bot knows from round 1: a champion in our or their comp, the team size, and map features the bot can
compute from the map (draftlab's maps.jsonl, split at terciles over the 128 ladder maps; never the map's name). A conditioned variant keeps the
arm's games where the condition holds and the base's elsewhere. The condition is chosen on odd seeds, then read on
even seeds against the whole arm: only a held-out gain counts."""
import sys, os, collections, numpy as np
T = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, T); sys.path.insert(0, os.path.join(T, '..', 'spar-tools'))
import flips, live
D = live.drafts()
CH = ['Ryth', 'Vesper Vale', 'Prism', 'Stellar', 'Vendetta', 'Marcella', 'Tavi', 'Willow', 'Ren', 'Varg', 'Heart of Ruin', 'Cassi & Issac']
conds = {'all': lambda p, o, mp: True}
for c in CH:
    conds[f'we have {c}'] = lambda p, o, mp, c=c: c in p[1]; conds[f'we lack {c}'] = lambda p, o, mp, c=c: c not in p[1]
    conds[f'they have {c}'] = lambda p, o, mp, c=c: c in p[0]; conds[f'they lack {c}'] = lambda p, o, mp, c=c: c not in p[0]
for n in (3, 4, 5): conds[f'team size {n}'] = lambda p, o, mp, n=n: len(p[1]) == n
import json
MF = {}
for l in open(os.path.expanduser('~/tmp-offload/bigl/maps.jsonl')):
    r = json.loads(l); MF[r['name']] = r['f']
FEATS = ['area', 'altars', 'spawn_dist', 'choke_rel', 'openness', 'detour', 'reach_frac', 'gems_side', 'gold_side',
         'camps_side', 'camp_density', 'contested_share', 'altar_near', 'altar_ratio', 'cluster_share', 'big_share',
         'groups_side', 'max_group', 'holes', 'walls', 'bushes', 'dash_gain', 'shared_share', 'camp_near']
MAPF = {}  # condition name -> set of map names
for f in FEATS:
    v = np.array([MF[m][f] for m in MF], float); lo, hi = np.quantile(v, [1 / 3, 2 / 3])
    if lo < hi:
        MAPF[f'{f} <= {lo:.3g}'] = {m for m in MF if MF[m][f] <= lo}
        MAPF[f'{f} > {hi:.3g}'] = {m for m in MF if MF[m][f] > hi}
        MAPF[f'{f} <= {hi:.3g}'] = {m for m in MF if MF[m][f] <= hi}
        MAPF[f'{f} > {lo:.3g}'] = {m for m in MF if MF[m][f] > lo}
MAPF['one altar'] = {m for m in MF if MF[m]['altars'] <= 1}; MAPF['multi altar'] = {m for m in MF if MF[m]['altars'] > 1}
for c, ms in MAPF.items(): conds['map ' + c] = lambda p, o, mp, ms=ms: mp in ms
for cand in sys.argv[1:]:
    G = flips.games(cand, 'variants/oc-base25')
    tot = {0: collections.Counter(), 1: collections.Counter()}; n = collections.Counter()
    for (k, o, mp, s), (cw, rw, *_) in G.items():
        p = D.get((mp, s, o), ((), ())); n[k % 2] += 1; d = int(cw) - int(rw)
        if d:
            for name, f in conds.items():
                if f(p, o, mp): tot[k % 2][name] += d
    pts = {par: {c: 100 * tot[par][c] / n[par] for c in conds} for par in (0, 1)}
    best = sorted(conds, key=lambda c: -pts[1][c])[:int(os.environ.get('TOP', 8))]  # chosen on odd seeds
    print(f'\n{cand} ({len(G)} games): whole arm odd {pts[1]["all"]:+.2f}, even {pts[0]["all"]:+.2f}')
    for c in best: print(f'  chosen on odd: {c:28s} odd {pts[1][c]:+.2f}  even (held out) {pts[0][c]:+.2f}')
    # Cell effects repeat across seeds, so map conditions can pass the seed split by picking maps. Stricter: choose on
    # odd seeds of half the maps, read on even seeds of the other half; the gain is the condition's over the whole arm.
    rng = np.random.default_rng(0); maps = sorted({mp for (_, _, mp, _) in G}); held = []; pick = collections.Counter()
    for _ in range(40):
        A = set(rng.permutation(maps)[:len(maps) // 2])
        t = {0: collections.Counter(), 1: collections.Counter()}; m = collections.Counter()
        for (k, o, mp, s), (cw, rw, *_) in G.items():
            par = k % 2
            if (par == 1) != (mp in A): continue
            p = D.get((mp, s, o), ((), ())); m[par] += 1; d = int(cw) - int(rw)
            if d:
                for name, f in conds.items():
                    if f(p, o, mp): t[par][name] += d
        c = max(conds, key=lambda c: t[1][c]); pick[c] += 1; held.append(100 * (t[0][c] - t[0]['all']) / m[0])
    print(f'  map-split held out: condition minus whole arm {np.mean(held):+.2f} (sd over splits {np.std(held):.2f});'
          f' chosen {pick.most_common(4)}')
