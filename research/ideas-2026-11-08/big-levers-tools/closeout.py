# Close-out: from the first round a side owns >= TH gems (tributed + carried), what happens until the game ends.
# For each side that crosses (ours in losses = blown close-outs; ours in wins; theirs in both), the state at the
# crossing (tributed, carried, bags per champion, carrier distance to the nearest altar, alive) and the outcome:
# rounds to finish, bags lost to kills, tribute cancels. usage: closeout.py TH OUT.pkl
import json, gzip, os, sys, pickle, collections
import numpy as np
TH = int(sys.argv[1])
ana = os.environ.get('ANA', os.path.expanduser('~/tmp-offload/bigl/ana'))
LOCAL = os.environ.get('LOCAL')  # substring of local batch source paths: CAND side = team A in -12 files
games = {} if LOCAL else json.load(open(os.path.expanduser('~/tmp-offload/bigl/games.json')))
idx = json.load(open(ana + '/index.json'))['games']
rows = []; done = set()
for g in idx:
    m = os.path.basename(g['source']).split('.')[0]; gm = games.get(m)
    if LOCAL:
        if LOCAL not in g['source']: continue
        a = g['source'].endswith('-12.repl26a')
        gm = dict(side='a' if a else 'b', result='win' if (g['winner'] == 0) == a else 'loss', opp_name='local', map=m)
    if not gm or g['dir'] in done: continue
    done.add(g['dir'])
    d = ana + '/' + g['dir']
    meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
    mp = json.load(open(ana + '/maps/' + os.path.basename(meta['mapFile'])))
    altars = mp['altars']
    us = 0 if gm['side'] == 'a' else 1
    n = len(R['round'])
    trib = np.array(R['gems'], float)
    car = np.zeros((2, n))
    for c in R['champions']: car[c['team']] += np.array(c['gems'], float)
    own = trib + car
    ev = None
    for t in (0, 1):
        hit = np.where(own[t] >= TH)[0]
        if not len(hit): continue
        i = int(hit[0]); r0 = R['round'][i]
        won = (gm['result'] == 'win') == (t == us)
        bags = []
        for c in R['champions']:
            if c['team'] != t or not c['alive'][i] or c['x'][i] is None: continue
            gms = c['gems'][i]
            if gms <= 0: continue
            dist = min(max(abs(c['x'][i] - a[0]), abs(c['y'][i] - a[1])) for a in altars) if altars else 99
            bags.append((gms, dist, c['chan'][i]))
        if ev is None:
            ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
        team = {c['id']: c['team'] for c in meta['champions']}
        after = [e for e in ev if e['r'] >= r0]
        lost_bags = sum(e.get('gems', 0) for e in after if e['k'] == 'death' and team[e['v']] == t)
        deaths = sum(1 for e in after if e['k'] == 'death' and team[e['v']] == t and not e.get('linked'))
        kills = sum(1 for e in after if e['k'] == 'death' and team[e['v']] != t and not e.get('linked') and e.get('by') is not None)
        canc = collections.Counter(e.get('cause') for e in after if e['k'] == 'tribute_cancel' and team[e['a']] == t)
        canc_g = collections.Counter()
        for e in after:
            if e['k'] == 'tribute_cancel' and team[e['a']] == t: canc_g[e.get('cause')] += e.get('gems', 0)
        tstarts = sum(1 for e in after if e['k'] == 'tribute_start' and team[e['a']] == t)
        opp_own = own[1 - t][i]; opp_trib = trib[1 - t][i]
        rows.append(dict(dir=g['dir'], ours=t == us, won=won, r0=r0, end=n, trib=trib[t][i], car=car[t][i], bags=bags,
                         opp_trib=opp_trib, opp_own=opp_own, lost_bags=lost_bags, deaths=deaths, kills=kills,
                         canc=dict(canc), canc_g=dict(canc_g), tstarts=tstarts, opp=gm['opp_name'], map=gm['map'],
                         copies=g.get('copies', 1), alive=sum(1 for c in R['champions'] if c['team'] == t and c['alive'][i]),
                         opp_alive=sum(1 for c in R['champions'] if c['team'] != t and c['alive'][i])))
pickle.dump(rows, open(sys.argv[2], 'wb')); print(len(rows))
