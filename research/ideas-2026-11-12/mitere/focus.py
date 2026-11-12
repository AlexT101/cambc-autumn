"""Live r7: whom our hits go to when Mite's Vesper and another Mite body are both in reach (start-of-round positions),
and what Mite's Vesper does to us. Usage: focus.py"""
import sys, json, gzip, collections, os
sys.path.insert(0, os.path.dirname(__file__))
import ml
# cambc-rules.yaml champions: attack melee (range 1) or ranged (3).
RANGED = {'Vesper Vale', 'Prism', 'Stellar', 'Tavi', 'Willow', 'Cassi'}
def rng(name): return 3 if name in RANGED else 1
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
st = collections.Counter(); vk = collections.Counter()
for sd in ml.dirs('live'):
    g = ml.load(sd)
    if g is None: continue
    m = g['mite']; o = 1 - m; meta = g['meta']; rd = g['rd']
    name = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    C = {c['id']: c for c in rd['champions']}
    V = [c for c in name if team[c] == m and name[c] == 'Vesper Vale']
    if not V: continue
    v = V[0]; st['games'] += 1; st['wins_mite'] += g['win']
    def pos(c, r):  # start of round r = end of round r-1
        i = max(0, r - 2)
        return (C[c]['x'][i], C[c]['y'][i]) if C[c]['alive'][i] and C[c]['x'][i] is not None else None
    def hp(c, r):
        i = max(0, r - 2); return C[c]['hp'][i] / max(1, C[c]['maxHp'][i] if isinstance(C[c]['maxHp'], list) else C[c]['maxHp'])
    for e in g['ev']:
        if e['k'] == 'death' and e.get('v') in team and team[e['v']] == o:
            st['our_deaths'] += 1; vk['by_vesper' if e.get('by') == v else 'by_other'] += 1
        if e['k'] != 'attack' or e.get('a') not in team or team[e['a']] != o: continue
        t = e.get('tgt')
        if t not in team or team[t] != m: continue
        r = e['r']; f = tuple(e['f']); rg = rng(name[e['a']])
        cands = [c for c in name if team[c] == m and pos(c, r) and cheb(pos(c, r), f) <= rg]
        if v not in cands or len(cands) < 2: continue
        st['choices'] += 1; st['hit_v'] += t == v
        st['share_uniform'] += 1 / len(cands)
        lowest = min(cands, key=lambda c: C[c]['hp'][max(0, r - 2)])
        st['v_lowest_abs'] += lowest == v; st['hit_lowest'] += t == lowest
        if lowest != v: st['v_not_lowest'] += 1; st['hit_v_not_lowest'] += t == v
print(dict(st)); print(dict(vk))
print(f"choices with Vesper and another Mite body in reach: {st['choices']}; hit Vesper {st['hit_v']/st['choices']:.0%} (uniform {st['share_uniform']/st['choices']:.0%}); "
      f"when she is not the lowest-health one: {st['hit_v_not_lowest']/max(1,st['v_not_lowest']):.0%} of {st['v_not_lowest']}; our deaths by her {vk['by_vesper']/max(1,st['our_deaths']):.0%}")
