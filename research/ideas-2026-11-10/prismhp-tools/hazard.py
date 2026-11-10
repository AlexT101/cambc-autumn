"""Our Prism's death hazard: every round alive off spawn with an enemy within R, P(champion kill within H rounds) by hp share x gems.
   [LOCAL=dir] python3 hazard.py OUT.json [since]"""
import sys, json, collections
sys.path.insert(0, '/home/ubuntu/tmp-offload/fishre/tools')
from fl import games, cheb
since = sys.argv[2] if len(sys.argv) > 2 else '2026-11-08'
H = 6; R = 6
rows = []
for g in games(lambda g: g['created'] >= since and g['opp'] == 'stellar best girl'):
    m = g['meta']; rd = g['rd']; team = 1 - g['fish']
    pr = [c for c in m['champions'] if c['name'] == 'Prism' and c['team'] == team]
    if not pr: continue
    P = pr[0]['id']; ch = {c['id']: c for c in rd['champions']}; v = ch[P]; tm = {c['id']: c['team'] for c in m['champions']}
    sp = g['map']['spawn'][team]
    kill_r = sorted(e['r'] for e in g['ev'] if e['k'] == 'death' and e['v'] == P and 'camp' not in e)
    rr = rd['round']; en = [c for c in rd['champions'] if tm[c['id']] != team]
    al = [c for c in rd['champions'] if tm[c['id']] == team and c['id'] != P]
    for i, r in enumerate(rr):
        if not v['alive'][i] or v['x'][i] is None: continue
        p = (v['x'][i], v['y'][i])
        if sp['minX'] <= p[0] <= sp['maxX'] and sp['minY'] <= p[1] <= sp['maxY']: continue
        ds = [cheb(p, (c['x'][i], c['y'][i])) for c in en if c['alive'][i] and c['x'][i] is not None]
        ne = min(ds, default=99)
        if ne > R: continue
        n4 = sum(d <= 5 for d in ds); a5 = sum(1 for c in al if c['alive'][i] and c['x'][i] is not None and cheb(p, (c['x'][i], c['y'][i])) <= 5)
        died = any(r < k <= r + H for k in kill_r)
        rows.append((round(v['hp'][i] / v['maxHp'][i], 3), v['hp'][i], v['gems'][i], ne, n4, a5, int(died), v['maxHp'][i], r))
json.dump(rows, open(sys.argv[1], 'w'))
print(len(rows))
