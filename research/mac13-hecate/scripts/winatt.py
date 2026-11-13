# winatt.py EXTRACT_DIR: winning tribute attempts (bag >= 1000 - team score) and what became of them
import gzip, json, glob, sys, collections, statistics as S
D = sys.argv[1]; n = 0; lost_after = 0; first_gap = []; tries = []; noatt = 0; enda = collections.Counter()
for d in glob.glob(D + '/*/'):
    try:
        M = json.load(open(d + 'meta.json')); R = json.load(gzip.open(d + 'rounds.json.gz'))
    except Exception: continue
    n += 1
    team = {c['id']: c['team'] for c in M['champions']}
    g = R['gems']; r0 = R['round'][0]; last = len(R['round']) - 1
    W = 0 if g[0][last] > g[1][last] else 1
    ev = [json.loads(l) for l in gzip.open(d + 'events.jsonl.gz', 'rt')]
    first = {}; cnt = collections.Counter()
    for e in ev:
        if e['k'] == 'tribute_start':
            t = team[e['a']]; sc = g[t][max(0, e['r'] - r0)]
            if e['gems'] + sc >= 1000:
                cnt[t] += 1
                first.setdefault(t, e['r'])
    if W in first: first_gap.append(R['round'][last] - first[W]); tries.append(cnt[W])
    else: noatt += 1
    if (1 - W) in first: lost_after += 1
    enda[R['round'][last] >= 2000] += 1
print('games', n, 'winner made a winning attempt', len(first_gap), 'median gap to end', S.median(first_gap), 'mean', round(S.mean(first_gap)),
      'attempts median', S.median(tries), 'mean', round(S.mean(tries), 1))
print('loser had made a winning attempt (and lost)', lost_after, 'winner never made one', noatt, 'reached r2000', enda[True])
q = sorted(first_gap); print('gap quartiles', q[len(q)//4], q[len(q)//2], q[3*len(q)//4], q[9*len(q)//10])
