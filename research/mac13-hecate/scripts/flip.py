# flip.py EXTRACT_DIR: games where the eventual loser made a winning tribute attempt: what became of the bag
import gzip, json, glob, sys, collections
D = sys.argv[1]; out = collections.Counter(); ex = []
for d in glob.glob(D + '/*/'):
    try:
        M = json.load(open(d + 'meta.json')); R = json.load(gzip.open(d + 'rounds.json.gz'))
    except Exception: continue
    team = {c['id']: c['team'] for c in M['champions']}; name = {c['id']: c['name'] for c in M['champions']}
    g = R['gems']; r0 = R['round'][0]; last = len(R['round']) - 1
    W = 0 if g[0][last] > g[1][last] else 1; L = 1 - W
    ev = [json.loads(l) for l in gzip.open(d + 'events.jsonl.gz', 'rt')]
    att = None; cancels = collections.Counter()
    for e in ev:
        if e['k'] == 'tribute_start' and team[e['a']] == L and e['gems'] + g[L][max(0, e['r'] - r0)] >= 1000:
            if att is None: att = (e['r'], e['a'], e['gems'])
        if att and e['k'] == 'tribute_cancel' and e['a'] == att[1]: cancels[e.get('cause')] += 1
        if att and e['k'] == 'death' and e['v'] == att[1] and e['gems'] >= att[2] // 2:
            out['carrier killed, bag to ' + ('enemy' if e.get('gemsTo') else 'camp')] += 1
            ex.append((d.split('/')[-2], att, e['r'], name.get(e.get('by')), dict(cancels), R['round'][last])); att = 'done'; break
    if att and att != 'done': out['other (round limit / enemy won first)'] += 1; ex.append((d.split('/')[-2], att, None, None, dict(cancels), R['round'][last]))
print(out)
for x in ex[:40]: print(x)
