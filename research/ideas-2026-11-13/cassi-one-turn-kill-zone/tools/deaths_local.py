"""deaths2.py for local ab runs (extract.mjs output): python3 deaths_local.py EXT"""
import gzip, json, os, sys, collections, statistics as st
ext = sys.argv[1]
cheb = lambda a, b: 99 if None in a or None in b else max(abs(a[0] - b[0]), abs(a[1] - b[1]))
idx = json.load(open(ext + '/index.json'))['games']
D = []; cig = 0
for g in idx:
    us = 0 if g['source'].endswith('-12.repl26a') else 1
    d = ext + '/' + g['dir']
    m = json.load(open(d + '/meta.json'))
    ch = {c['id']: c for c in m['champions']}
    ours = {c['name']: c['id'] for c in m['champions'] if c['team'] == us}
    fish = {c['name']: c['id'] for c in m['champions'] if c['team'] != us}
    if 'Cassi' not in ours or 'Vesper Vale' not in fish: continue
    cig += 1
    vid = fish['Vesper Vale']
    evs = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    kills = [e for e in evs if e['k'] == 'death' and e['v'] in (ours['Cassi'], ours['Issac']) and 'linked' not in e and e['r'] >= 300 and e.get('by') == vid]
    if not kills: continue
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt')); ri = {v: i for i, v in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    ves = C[vid]
    for e in kills:
        i = ri.get(e['r'])
        if i is None or i < 12: continue
        B = C[e['v']]; cid = e['v']
        rec = dict(game=g['dir'], src=os.path.basename(g['source']), r=e['r'], body=ch[e['v']]['name'], handle=e['v'], us=us)
        for k in range(1, 11):
            j = i - k
            hp = B['hp'][j] + B['shield'][j]
            rec[k] = dict(d=cheb((B['x'][j], B['y'][j]), (ves['x'][j], ves['y'][j])), hp=B['hp'][j], mx=B['maxHp'][j], s=ves['str'][j],
                          one=ves['str'][j] >= hp, two=2 * ves['str'][j] >= hp, seen=vid in (B['sees'][j] or []), ok=bool(B['alive'][j] and ves['alive'][j]))
        dealt = 0
        for x in evs:
            if x.get('a') == cid and e['r'] - 6 <= x['r'] <= e['r'] and isinstance(x.get('dmg'), list): dealt += sum(v for t, v in x['dmg'])
        rec['dealt'] = dealt
        fd = [x['r'] for x in evs if e['r'] - 15 <= x['r'] <= e['r'] and isinstance(x.get('dmg'), list) and any(t == cid for t, v in x['dmg'])]
        rec['first_hit'] = e['r'] - min(fd) if fd else -1
        D.append(rec)
print(f'C&I games with an enemy Vesper {cig}; late pair deaths to her:', collections.Counter(x['body'] for x in D))
for body in ('Cassi', 'Issac'):
    xs0 = [x for x in D if x['body'] == body]
    if not xs0: continue
    print(f'== {body}: {len(xs0)} ({len(xs0)/cig:.3f}/game); dealt 0 champion damage in last 6 rounds: {sum(x["dealt"]==0 for x in xs0)}; first hit (rounds before death) {sorted(collections.Counter(x["first_hit"] for x in xs0).items())}')
    for k in (1, 2, 3, 4, 6, 8):
        xs = [x[str(k)] if str(k) in x else x[k] for x in xs0]
        xs = [x for x in xs if x['ok']]
        dd = [x['d'] for x in xs]
        print(f' k={k} n={len(xs)} d med {st.median(dd)} <=3 {sum(v<=3 for v in dd)} <=5 {sum(v<=5 for v in dd)} <=6 {sum(v<=6 for v in dd)} <=8 {sum(v<=8 for v in dd)} | sees {sum(x["seen"] for x in xs)} | one {sum(x["one"] for x in xs)} two {sum(x["two"] for x in xs)} | hp/max {st.median(x["hp"]/x["mx"] for x in xs):.2f} str {st.median(x["s"] for x in xs):.0f} mx {st.median(x["mx"] for x in xs):.0f}')
json.dump(D, open(ext + '.deaths.json', 'w'))
