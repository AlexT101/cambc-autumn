import gzip, json, sys, os
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
ROOT = sys.argv[1]; batch = sys.argv[2]
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    p = os.path.join(ROOT, d)
    m = json.load(open(p + '/meta.json'))
    mp = json.load(open(os.path.join(p, m['mapFile'])))
    R = json.load(gzip.open(p + '/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    W = m['result']['winner']
    champs = R['champions']; ci = {c['id']: i for i, c in enumerate(champs)}
    name = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    sp = mp['spawn']; spc = [((s['minX']+s['maxX'])/2, (s['minY']+s['maxY'])/2) for s in sp]
    rounds = R['round']; ridx = {r: i for i, r in enumerate(rounds)}
    # damage log: (round, attacker, victim, dmg)
    dlog = []
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'dmg' in e:
            for v, dm in e['dmg']: dlog.append((e['r'], e['a'], v, dm))
    out = []
    for e in ev:
        if e['k'] != 'death': continue
        v = e['v']; r = e['r']; t = team[v]
        i = ridx.get(r - 1, ridx.get(r))
        if i is None: continue
        vp = e['at']
        def pos(c):
            cc = champs[ci[c]]
            if not cc['alive'][i] or cc['x'][i] is None: return None
            return (cc['x'][i], cc['y'][i])
        en4 = en8 = al4 = al8 = 0
        for c in team:
            if c == v: continue
            q = pos(c)
            if q is None: continue
            dd = cheb(q, vp)
            if team[c] != t:
                en4 += dd <= 4; en8 += dd <= 8
            elif e.get('linked') != c:
                al4 += dd <= 4; al8 += dd <= 8
        att = {a for (rr, a, vv, dm) in dlog if vv == v and r - 10 <= rr <= r and team.get(a, t) != t}
        # allies of victim who damaged enemies within 10 rounds within 8 of victim
        helpers = {a for (rr, a, vv, dm) in dlog if r - 10 <= rr <= r and team.get(a) == t and team.get(vv) != t and a != v}
        cc = champs[ci[v]]
        dm_own = cheb(vp, spc[t]); dm_en = cheb(vp, spc[1 - t])
        out.append(dict(r=r, v=name[v], won=(t == W), gems=e['gems'], cause=e.get('cause'), camp=('camp' in e and 'by' not in e),
                        by=name.get(e.get('by')), byfoc=(champs[ci[e['by']]]['foc'][i] if e.get('by') in ci else None), vfoc=cc['foc'][i], en4=en4, en8=en8, al4=al4, al8=al8, natt=len(att), nhelp=len(helpers),
                        half='own' if dm_own < dm_en else 'enemy', chan=cc['chan'][i], hp=e.get('hp')))
    return out
if __name__ == '__main__':
    idx = json.load(open(os.path.join(ROOT, 'index.json')))
    dirs = sorted({g['dir'] for g in idx['games'] if batch in g['source'] and g.get('ok')})
    with ProcessPoolExecutor(16) as ex:
        rows = [x for r in ex.map(one, dirs, chunksize=8) for x in r]
    json.dump(rows, open(sys.argv[3], 'w'))
    print(len(rows))
    print('  victim types', collections.Counter(x[2] for x in rr).most_common(8))
    print('  killer types', collections.Counter(x[7] for x in rr).most_common(8))
