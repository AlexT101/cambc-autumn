#!/usr/bin/env python3
"""How often a Fish non-Vesper 50+ carrier we see is isolated: numbers within radius R of the carrier, ours vs Fish's.

Episodes are runs of qualifying rounds (gaps up to 3 rounds merged), per carrier. For each, the spell's end
(spells-live.json), and whether we dealt damage to the carrier during the episode.
"""
import collections, gzip, json, os, statistics as st

import sys
EXT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/tmp-offload/fishr8/live/ext')
rows = json.load(open(sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/tmp-offload/fishr8/live/rows-r8-all.json')))
spells = json.load(open(sys.argv[3] if len(sys.argv) > 3 else os.path.expanduser('~/tmp-offload/bag-carrier-prey/spells-live.json')))
sp = collections.defaultdict(list)
for s in spells: sp[(s['game'], s['champ'])].append(s)
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
CONDS = {
    'A: 2+ ours<=6, Vesper>8': lambda no, fo, vd, nv: no >= 2 and vd > 8,
    'B: A + no other Fish within 8': lambda no, fo, vd, nv: no >= 2 and vd > 8 and fo == 0,
    'C: ours<=6 > Fish<=8 (carrier incl), Vesper>8': lambda no, fo, vd, nv: no > fo + 1 and vd > 8,
    'D: 1+ ours<=6, no other Fish within 8, Vesper>8': lambda no, fo, vd, nv: no >= 1 and vd > 8 and fo == 0,
}
eps = {k: [] for k in CONDS}; ng = 0; rounds = collections.Counter()
for d in sorted(os.listdir(EXT)):
    p = os.path.join(EXT, d)
    if not os.path.exists(p + '/meta.json'): continue
    m = json.load(open(p + '/meta.json'))
    key = os.path.basename(m['source']).split('.')[0]
    if key not in rows: continue
    r = rows[key]; P = m['draft']['picks']
    if 'our_picks' in r:
        cand = [t for t in (0, 1) if sorted(P[t]) == sorted(r['our_picks']) and sorted(P[1 - t]) == sorted(r['opp_picks'])]
    else:
        cand = [0 if r['side'] == 'a' else 1]
        r = dict(r, result='win' if m['result'].get('winner') == cand[0] else 'loss')
    if len(cand) != 1: continue
    us = cand[0]; ng += 1
    names = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
    R = json.load(gzip.open(p + '/rounds.json.gz', 'rt')); C = R['champions']; n = len(R['round']); rnd = R['round']
    ours = [c for c in C if c['team'] == us]; fish = [c for c in C if c['team'] != us]
    fv = [c for c in fish if names[c['id']] == 'Vesper Vale']
    dmg = collections.defaultdict(float)
    for l in gzip.open(p + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] in ('attack', 'cast') and 'dmg' in e and team.get(e['a']) == us:
            for v, x in e['dmg']: dmg[(v, e['r'])] += x
    for f in fish:
        nm = names[f['id']]
        if nm == 'Vesper Vale': continue
        # Cassi and Issac: the other body is the same kill, not a defender to count.
        twin = {'Cassi': 'Issac', 'Issac': 'Cassi'}.get(nm)
        cur = {k: None for k in CONDS}
        for k in range(n):
            ok = f['alive'][k] and f['gems'][k] >= 50 and any(f['id'] in (o['sees'][k] or []) for o in ours if o['alive'][k])
            vals = None
            if ok:
                pos = (f['x'][k], f['y'][k])
                vd = min([cheb((v['x'][k], v['y'][k]), pos) for v in fv if v['alive'][k]] or [99])
                no = sum(1 for o in ours if o['alive'][k] and cheb((o['x'][k], o['y'][k]), pos) <= 6)
                fo = sum(1 for g in fish if g is not f and g['alive'][k] and names[g['id']] not in ('Vesper Vale', twin)
                         and cheb((g['x'][k], g['y'][k]), pos) <= 8)
                vals = (no, fo, vd, 0)
            for c, fn in CONDS.items():
                hit = vals is not None and fn(*vals)
                if hit: rounds[c] += 1
                e = cur[c]
                if hit:
                    if e and rnd[k] - e['last'] <= 3: e['last'] = rnd[k]; e['n'] += 1; e['hp'].append(f['hp'][k] / f['maxHp'][k])
                    else:
                        cur[c] = e = dict(game=key, champ=nm, first=rnd[k], last=rnd[k], n=1, gems=f['gems'][k], hp=[f['hp'][k] / f['maxHp'][k]], res=r['result'])
                        eps[c].append(e)
    for c in CONDS:
        for e in eps[c]:
            if e['game'] != key or 'end' in e: continue
            s = [s for s in sp[(key, e['champ'])] if s['r0'] <= e['first'] <= s['r1']]
            e['end'] = s[0]['end'] if s else '?'
            e['spell'] = (key, e['champ'], s[0]['r0']) if s else None
            fid = [f['id'] for f in fish if names[f['id']] == e['champ']][0]
            e['dealt'] = sum(dmg[(fid, rr)] for rr in range(e['first'], e['last'] + 2))
print('games', ng)
for c, E in eps.items():
    ends = collections.Counter(e['end'] for e in E)
    print(f"{c}: {rounds[c]/ng:.1f} rounds/game, {len(E)/ng:.2f} episodes/game, mean len {st.mean(e['n'] for e in E) if E else 0:.1f}")
    print('    ends', {k: f"{v/len(E):.0%}" for k, v in ends.most_common()}, ' dealt>0', f"{sum(e['dealt']>0 for e in E)/max(1,len(E)):.0%}",
          ' hp median', round(st.median(st.mean(e['hp']) for e in E), 2) if E else None)
    sp_k = {e['spell'] for e in E if e['end'] == 'killed_by_us' and e['spell']}; sp_t = {e['spell'] for e in E if e['end'] == 'tribute' and e['spell']}
    print(f"    distinct spells: killed by us {len(sp_k)/ng:.2f}/game, tributed {len(sp_t)/ng:.2f}/game")
    trib = [e for e in E if e['end'] == 'tribute']
    print(f"    tributed episodes {len(trib)/ng:.2f}/game, their bag when first seen isolated {sum(e['gems'] for e in trib)/ng:.1f} gems/game")
    byc = collections.Counter(e['champ'] for e in E)
    print('    by champ', dict(byc.most_common()))
    for res in ('win', 'loss'):
        S = [e for e in E if e['res'] == res]
        if S: print(f"    {res}: {len(S)} eps, killed {sum(e['end']=='killed_by_us' for e in S)/len(S):.0%}, tributed {sum(e['end']=='tribute' for e in S)/len(S):.0%}")
