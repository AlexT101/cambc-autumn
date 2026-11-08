"""After each capture share: the holder's next move within 20 rounds: recall home, tribute, next camp hit (chain), by bag size."""
import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
RW = 600
def f(d, team):
    meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}
    R = json.load(gzip.open(d + '/rounds.json.gz')); ri = {r: j for j, r in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz')]
    out = []
    for i, e in enumerate(ev):
        if e['r'] > RW: break
        if e['k'] != 'capture' or e['team'] != team: continue
        for cid, gm, gd in e['shares']:
            j = ri.get(e['r']); bag = C[cid]['gems'][j] if j is not None else 0  # bag at round start incl? approximate
            hp = C[cid]['hp'][j] / max(1, C[cid]['maxHp'][j]) if j is not None else 1
            nxt = 'none'
            for e2 in ev[i + 1:]:
                if e2['r'] > e['r'] + 20: break
                if e2.get('a') != cid and e2.get('v') != cid: continue
                if e2['k'] == 'recall_end': nxt = 'home'; break
                if e2['k'] == 'tribute_start': nxt = 'tribute'; break
                if e2['k'] in ('attack', 'cast') and 'cdmg' in e2: nxt = 'farm'; break
                if e2['k'] == 'death': nxt = 'death'; break
                if e2['k'] in ('attack', 'cast') and ('dmg' in e2 or 'stun' in e2): nxt = 'fight'; break
            out.append((gm, bag, hp, nxt))
    return out
L = load(H + 'bigl/ana', False); S = load(H + 'spar/ana')
games = json.load(open(H + 'bigl/games.json')); liveg = {}
for mid, g in games.items():
    if g['version'] != 89 or mid not in L: continue
    liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
acc = collections.defaultdict(list); ng = collections.Counter()
for o in 'FM':
    for mp, side, m in local.matches(f'spar-c27-o29{o}'):
        k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
        if k not in S or (mp, side, o) not in liveg: continue
        ot = 1 if side == 'a' else 0; ld, g = liveg[(mp, side, o)]
        for nm, d, t in (('live', H + 'bigl/ana/' + ld, ot), ('spar', H + 'spar/ana/' + S[k], ot), ('us', H + 'bigl/ana/' + ld, 1 - ot)):
            acc[(o, nm)] += f(d, t); ng[(o, nm)] += 1
for key, rs in sorted(acc.items()):
    a = np.array([(g, b) for g, b, h, x in rs]); nx = [x for g, b, h, x in rs]
    for lo, hi in ((1, 14), (15, 39), (40, 9999)):
        sel = [x for (g, b, h, x) in rs if lo <= b + g <= hi and g > 0]
        c = collections.Counter(sel); t = max(1, len(sel))
        print(key, f'bag {lo}-{hi}: n/g {len(sel)/ng[key]:.1f} ' + ' '.join(f'{x} {c[x]/t:.2f}' for x in ('home', 'tribute', 'farm', 'fight', 'death', 'none')))
