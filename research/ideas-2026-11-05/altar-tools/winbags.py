#!/usr/bin/env python3
"""winbags.py ANA: winning bags (team tributed + carried >= 1000) that died, and the game after."""
import json, gzip, os, sys, collections
ANA = sys.argv[1]
c = collections.Counter()
for d in os.listdir(ANA):
    if not os.path.exists(f'{ANA}/{d}/meta.json'): continue
    m = json.load(open(f'{ANA}/{d}/meta.json'))
    mp = json.load(open(f"{ANA}/maps/{m['map']['hash']}.json"))
    kind = 'one' if len(mp['altars']) == 1 else 'multi'
    R = json.load(gzip.open(f'{ANA}/{d}/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(f'{ANA}/{d}/events.jsonl.gz', 'rt')]
    team = {ch['id']: ch['team'] for ch in m['champions']}
    ri = {r: i for i, r in enumerate(R['round'])}
    w = m['result']['winner']
    c[(kind, 'games')] += 1
    lost_team = set()
    for e in ev:
        if e['k'] != 'death' or not e.get('gems'): continue
        t = team[e['v']]; i = ri.get(e['r'] - 1, 0)
        if R['gems'][t][i] + e['gems'] >= 1000:
            c[(kind, 'winbag_died', 'by_champ' if e.get('by') is not None else 'by_camp')] += 1
            if t not in lost_team:
                lost_team.add(t); c[(kind, 'games_with_winbag_death')] += 1
                c[(kind, 'then_lost')] += w != t
for k in sorted(c, key=str): print(k, c[k])
