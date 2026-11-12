"""Live r7: how our deaths to Mite's Vesper happen. Per death (Vesper's kill or another's): victim, health and bag,
Vesper's range and whether the victim / any of us saw her in the rounds before, numbers within 5, the fight's
length (rounds since her first hit on the victim), and the victim's channel. Writes rows to
~/tmp-offload/mitere/vdeath.jsonl.gz and prints summaries. Index i of rounds.json = end of round i+1."""
import sys, os, json, gzip, collections
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml
OUT = os.path.expanduser('~/tmp-offload/mitere/vdeath.jsonl.gz')
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def one(sd):
    g = ml.load(sd)
    if g is None: return []
    m = g['mite']; o = 1 - m; meta = g['meta']; rd = g['rd']
    name = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    C = {c['id']: c for c in rd['champions']}
    V = [c for c in name if team[c] == m and name[c] == 'Vesper Vale']
    if not V: return []
    v = V[0]; nR = len(rd['round'])
    ours = [c for c in name if team[c] == o]; theirs = [c for c in name if team[c] == m]
    def at(c, i):
        cc = C[c]
        return (cc['x'][i], cc['y'][i]) if 0 <= i < nR and cc['alive'][i] and cc['x'][i] is not None else None
    hits = collections.defaultdict(list)  # victim -> [(round, attacker, dmg)]
    for e in g['ev']:
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            for t, d in e['dmg']:
                if t in team and team[t] == o: hits[t].append((e['r'], e['a'], d))
    rows = []
    for e in g['ev']:
        if e['k'] != 'death' or e.get('v') not in team or team[e['v']] != o or e.get('linked') is not None: continue
        vic = e['v']; r = e['r']; i0 = r - 2  # start of the death round
        if i0 < 12: continue
        cv = C[vic]; cV = C[v]
        row = {'mid': g['mid'], 'r': r, 'vic': name[vic], 'by_v': e.get('by') == v, 'by': name.get(e.get('by'), 'camp'),
               'cause': e.get('cause'), 'win_mite': g['win'], 'gems': e.get('gems', 0),
               'hp0': cv['hp'][i0] / cv['maxHp'][i0], 'hpabs0': cv['hp'][i0], 'maxhp': cv['maxHp'][i0],
               'vstr': cV['str'][i0], 'vhp': cV['hp'][i0] / max(1, cV['maxHp'][i0]), 'chan0': cv['chan'][i0],
               'vic_str': cv['str'][i0]}
        # range and sight, k rounds before the death round's start
        dist, seen_v, seen_any = [], [], []
        for k in range(0, 11):
            i = i0 - k; pv = at(vic, i); pV = at(v, i)
            dist.append(cheb(pv, pV) if pv and pV else None)
            seen_v.append(v in (cv['sees'][i] or []))
            seen_any.append(any(v in (C[c]['sees'][i] or []) for c in ours if at(c, i)))
        row.update(dist=dist, seen_v=seen_v, seen_any=seen_any)
        row['hp5'] = cv['hp'][i0 - 5] / cv['maxHp'][i0 - 5] if cv['alive'][i0 - 5] else None
        row['gems5'] = cv['gems'][i0 - 5] if cv['alive'][i0 - 5] else None
        pv = at(vic, i0)
        if pv:
            row['mites5'] = sum(1 for c in theirs if at(c, i0) and cheb(at(c, i0), pv) <= 5)
            row['ours5'] = sum(1 for c in ours if c != vic and at(c, i0) and cheb(at(c, i0), pv) <= 5)
        H = [h for h in hits[vic] if r - 15 <= h[0] <= r]
        Hv = [h for h in H if h[1] == v]
        row['v_first_hit'] = r - min(h[0] for h in Hv) if Hv else None
        row['any_first_hit'] = r - min(h[0] for h in H) if H else None
        row['dmg_v'] = sum(h[2] for h in H if h[1] == v); row['dmg_all'] = sum(h[2] for h in H)
        row['dmg_v_last'] = sum(h[2] for h in H if h[1] == v and h[0] == r)
        # did the victim attack in the 3 rounds before (who)
        row['vic_attacked'] = sorted({name.get(x.get('tgt'), 'camp') if x.get('tgt') in team else 'camp'
                                      for x in g['ev'] if x['k'] == 'attack' and x.get('a') == vic and r - 3 <= x['r'] <= r})
        rows.append(row)
    return rows

if __name__ == '__main__':
    R = []
    with Pool(8) as P:
        for rr in P.imap_unordered(one, ml.dirs('live'), chunksize=4): R.extend(rr)
    with gzip.open(OUT, 'wt') as f:
        for r in R: f.write(json.dumps(r) + '\n')
    print(len(R), 'deaths written to', OUT)
