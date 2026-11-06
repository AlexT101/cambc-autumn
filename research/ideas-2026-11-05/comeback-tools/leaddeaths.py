#!/usr/bin/env python3
"""leaddeaths.py ANA COOKED_JSON: where and how the leader's bodies die after the g600 cook point (comebacks vs losses):
the half (nearer whose spawn), the victim's bag, the killer (camp or champion), nearby altar, and trailer deaths likewise."""
import json, gzip, sys, collections
ANA, CJ = sys.argv[1], sys.argv[2]
rows = [r for r in json.load(open(CJ)) if r['def'] == 'g600']
c = collections.Counter()
for r in rows:
    d = f"{ANA}/{r['game']}"
    m = json.load(open(f'{d}/meta.json')); R = json.load(gzip.open(f'{d}/rounds.json.gz'))
    ch = R['champions']; team = [x['team'] for x in ch]
    sp = [None, None]
    for x in ch:
        if sp[x['team']] is None: sp[x['team']] = (x['x'][0], x['y'][0])
    mp = json.load(open(f"{ANA}/maps/{m['map']['hash']}.json"))
    alt = [tuple(a) for a in mp['altars']]
    t = r['trail']; o = 1 - t; k = 'back' if r['won'] else 'lost'
    c[(k, 'n')] += 1
    for l in gzip.open(f'{d}/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] < r['round'] or e['k'] != 'death': continue
        v = e['v']; at = tuple(e['at']); g = e.get('gems', 0)
        side = 'leader' if team[v] == o else 'trailer'
        dl = max(abs(at[0] - sp[o][0]), abs(at[1] - sp[o][1])); dt = max(abs(at[0] - sp[t][0]), abs(at[1] - sp[t][1]))
        half = 'leaderhalf' if dl < dt else 'trailerhalf'
        near_alt = min(max(abs(at[0] - a[0]), abs(at[1] - a[1])) for a in alt) <= 3
        by = e.get('by'); camp = by is None or by >= len(team)
        c[(k, side, 'deaths')] += 1; c[(k, side, 'gems')] += g
        c[(k, side, half)] += 1; c[(k, side, half, 'gems')] += g
        c[(k, side, 'at_altar')] += near_alt; c[(k, side, 'at_altar', 'gems')] += g if near_alt else 0
        c[(k, side, 'camp')] += camp
        c[(k, side, 'bag100')] += g >= 100
for k in ('back', 'lost'):
    n = c[(k, 'n')]
    print(f'{k}: games {n}')
    for side in ('leader', 'trailer'):
        f = lambda *x: c[(k, side) + x] / max(1, n)
        print(f'  {side}: deaths {f("deaths"):.2f} gems {f("gems"):.1f} | on leader half {f("leaderhalf"):.2f} ({f("leaderhalf","gems"):.1f} gems) trailer half {f("trailerhalf"):.2f} ({f("trailerhalf","gems"):.1f}) | at an altar {f("at_altar"):.2f} ({f("at_altar","gems"):.1f}) | to camps {f("camp"):.2f} | bags 100+ {f("bag100"):.2f}')
