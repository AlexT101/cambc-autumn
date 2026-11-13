"""Prism-on-Prism kills: distance trace, cooldowns, bags, casts in the last rounds."""
import sys, json, gzip, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    except Exception: return None
    name = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}
    r0 = R['round'][0]; out = []
    casts = collections.defaultdict(list)
    for e in ev:
        if e.get('k') == 'cast': casts[e['a']].append(e)
        if e.get('k') == 'attack' and 'champ' in json.dumps(e): pass
    for e in ev:
        if e.get('k') != 'death': continue
        v, k = e['v'], e.get('by')
        if k is None or name.get(v) != 'Prism' or name.get(k) != 'Prism': continue
        i = e['r'] - r0
        V, K = ch[v], ch[k]
        dists = []
        for j in range(max(0, i-15), i+1):
            dists.append(max(abs(V['x'][j]-K['x'][j]), abs(V['y'][j]-K['y'][j])) if V['x'][j] is not None and K['x'][j] is not None else None)
        j = max(0, i-1)
        # killer casts in last 3 rounds
        kc = [c for c in casts[k] if e['r']-3 <= c['r'] <= e['r']]
        vc = [c for c in casts[v] if e['r']-8 <= c['r'] <= e['r']]
        out.append(dict(r=e['r'], gems=e.get('gems',0), vfoc=V['foc'][j], kfoc=K['foc'][j], vhp=V['hp'][j], vmax=V['maxHp'][j],
            dists=dists, vcd=(V['cd0'][j], V['cd1'][j]), kcd_before=(K['cd0'][max(0,i-3)], K['cd1'][max(0,i-3)]),
            kcasts=[(c['r']-e['r'], c.get('ab'), c.get('slot')) for c in kc], vcasts=[(c['r']-e['r'], c.get('slot'), 'tgtchamp' if c.get('hits') else '') for c in vc],
            vseen=[ (v in ch[k]['seenBy'][jj]) for jj in range(max(0,i-6), i+1)], vsees=[(k in ch[v]['seenBy'][jj]) for jj in range(max(0,i-6), i+1)] ))
    return out
if __name__ == '__main__':
    dirs = [p for a in sys.argv[1:] for p in Path(a).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if o: rows += o
    print('prism-prism kills', len(rows), 'per game', len(rows)/len(dirs))
    big = [x for x in rows if x['gems'] >= 100]
    print('100+ bags', len(big))
    # min distance in last 15 rounds and distance profile
    prof = collections.defaultdict(list)
    for x in big:
        for t, dd in enumerate(x['dists']):
            if dd is not None: prof[t-len(x['dists'])+1].append(dd)
    print('mean dist by round offset (big):', {t: round(sum(v)/len(v),1) for t, v in sorted(prof.items())})
    vcd_ready = sum(1 for x in big if x['vcd'][0] == 0)
    print('victim stun (slot0) ready at death-1:', vcd_ready, 'of', len(big))
    ratio = sorted(x['kfoc']/max(1,x['vfoc']) for x in big); print('focus ratio k/v quartiles', [round(ratio[int(len(ratio)*q)],2) for q in (0.1,0.25,0.5,0.75,0.9)])
    import itertools
    for x in big[:12]: print(x)
