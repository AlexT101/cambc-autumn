"""mech.py STUDY.jsonl ANA CANDNAME: candidate vs base long-channel outcomes and rounds from a winning bag to the win.
Classes by the plan's zones (Chebyshev 10). Sides named from the replay file name (A-vs-B)."""
import json, gzip, sys, collections, statistics, os
study, ana, cand = sys.argv[1:4]
ix = json.load(open(f'{ana}/index.json'))['games']
names = {}
for g in ix:
    o = os.path.basename(g['source']).rsplit('-', 1)[1].split('.')[0]  # run_batched: -12 = bot 1 (CAND) is team A
    names[g['dir']] = ['cand', 'base'] if o == '12' else ['base', 'cand']
rows = [json.loads(l) for l in open(study)]
T = [r for r in rows if r['kind'] == 'trib']
for r in T: r['who'] = names[r['d']][r['team']]
band = lambda d: '1-8' if d <= 8 else '9-20' if d <= 20 else '21+'
cls = lambda r: '1zone' if r['nz'] == 1 else 'multi'
print('## channels: starts, completed %, cancels by cause (per start), carrier died %')
c = collections.defaultdict(collections.Counter)
for r in T:
    k = (cls(r), band(r['dur']), r['who'])
    c[k]['n'] += 1; c[k][r['res']] += 1; c[k]['died'] += r['died']; c[k]['gems'] += r['gems']
for k in sorted(c):
    x = c[k]; n = x['n']
    print(f"  {k[0]:6s} {k[1]:5s} {k[2]:4s} n={n:5d} done={100*x['end']/n:5.1f}% manual={100*x['cancel:manual']/n:5.1f}% stun={100*x['cancel:stun']/n:5.1f}% "
          f"lock={100*x['cancel:lock']/n:5.1f}% death={100*x['cancel:death']/n:4.1f}% none={100*x['none']/n:4.1f}% died={100*x['died']/n:4.1f}% meanbag={x['gems']/n:5.1f}")
print('## long channels (9+): enemies within 8 at start; completed %')
c = collections.defaultdict(lambda: [0, 0])
for r in T:
    if r['dur'] < 9: continue
    k = (cls(r), r['who'], min(r['en8'], 2)); c[k][0] += 1; c[k][1] += r['res'] == 'end'
for k in sorted(c): print(f"  {k} n={c[k][0]} done={100*c[k][1]/c[k][0]:.1f}%")
print('## long-channel gems banked per game-side')
gs = collections.Counter(); sides = collections.Counter()
for d, (a, b) in names.items(): sides[a] += 1; sides[b] += 1
for r in T:
    if r['dur'] >= 9 and r['res'] == 'end': gs[r['who']] += r['gems']
print('  ', {w: round(gs[w] / sides[w], 1) for w in sides})
print('## rounds from a winning bag to the win')
seen = set(); out = collections.defaultdict(list)
for g in ix:
    d = g['dir']
    if d in seen: continue
    seen.add(d)
    m = json.load(open(f'{ana}/{d}/meta.json')); R = json.load(gzip.open(f'{ana}/{d}/rounds.json.gz'))
    al = json.load(open(f"{ana}/maps/{m['map']['hash']}.json"))['altars']; na = len(al); z = list(range(na))
    def f(i):
        while z[i] != i: i = z[i]
        return i
    for i in range(na):
        for j in range(i + 1, na):
            if max(abs(al[i][0] - al[j][0]), abs(al[i][1] - al[j][1])) <= 10: z[f(i)] = f(j)
    nz = len({f(i) for i in range(na)}); N = len(R['round'])
    for t in (0, 1):
        cs = [c for c in R['champions'] if c['team'] == t]; ready = None
        for i in range(N):
            if R['gems'][t][i] >= 1000: break
            if any(R['gems'][t][i] + (c['gems'][i] or 0) >= 1000 for c in cs): ready = i; break
        if ready is None: continue
        end = next((i for i in range(ready, N) if R['gems'][t][i] >= 1000), None)
        out[('1zone' if nz == 1 else 'multi', names[d][t])].append((m['result']['winner'] == t, None if end is None else R['round'][end] - R['round'][ready]))
for k in sorted(out):
    v = out[k]; dl = sorted(x for _, x in v if x is not None)
    print(f"  {k} sides={len(v)} won={100*sum(w for w, _ in v)/len(v):.1f}% median={statistics.median(dl) if dl else None} "
          f"p75={dl[int(.75*len(dl))] if dl else None} over30={100*sum(x > 30 for x in dl)/max(1, len(dl)):.0f}%")
