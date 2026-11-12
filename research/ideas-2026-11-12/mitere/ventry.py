"""Live r7, Mite's Vesper's kills of our bodies: the stretch the victim spent within 6 of her before dying (entry =
first round of it, looking back up to 20), its health in her hits at entry and at death, who closed the distance
into 6 (her or the victim), whether the victim saw her at entry, and the damage it took in the stretch by source."""
import sys, os, json, collections
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(sd):
    g = ml.load(sd)
    if g is None: return []
    m = g['mite']; o = 1 - m; rd = g['rd']
    name = {c['id']: c['name'] for c in g['meta']['champions']}; team = {c['id']: c['team'] for c in g['meta']['champions']}
    C = {c['id']: c for c in rd['champions']}
    V = [c for c in name if team[c] == m and name[c] == 'Vesper Vale']
    if not V: return []
    v = V[0]; nR = len(rd['round'])
    def at(c, i):
        cc = C[c]
        return (cc['x'][i], cc['y'][i]) if 0 <= i < nR and cc['alive'][i] and cc['x'][i] is not None else None
    dmg = collections.defaultdict(list)
    for e in g['ev']:
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            for t, d in e['dmg']: dmg[t].append((e['r'], 'V' if e['a'] == v else ('M' if team.get(e['a']) == m else 'O'), d))
        if e['k'] == 'camp_attack':
            dmg[e.get('tgt')].append((e['r'], 'camp', e.get('dmg', 0)))
    out = []
    for e in g['ev']:
        if e['k'] != 'death' or e.get('by') != v or team.get(e.get('v')) != o or e.get('linked') is not None: continue
        x = e['v']; r = e['r']; i0 = r - 2
        if i0 < 22: continue
        k = 0
        while k < 20 and at(x, i0 - k - 1) and at(v, i0 - k - 1) and cheb(at(x, i0 - k - 1), at(v, i0 - k - 1)) <= 6: k += 1
        ie = i0 - k  # entry: first index of the stretch
        pa, pb = at(x, ie - 1), at(x, ie); qa, qb = at(v, ie - 1), at(v, ie)
        closer = None
        if pa and pb and qa and qb and k < 20:
            closer = 'both' if pa != pb and qa != qb else ('us' if pa != pb else ('her' if qa != qb else 'none'))
        hp_e = C[x]['hp'][ie]; s_e = C[v]['str'][ie]
        D = collections.Counter()
        for (rr, src, d) in dmg[x]:
            if ie + 2 <= rr <= r: D[src] += d
        out.append({'k': k, 'htk_entry': hp_e / s_e, 'hpf_entry': hp_e / C[x]['maxHp'][ie], 'htk_death': C[x]['hp'][i0] / C[v]['str'][i0],
                    'closer': closer, 'seen_entry': v in (C[x]['sees'][ie] or []), 'dmg': dict(D), 'vic': name[x],
                    'vhpf_entry': C[v]['hp'][ie] / C[v]['maxHp'][ie], 'vstr': s_e, 'r': r,
                    'gems_entry': C[x]['gems'][ie],
                    'm5': sum(1 for c in name if team[c] == m and at(c, ie) and at(x, ie) and cheb(at(c, ie), at(x, ie)) <= 5),
                    'o5': sum(1 for c in name if team[c] == o and c != x and at(c, ie) and at(x, ie) and cheb(at(c, ie), at(x, ie)) <= 5)})
    return out
if __name__ == '__main__':
    R = []
    with Pool(8) as P:
        for rr in P.imap_unordered(one, ml.dirs('live'), chunksize=4): R.extend(rr)
    json.dump(R, open(os.path.expanduser('~/tmp-offload/mitere/ventry.json'), 'w'))
    n = len(R); print(n, 'kills')
    print('stretch length within 6 (rounds):', sorted(collections.Counter(min(r['k'], 20) for r in R).items()))
    print('closer into 6:', collections.Counter(r['closer'] for r in R))
    print('seen at entry:', sum(r['seen_entry'] for r in R) / n)
    def b(h): return min(int(h), 8)
    print('her hits to kill at entry:', sorted(collections.Counter(b(r['htk_entry']) for r in R).items()))
    print('health fraction at entry:', sorted(collections.Counter(round(r['hpf_entry'], 1) for r in R).items()))
    T = collections.Counter(); [T.update(r['dmg']) for r in R]; tot = sum(T.values())
    print('damage taken in the stretch by source:', {k: f'{v / tot:.0%}' for k, v in T.items()})
    print('numbers at entry m5 - 1 - o5:', sorted(collections.Counter(r['m5'] - 1 - r['o5'] for r in R).items()))
