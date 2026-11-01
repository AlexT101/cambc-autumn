# Trace a group cycle: python3 trace_cycle.py <source substring> <r0> <r1> [group]
import sys, json
sys.path.insert(0, 'research/v66-replays/scripts/extract')
from common import *
src, r0, r1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
r = [g for g in games() if src in g['source']][0]
m = meta(r['dir']); mj = mapj(m); ev = events(r['dir']); R = rounds(r['dir'])
name = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
tag = lambda a: ('US ' if team[a] == r['us'] else 'TH ') + name[a] + str(a)
cg = {c['id']: c['group'] for c in mj['camps']}
g = int(sys.argv[4]) if len(sys.argv) > 4 else None
if g is None:
    caps = [e for e in ev if e['k'] == 'capture' and r0 <= e['r'] <= r1]
    g = caps[0]['g']
tiles = [tuple(t) for t in mj['groups'][g]['tiles']]
print(r['source'], 'us team', r['us'], 'group', g, mj['groups'][g]['types'], tiles)
for e in ev:
    if not (r0 <= e['r'] <= r1): continue
    if e.get('g') == g or (e.get('camp') is not None and cg.get(e['camp']) == g) or e['k'] in ('death',) or (e['k'] in ('attack', 'cast') and e.get('tgt') is not None):
        d = {k: v for k, v in e.items() if k not in ('s',)}
        if 'a' in d: d['a'] = tag(d['a'])
        if 'v' in d: d['v'] = tag(d['v'])
        if 'tgt' in d: d['tgt'] = tag(d['tgt'])
        print(d)
for rr in range(r0, r1 + 1, 3):
    i = rr - 1
    row = []
    for c in R['champions']:
        if c['alive'][i] and c['x'][i] is not None:
            p = (c['x'][i], c['y'][i]); dd = min(cheb(p, t) for t in tiles)
            if dd <= 10: row.append(f"{tag(c['id'])}@{p} d{dd} hp{c['hp'][i]:.0f} g{c['gems'][i]}")
    print(rr, ' | '.join(row))
