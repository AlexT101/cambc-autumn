"""Live r8 games: our C&I deaths to Fish's Vesper, the rounds before them, and how often a one-turn-kill zone
would fire without a death. Run from ~/tmp-offload/fishr8/live/ext."""
import gzip, json, os, collections, statistics as st, sys

rows = json.load(open('../rows-r8-all.json'))
LATE = int(sys.argv[1]) if len(sys.argv) > 1 else 300
cheb = lambda a, b: 99 if None in a or None in b else max(abs(a[0] - b[0]), abs(a[1] - b[1]))

ng = 0; cig = 0
deaths = []          # per late C&I death to Vesper
zone_rounds = collections.Counter(); zone_deaths = collections.Counter(); cassi_rounds = 0
entries = collections.Counter(); entry_deaths = collections.Counter()
other_killers = collections.Counter()
for d in sorted(os.listdir('.')):
    if not os.path.exists(d + '/meta.json'): continue
    m = json.load(open(d + '/meta.json'))
    key = os.path.basename(m['source']).split('.')[0]
    if key not in rows: continue
    r = rows[key]; P = m['draft']['picks']
    cand = [t for t in (0, 1) if sorted(P[t]) == sorted(r['our_picks']) and sorted(P[1 - t]) == sorted(r['opp_picks'])]
    if len(cand) != 1: continue
    us = cand[0]; ng += 1
    ch = {c['id']: c for c in m['champions']}
    ours = {c['name']: c['id'] for c in m['champions'] if c['team'] == us}
    fish = {c['name']: c['id'] for c in m['champions'] if c['team'] != us}
    if 'Cassi' not in ours: continue
    cig += 1
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt'))
    rnd = R['round']; idx = {v: i for i, v in enumerate(rnd)}
    C = {c['id']: c for c in R['champions']}
    ca, isa = C[ours['Cassi']], C[ours['Issac']]
    ves = C[fish['Vesper Vale']] if 'Vesper Vale' in fish else None
    evs = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    dr = [e for e in evs if e['k'] == 'death' and e['v'] in (ours['Cassi'], ours['Issac'])]
    for e in dr:
        if e['r'] < LATE: continue
        killer = ch[e['by']]['name'] if e.get('by') in ch else 'camp'
        if killer != 'Vesper Vale' or ves is None: other_killers[killer] += 1; continue
        i = idx.get(e['r'])
        if i is None or i < 25: continue
        rec = {'game': d, 'r': e['r'], 'victim': ch[e['v']]['name'], 'hp_at': e.get('hp')}
        for k in (1, 2, 3, 4, 5, 6, 8, 10):
            j = i - k
            pc = (ca['x'][j], ca['y'][j]); pi = (isa['x'][j], isa['y'][j]); pv = (ves['x'][j], ves['y'][j])
            rec[k] = dict(dc=cheb(pc, pv), di=cheb(pi, pv), dci=cheb(pc, pi), chp=ca['hp'][j], cmax=ca['maxHp'][j],
                          csh=ca['shield'][j], vstr=ves['str'][j], vcd0=ves['cd0'][j], vcd1=ves['cd1'][j],
                          seen=(fish['Vesper Vale'] in (ca['sees'][j] or [])) or (fish['Vesper Vale'] in (isa['sees'][j] or [])),
                          cseen=fish['Vesper Vale'] in (ca['sees'][j] or []), valive=ves['alive'][j], calive=ca['alive'][j],
                          stun=ca['stun'][j], ccd1=ca['cd1'][j], ccd0=ca['cd0'][j])
        # Cassi's own actions in the last 6 rounds
        acts = [x for x in evs if x.get('a') == ours['Cassi'] and e['r'] - 6 <= x['r'] <= e['r']]
        rec['acts'] = [(x['r'], x['k'], x.get('ab')) for x in acts]
        deaths.append(rec)
    # zone frequency: rounds where Cassi alive off spawn, Vesper alive & seen by the pair, 2*str >= hp+shield
    if ves is None: continue
    death_rounds = sorted(e['r'] for e in dr if e['r'] >= LATE and ch.get(e.get('by'), {}).get('name') == 'Vesper Vale')
    inz_prev = {Z: False for Z in (3, 4, 5, 6, 7, 8)}
    for j, rr in enumerate(rnd):
        if rr < LATE or not ca['alive'][j] or not ves['alive'][j]: inz_prev = {Z: False for Z in inz_prev}; continue
        cassi_rounds += 1
        seen = (fish['Vesper Vale'] in (ca['sees'][j] or [])) or (fish['Vesper Vale'] in (isa['sees'][j] or []))
        lethal2 = 2 * ves['str'][j] >= ca['hp'][j] + ca['shield'][j]
        dc = cheb((ca['x'][j], ca['y'][j]), (ves['x'][j], ves['y'][j]))
        soon = any(rr < dd <= rr + 6 for dd in death_rounds)
        for Z in inz_prev:
            inz = seen and lethal2 and dc <= Z
            if inz:
                zone_rounds[Z] += 1; zone_deaths[Z] += soon
                if not inz_prev[Z]: entries[Z] += 1; entry_deaths[Z] += soon
            inz_prev[Z] = inz

