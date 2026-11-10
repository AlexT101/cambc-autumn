"""Our Prism's last rounds before each champion-kill death: hp share, nearest enemy, spawn distance, what it did.
   [LOCAL=dir] python3 traj.py OUT.jsonl [since]"""
import sys, json, collections
sys.path.insert(0, '/home/ubuntu/tmp-offload/fishre/tools')
from fl import games, cheb
since = sys.argv[2] if len(sys.argv) > 2 else '2026-11-08'
out = open(sys.argv[1], 'w')
def spawn_d(sp, p): return max(max(sp['minX'] - p[0], 0, p[0] - sp['maxX']), max(sp['minY'] - p[1], 0, p[1] - sp['maxY']))
for g in games(lambda g: g['created'] >= since and g['opp'] == 'stellar best girl'):
    m = g['meta']; rd = g['rd']; team = 1 - g['fish']
    pr = [c for c in m['champions'] if c['name'] == 'Prism' and c['team'] == team]
    if not pr: continue
    P = pr[0]['id']; ch = {c['id']: c for c in rd['champions']}; v = ch[P]; tm = {c['id']: c['team'] for c in m['champions']}
    idx = {r: i for i, r in enumerate(rd['round'])}; sp = g['map']['spawn'][team]
    act = collections.defaultdict(set); took = collections.defaultdict(float); dealt = collections.defaultdict(float)
    for e in g['ev']:
        if e.get('a') == P and e['k'] in ('attack', 'cast', 'move', 'shop', 'tribute_start', 'recall_end'): act[e['r']].add(e['k'] if e['k'] != 'cast' else 'cast')
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            for vid, amt in e['dmg']:
                if vid == P: took[e['r']] += amt
                if e.get('a') == P and tm.get(vid) is not None and tm[vid] != team: dealt[e['r']] += amt
    for e in g['ev']:
        if e['k'] != 'death' or e['v'] != P or 'camp' in e: continue
        r = e['r']; T = []
        for k in range(1, 13):
            i = idx.get(r - k)
            if i is None or not v['alive'][i] or v['x'][i] is None: break
            p = (v['x'][i], v['y'][i])
            ens = [cheb(p, (c['x'][i], c['y'][i])) for c in rd['champions'] if tm[c['id']] != team and c['alive'][i] and c['x'][i] is not None]
            T.append(dict(k=k, hp=round(v['hp'][i] / v['maxHp'][i], 3), hpabs=round(v['hp'][i]), ne=min(ens, default=99), n4=sum(d <= 4 for d in ens),
                          sd=spawn_d(sp, p), gems=v['gems'][i], act=sorted(act[r - k + 1]), took=round(took[r - k + 1]), dealt=round(dealt[r - k + 1])))
        out.write(json.dumps(dict(mid=g['mid'], map=m['map']['name'], win=m['result']['winner'] == team, r=r, gems=e.get('gems', 0), maxhp=v['maxHp'][idx[r - 1]], T=T)) + '\n')
