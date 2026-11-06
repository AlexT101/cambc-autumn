"""Back-to-back deaths in local games by the victim's branch (its D line) at its last turn before them.
python3 b2b3.py GAMES.jsonl (each line: dir of the extraction, us; meta.json's source is the replay zip)"""
import collections, gzip, json, sys, zipfile, re
from concurrent.futures import ProcessPoolExecutor

def game(g):
    d, us = g['dir'], g['us']
    meta = json.load(open(d + '/meta.json'))
    src = '/home/ubuntu/cambc-autumn/' + meta['source']
    D = {}
    try:
        with zipfile.ZipFile(src) as z:
            for t, name in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
                for l in z.read(name).decode('latin1').splitlines():
                    if l.startswith('D '):
                        p = l.split()
                        if len(p) >= 4: D[(int(p[1]), int(p[2]))] = p[3]
    except Exception:
        return []
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt'))
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    ri_of = {r: i for i, r in enumerate(R['round'])}
    champs = R['champions']; team = {c['id']: c['team'] for c in champs}
    tseq = {}
    for e in ev:
        if e.get('a') in team and e.get('t', -1) >= 0: tseq.setdefault((e['r'], e['a']), e['s'])
    hitby = collections.defaultdict(float)
    for e in ev:
        dd = e.get('dmg')
        if isinstance(dd, list):
            for x in dd:
                if x[0] in team: hitby[(e['r'], e.get('a'), x[0])] += x[1]
    out = []
    for e in ev:
        if e['k'] != 'death' or e.get('linked') is not None or e.get('by') not in team: continue
        v, k, r = e['v'], e['by'], e['r']
        if team[v] == team[k]: continue
        s1 = tseq.get((r - 1, k)); sv1 = tseq.get((r - 1, v)); sv2 = tseq.get((r, v))
        if s1 is None or sv1 is None or hitby[(r - 1, k, v)] <= 0: continue
        b2b = sv1 < s1 and (sv2 is None or sv2 > e['s'])
        if not b2b: continue
        run = 0
        while D.get((r - 1 - run, v)) == 'R': run += 1
        i0 = ri_of.get(r - 1 - run)
        C = {c['id']: c for c in champs}
        fr = (C[v]['hp'][i0] or 0) / max(1, C[v]['maxHp'][i0] or 1) if i0 is not None else -1
        out.append(dict(ours=team[v] == us, br=D.get((r - 1, v), '?'), br2=D.get((r - 2, v), '?'), run=run, hp_at_start=fr))
    return out

if __name__ == '__main__':
    gs = [json.loads(l) for l in open(sys.argv[1])]
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(game, gs, chunksize=8): rows += o
    for side, name in ((True, 'cand'), (False, 'ref')):
        xs = [x for x in rows if x['ours'] == side]
        c = collections.Counter(x['br'] for x in xs)
        rs = [x for x in xs if x['br'] == 'R']
        runs = collections.Counter(min(x['run'], 6) for x in rs)
        print(f"  {name} R deaths: retreat turns before death " + ', '.join(f"{k}{'+' if k == 6 else ''}: {runs[k]}" for k in sorted(runs)) + f"; hp share when the retreat began: mean {sum(x['hp_at_start'] for x in rs)/max(1,len(rs)):.2f}, <0.3 {sum(x['hp_at_start'] < 0.3 for x in rs)}, 0.3-0.6 {sum(0.3 <= x['hp_at_start'] < 0.6 for x in rs)}, >=0.6 {sum(x['hp_at_start'] >= 0.6 for x in rs)}")
        print(f"{name}: b2b deaths {len(xs)} ({len(xs)/len(gs):.3f}/game); branch at last turn: " + ', '.join(f"{b} {n} ({100*n/len(xs):.0f}%)" for b, n in c.most_common(10)))