print(f'games {ng}, with our C&I {cig}, late (r>={LATE}) C&I deaths to Vesper {len(deaths)} ({len(deaths)/max(cig,1):.2f}/C&I game); other killers {dict(other_killers)}')
print('victim', collections.Counter(x['victim'] for x in deaths))
for k in (1, 2, 3, 4, 5, 6, 8, 10):
    xs = [x[k] for x in deaths if x[k]['calive'] and x[k]['valive']]
    if not xs: continue
    dc = [x['dc'] for x in xs]
    print(f'k={k:2d} n={len(xs)} dCassi med {st.median(dc)} <=3 {sum(v<=3 for v in dc)} <=5 {sum(v<=5 for v in dc)} <=6 {sum(v<=6 for v in dc)} <=8 {sum(v<=8 for v in dc)} | seen {sum(x["seen"] for x in xs)} cseen {sum(x["cseen"] for x in xs)} | 2str>=hp {sum(2*x["vstr"]>=x["chp"]+x["csh"] for x in xs)} str>=hp {sum(x["vstr"]>=x["chp"]+x["csh"] for x in xs)} | Cassi hp/max med {st.median(x["chp"]/x["cmax"] for x in xs):.2f} | dCI med {st.median(x["dci"] for x in xs)} | V dash ready {sum(x["vcd1"]==0 for x in xs)} reset ready {sum(x["vcd0"]==0 for x in xs)} | C stun ready {sum(x["ccd1"]==0 for x in xs)}')
# first round (going back) at which a zone rule seen & 2str>=hp & d<=Z fired continuously up to death
for Z in (5, 6, 7, 8):
    leads = []
    for x in deaths:
        lead = 0
        for k in (1, 2, 3, 4, 5, 6, 8, 10):
            y = x[k]
            if y['calive'] and y['valive'] and y['seen'] and 2 * y['vstr'] >= y['chp'] + y['csh'] and y['dc'] <= Z: lead = k
        leads.append(lead)
    c = collections.Counter(leads)
    print(f'Z={Z}: earliest firing (rounds before death, among 1..10) {sorted(c.items())}; never {c[0]}')
print('zone frequency, Cassi late rounds alive:', cassi_rounds)
for Z in sorted(zone_rounds):
    print(f'  Z={Z}: {zone_rounds[Z]/cassi_rounds*100:.1f}% of rounds, {zone_rounds[Z]/max(cig,1):.0f} rounds/game; entries {entries[Z]} ({entries[Z]/max(cig,1):.1f}/game), entries with a death to her within 6 rounds {entry_deaths[Z]} ({entry_deaths[Z]/max(entries[Z],1)*100:.0f}%)')
acts = collections.Counter()
for x in deaths:
    for a in x['acts']: acts[(a[1], a[2])] += 1
print('Cassi acts in last 6 rounds:', acts.most_common(12))
json.dump(deaths, open(os.path.expanduser('~/tmp-offload/cassizone/deaths.json'), 'w'))
