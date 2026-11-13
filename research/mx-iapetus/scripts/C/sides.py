# Captures by side for CAND (bot 0) vs REF (bot 1) in extracted A/B games: capture gems per game by the capturing
# team's static home weight bin (own h=1, near h in [.5,1), far h<.5), and of those, the ones taken while 2+ enemy
# bodies were dead; deaths and gems carried at death; wins. Usage: sides.py ANALYSIS_DIR
import json, gzip, sys, collections, os
sys.argv, ADIR = sys.argv[:1], sys.argv[1].rstrip('/') + '/'
from oracle import mapinfo
idx = json.load(open(ADIR + 'index.json'))['games']
S = collections.defaultdict(float); n = 0
for row in idx:
    d = row['dir']
    try:
        m = json.load(open(ADIR + d + '/meta.json'))
    except Exception:
        continue
    G = mapinfo(ADIR + m['mapFile'].replace('../', ''))
    gid = {g['id']: i for i, g in enumerate(G)}
    bot_of = {t: m['teams'][t]['bot'] for t in (0, 1)}  # team -> bot index
    R = json.load(gzip.open(ADIR + d + '/rounds.json.gz'))
    ri = {r: i for i, r in enumerate(R['round'])}
    ch = R['champions']
    team = {c['id']: c['team'] for c in ch}
    n += 1
    w = m['result']['winner']; S['win', bot_of[w]] += 1
    for line in gzip.open(ADIR + d + '/events.jsonl.gz', 'rt'):
        e = json.loads(line)
        if e['k'] == 'capture':
            t = e['team']; b = bot_of[t]; gems = sum(s[1] for s in e['shares'])
            i = gid.get(e['g'])
            if i is None: continue
            h = G[i]['home'][t]
            hb = 'own' if h >= 0.999 else 'near' if h >= 0.5 else 'far'
            j = ri.get(e['r'], 0)
            dead = sum(1 for c in ch if c['team'] != t and not c['alive'][j])
            S['cap', hb, b] += gems
            if dead >= 2: S['cap2dead', hb, b] += gems
        elif e['k'] == 'death':
            v = e['v']
            if v not in team: continue
            b = bot_of[team[v]]; S['deaths', b] += 1; S['deathgems', b] += e.get('gems', 0) or 0
print('games', n)
for k in sorted(set(k[:-1] for k in S)):
    c, r = S[k + (0,)], S[k + (1,)]
    print('%-22s CAND %8.1f  REF %8.1f  diff %+7.2f a game' % ('/'.join(map(str, k)), c / n, r / n, (c - r) / n))
