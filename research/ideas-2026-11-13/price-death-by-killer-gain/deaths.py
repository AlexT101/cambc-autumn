"""Our deaths in live Fish r8 games: who killed, what the killer gained, the victim's recent health, and
whether the fight was a trade (a Fish death within 6 rounds and 8 tiles).
    python3 deaths.py   (reads ~/tmp-offload/fishr8/live)"""
import gzip, json, os, collections, statistics as st
L = os.path.expanduser('~/tmp-offload/fishr8/live')
rows = json.load(open(f'{L}/rows-r8-all.json'))
E = json.load(open(f'{L}/ext/enums.json'))
HUNTER = {61, 63, 65}; TREAS = {19, 21, 23}; GREED = {73, 75, 77}
out = []
for d in sorted(os.listdir(f'{L}/ext')):
    p = f'{L}/ext/{d}'
    if not os.path.exists(p + '/meta.json'): continue
    m = json.load(open(p + '/meta.json'))
    key = os.path.basename(m['source']).split('.')[0]
    if key not in rows: continue
    r = rows[key]; P = m['draft']['picks']
    cand = [t for t in (0, 1) if sorted(P[t]) == sorted(r['our_picks']) and sorted(P[1 - t]) == sorted(r['opp_picks'])]
    if len(cand) != 1: continue
    us = cand[0]
    R = json.load(gzip.open(p + '/rounds.json.gz', 'rt'))
    rounds = R['round']; idx = {rr: i for i, rr in enumerate(rounds)}
    ch = {c['id']: c for c in R['champions']}
    name = {c['id']: c['name'] for c in m['champions']}
    evs = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    deaths = [e for e in evs if e.get('k') == 'death']
    for e in deaths:
        v = e['v']
        if ch[v]['team'] != us: continue
        rr = e['r']; i = idx.get(rr)
        if i is None: continue
        k = e.get('by')
        kc = ch.get(k) if k is not None else None
        def items(c, j):
            it = c['items'][j] if j >= 0 else []
            return {it[a] for a in range(0, len(it), 2)} if it else set()
        kit = items(kc, max(0, i - 1)) if kc else set()
        hunter = bool(kit & HUNTER); treas = bool(kit & TREAS); greed = bool(kit & GREED)
        kname = name.get(k, 'camp') if k is not None else 'camp'
        gain = None
        if kc and i >= 1: gain = kc['earned'][i] - kc['earned'][i - 1]
        hp = lambda j: ch[v]['hp'][j] / max(1, ch[v]['maxHp'][j]) if j >= 0 and ch[v]['alive'][j] else None
        trade = False; fish_dead_near = 0
        for f in deaths:
            if ch[f['v']]['team'] == us: continue
            if abs(f['r'] - rr) <= 6 and max(abs(f['at'][0] - e['at'][0]), abs(f['at'][1] - e['at'][1])) <= 8: fish_dead_near += 1
        out.append(dict(game=d, res=r['result'], r=rr, victim=name[v], killer=kname, kteam=(kc['team'] if kc else -1), hunter=hunter,
                        treas=treas, greed=greed, gain=gain, base=e.get('gold'), gems=e.get('gems', 0), hp1=hp(i - 1), hp3=hp(i - 3),
                        hp5=hp(i - 5), trade=fish_dead_near, kstr=(kc['str'][i] if kc else None), vmax=ch[v]['maxHp'][i]))
json.dump(out, open(os.path.expanduser('~/tmp-offload/pdkg/deaths.json'), 'w'))
print('our deaths', len(out), 'games', len({o['game'] for o in out}))
byk = collections.Counter((o['killer'], o['hunter']) for o in out)
for (kn, h), n in byk.most_common(12): print(f'  killer {kn:14s} hunter={h}: {n}')
fish = [o for o in out if o['kteam'] >= 0]
print('champion kills', len(fish), 'gain mean %.0f' % st.mean(o['gain'] for o in fish if o['gain'] is not None))
for h in (False, True):
    g = [o['gain'] for o in fish if o['hunter'] == h and o['gain'] is not None]
    if g: print(f'  hunter={h}: n={len(g)} gold gained mean {st.mean(g):.0f} median {st.median(g):.0f}')
for lab, sel in (('trade (a Fish death within 6r/8t)', lambda o: o['trade'] > 0), ('no trade', lambda o: o['trade'] == 0)):
    x = [o for o in fish if sel(o)]
    print(f'{lab}: {len(x)} ({len(x)/len(fish):.0%}); by hunter killer {sum(o["hunter"] for o in x)}')
for lab, sel in (('r<200', lambda o: o['r'] < 200), ('200-450', lambda o: 200 <= o['r'] < 450), ('450+', lambda o: o['r'] >= 450)):
    x = [o for o in fish if sel(o)]
    if x: print(f'{lab}: {len(x)}, hunter {sum(o["hunter"] for o in x)/len(x):.0%}, trade {sum(o["trade"]>0 for o in x)/len(x):.0%}, '
                f'hp3 median {st.median([o["hp3"] for o in x if o["hp3"] is not None]):.2f}, hp1 median {st.median([o["hp1"] for o in x if o["hp1"] is not None]):.2f}')
by_res = collections.defaultdict(list)
for o in fish: by_res[(o['game'], o['res'])].append(o)
for res in ('win', 'loss'):
    gs = [v for (g, rs), v in by_res.items() if rs == res]
    games = len({o['game'] for o in out if o['res'] == res})
    if gs: print(f'{res}: games with deaths {len(gs)}; hunter-kills per game {sum(sum(o["hunter"] for o in v) for v in gs)/max(1,games):.2f}; '
                 f'gold fed per game {sum(sum(o["gain"] or 0 for o in v) for v in gs)/max(1,games):.0f}')
