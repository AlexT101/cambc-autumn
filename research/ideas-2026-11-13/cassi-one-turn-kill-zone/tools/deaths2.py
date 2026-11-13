"""Live r8: late pair deaths to Fish's Vesper by the body actually hit (the death event without 'linked').
For the hit body B: distance to Vesper, sight, whether her Strength one- or two-shots it, and B's last actions;
and how often each body stands in her one-turn kill reach without dying. Run from ~/tmp-offload/fishr8/live/ext."""
import gzip, json, os, collections, statistics as st

rows = json.load(open('../rows-r8-all.json'))
cheb = lambda a, b: 99 if None in a or None in b else max(abs(a[0] - b[0]), abs(a[1] - b[1]))
LATE = 300
D = []; cig = 0
zone = collections.defaultdict(collections.Counter)
for d in sorted(os.listdir('.')):
    if not os.path.exists(d + '/meta.json'): continue
    m = json.load(open(d + '/meta.json')); key = os.path.basename(m['source']).split('.')[0]
    if key not in rows: continue
    r = rows[key]; P = m['draft']['picks']
    cand = [t for t in (0, 1) if sorted(P[t]) == sorted(r['our_picks']) and sorted(P[1 - t]) == sorted(r['opp_picks'])]
    if len(cand) != 1: continue
    us = cand[0]
    ch = {c['id']: c for c in m['champions']}
    ours = {c['name']: c['id'] for c in m['champions'] if c['team'] == us}
    fish = {c['name']: c['id'] for c in m['champions'] if c['team'] != us}
    if 'Cassi' not in ours or 'Vesper Vale' not in fish: continue
    cig += 1
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt'))
    rnd = R['round']; idx = {v: i for i, v in enumerate(rnd)}
    C = {c['id']: c for c in R['champions']}
    vid = fish['Vesper Vale']; ves = C[vid]
    evs = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    kills = [e for e in evs if e['k'] == 'death' and e['v'] in (ours['Cassi'], ours['Issac']) and 'linked' not in e
             and e['r'] >= LATE and e.get('by') == vid]
    for e in kills:
        i = idx.get(e['r'])
        if i is None or i < 12: continue
        B = C[e['v']]; Pn = C[ours['Issac'] if e['v'] == ours['Cassi'] else ours['Cassi']]
        rec = dict(game=d, r=e['r'], body=ch[e['v']]['name'], win=r['result'] == 'win', map=r['map'])
        for k in range(1, 11):
            j = i - k
            pb = (B['x'][j], B['y'][j]); pv = (ves['x'][j], ves['y'][j]); pp = (Pn['x'][j], Pn['y'][j])
            hp = B['hp'][j] + B['shield'][j]
            rec[k] = dict(d=cheb(pb, pv), dp=cheb(pp, pv), dbp=cheb(pb, pp), hp=B['hp'][j], mx=B['maxHp'][j], s=ves['str'][j],
                          one=ves['str'][j] >= hp, two=2 * ves['str'][j] >= hp, bseen=vid in (B['sees'][j] or []),
                          pseen=vid in (Pn['sees'][j] or []), cd0=ves['cd0'][j], cd1=ves['cd1'][j], ok=bool(B['alive'][j] and ves['alive'][j]))
        # B's last 3 turns: what it did
        rec['acts'] = [(x['r'], x['k'], x.get('ab')) for x in evs if x.get('a') == e['v'] and e['r'] - 3 <= x['r'] <= e['r']]
        D.append(rec)
    # zone occupancy by body: Vesper alive and seen by the body, her one-turn kill on the body possible:
    # one basic kills and d <= 5 (dash + attack) or two basics kill and d <= 3 (attack, reset, attack)
    kr = [e2['r'] for e2 in kills]
    for name in ('Cassi', 'Issac'):
        B = C[ours[name]]; prev = False
        for j, rr in enumerate(rnd):
            if rr < LATE or not B['alive'][j] or not ves['alive'][j]: prev = False; continue
            zone[name]['rounds'] += 1
            hp = B['hp'][j] + B['shield'][j]; dd = cheb((B['x'][j], B['y'][j]), (ves['x'][j], ves['y'][j]))
            seen = vid in (B['sees'][j] or [])
            inz = seen and ((ves['str'][j] >= hp and dd <= 5) or (2 * ves['str'][j] >= hp and dd <= 3))
            # the wider two-turn zone: two basics kill and d <= 6 (walk+dash, then walk+reset+attack ... )
            inz2 = seen and 2 * ves['str'][j] >= hp and dd <= 6
            for tag, z in (('one', inz), ('two6', inz2)):
                if z:
                    zone[name][tag] += 1
            if inz2 and not prev:
                zone[name]['entries'] += 1
                zone[name]['entries_die'] += any(rr < x <= rr + 8 for x in kr)
            prev = inz2

print(f'C&I games with Fish Vesper {cig}; late pair deaths to her by body hit:', collections.Counter(x['body'] for x in D))
for body in ('Cassi', 'Issac'):
    xs0 = [x for x in D if x['body'] == body]
    print(f'== {body} hit: {len(xs0)} ({len(xs0)/cig:.2f}/game), games won {sum(x["win"] for x in xs0)}')
    for k in (1, 2, 3, 4, 6, 8, 10):
        xs = [x[k] for x in xs0 if x[k]['ok']]
        if not xs: continue
        dd = [x['d'] for x in xs]
        print(f' k={k:2d} n={len(xs)} d med {st.median(dd)} <=3 {sum(v<=3 for v in dd)} <=5 {sum(v<=5 for v in dd)} <=6 {sum(v<=6 for v in dd)} <=8 {sum(v<=8 for v in dd)}'
              f' | body sees her {sum(x["bseen"] for x in xs)} partner {sum(x["pseen"] for x in xs)} either {sum(x["bseen"] or x["pseen"] for x in xs)}'
              f' | one-shot {sum(x["one"] for x in xs)} two-shot {sum(x["two"] for x in xs)} | hp/max med {st.median(x["hp"]/x["mx"] for x in xs):.2f}'
              f' | str med {st.median(x["s"] for x in xs):.0f} mx med {st.median(x["mx"] for x in xs):.0f} | d(body,partner) med {st.median(x["dbp"] for x in xs)}'
              f' | dash rdy {sum(x["cd1"]==0 for x in xs)} reset rdy {sum(x["cd0"]==0 for x in xs)}')
    a = collections.Counter()
    for x in xs0:
        for t in set((q[1], q[2]) for q in x['acts']): a[t] += 1
    print(' acts in last 3 rounds (games with):', a.most_common(10))
for name in zone:
    z = zone[name]
    print(f'{name}: late rounds alive {z["rounds"]} ({z["rounds"]/cig:.0f}/game); one-turn kill zone {z["one"]/cig:.1f} rounds/game; '
          f'two-turn zone (2 basics, d<=6) {z["two6"]/cig:.1f} rounds/game, entries {z["entries"]/cig:.2f}/game, followed by her kill on that body within 8 rounds {z["entries_die"]} ({z["entries_die"]/max(1,z["entries"])*100:.0f}%)')
json.dump(D, open(os.path.expanduser('~/tmp-offload/cassizone/deaths2.json'), 'w'))
