"""Camp damage, overkill-free efficiency, champion-damage turns, idle turns by r<=RW, live opp vs spar opp."""
import json, gzip, os, sys, collections, numpy as np, pickle
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
RW = int(os.environ.get('RW', 200))
def f(d, team):
    meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}
    mine = {i for i, c in ch.items() if c['team'] == team}
    o = collections.defaultdict(float)
    turns = collections.defaultdict(lambda: [False, False, False])  # (r, a) -> camp hit, champ hit, moved
    for l in gzip.open(d + '/events.jsonl.gz'):
        e = json.loads(l)
        if e['r'] > RW: break
        a = e.get('a')
        if a not in mine: continue
        k = e['k']
        if k in ('attack', 'cast'):
            if 'cdmg' in e: o['campdmg'] += sum(x for _, x in e['cdmg']); turns[(e['r'], a)][0] = True
            if 'dmg' in e: o['champdmg'] += sum(x for _, x in e['dmg']); turns[(e['r'], a)][1] = True
            if 'stun' in e: turns[(e['r'], a)][1] = True
        if k == 'move' or (k == 'cast' and 'moved' in e): turns[(e['r'], a)][2] = True
    o['campturns'] = sum(t[0] for t in turns.values()); o['champturns'] = sum(t[1] for t in turns.values())
    o['moveonly'] = sum(t[2] and not t[0] and not t[1] for t in turns.values())
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = np.array(R['round']); i = min(np.searchsorted(rr, RW), len(rr) - 1)
    o['alive_turns'] = sum(sum(c['alive'][:i + 1]) for c in R['champions'] if c['team'] == team)
    o['earned'] = sum(c['earned'][i] for c in R['champions'] if c['team'] == team)
    # turns spent on own spawn (healing/shopping) — approximate by position equal to spawn region of round 1
    sp = {(c['x'][0], c['y'][0]) for c in R['champions'] if c['team'] == team}
    xs = [(c['x'], c['y'], c['alive']) for c in R['champions'] if c['team'] == team]
    lo = (min(p[0] for p in sp), min(p[1] for p in sp)); hi = (max(p[0] for p in sp), max(p[1] for p in sp))
    o['spawn_turns'] = sum(1 for x, y, al in xs for j in range(i + 1) if al[j] and lo[0] - 1 <= x[j] <= hi[0] + 1 and lo[1] - 1 <= y[j] <= hi[1] + 1)
    return o
if __name__ == '__main__':
    L = load(H + 'bigl/ana', False); S = load(H + 'spar/ana')
    games = json.load(open(H + 'bigl/games.json')); liveg = {}
    for mid, g in games.items():
        if g['version'] != 89 or mid not in L: continue
        liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for o in 'FM':
        for mp, side, m in local.matches(f'spar-c27-o29{o}'):
            k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
            if k not in S or (mp, side, o) not in liveg: continue
            ot = 1 if side == 'a' else 0; ld, g = liveg[(mp, side, o)]
            for nm, d in (('live', H + 'bigl/ana/' + ld), ('spar', H + 'spar/ana/' + S[k])):
                for kk, v in f(d, ot).items(): acc[(o, nm)][kk].append(v)
    for (o, nm), dd in sorted(acc.items()):
        print(o, nm, ' '.join(f'{k} {np.mean(v):.0f}' for k, v in sorted(dd.items())), f'gold/campdmg {np.mean(dd["earned"])/np.mean(dd["campdmg"])*1000:.1f}/k')
