"""Prism deaths in context. env LOCAL=<extract dir> for local batches (fl.local_games), else fish-re's live caches.
   python3 pdeaths.py OUT.jsonl [who=us|fish|opp] [since]"""
import sys, json, collections, os, re
sys.path.insert(0, '/home/ubuntu/tmp-offload/fishre/tools')
from fl import games, cheb
out = open(sys.argv[1], 'w'); who = sys.argv[2] if len(sys.argv) > 2 else 'us'; since = sys.argv[3] if len(sys.argv) > 3 else '2026-11-08'
ITEMS = json.load(open("/home/ubuntu/cambc-autumn/replays/.analysis/enums.json"))["items"]
def spawn_d(sp, p): return max(max(sp['minX'] - p[0], 0, p[0] - sp['maxX']), max(sp['minY'] - p[1], 0, p[1] - sp['maxY']))
def filt(g):
    if g['created'] < since: return False
    if who == 'us' and g['opp'] != 'stellar best girl': return False
    return True
n = 0
for g in games(filt):
    m = g['meta']; rd = g['rd']; F = g['fish']
    team = {'us': 1 - F, 'fish': F, 'opp': 1 - F}[who]
    prisms = [c for c in m['champions'] if c['name'] == 'Prism' and c['team'] == team]
    if not prisms: continue
    P = prisms[0]['id']; ch = {c['id']: c for c in rd['champions']}; v = ch[P]; name = {c['id']: c['name'] for c in m['champions']}
    tm = {c['id']: c['team'] for c in m['champions']}
    rr = rd['round']; idx = {r: i for i, r in enumerate(rr)}
    sp = g['map']['spawn'][team]
    # champion damage taken by P per round, attackers
    dmg = collections.defaultdict(float); att = collections.defaultdict(set); campd = collections.defaultdict(float)
    rec = []  # recall events of P
    for e in g['ev']:
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            for vid, amt in e['dmg']:
                if vid == P and amt > 0: dmg[e['r']] += amt; att[e['r']].add(e['a'])
        if e['k'] == 'camp_attack':
            if e.get('tgt') == P: campd[e['r']] += e.get('dmg', 0)
            for x in e.get('xdmg', []) or []:
                if isinstance(x, list) and x[0] == P: campd[e['r']] += x[1]
        if e['k'] in ('recall_start', 'recall_cancel', 'recall_end') and e.get('a') == P: rec.append((e['r'], e['k'], e.get('cause')))
    deaths = [e for e in g['ev'] if e['k'] == 'death' and e['v'] == P]
    rows = []
    for e in deaths:
        r = e['r']; i = idx.get(r - 1, 0)
        p = (v['x'][i], v['y'][i])
        if p[0] is None: continue
        def frac(k):
            j = idx.get(r - k)
            return None if j is None or not v['alive'][j] else round(v['hp'][j] / max(1, v['maxHp'][j]), 3)
        # damage episode: walk back while champion damage within 3-round gaps
        s = r; last = r
        while s > 1 and any(dmg.get(s - k, 0) > 0 for k in (1, 2, 3)) and r - s < 40:
            s -= 1
            if dmg.get(s, 0) > 0: last = s
        ep_start = min([q for q in range(s, r + 1) if dmg.get(q, 0) > 0], default=r)
        j0 = idx.get(ep_start - 1, i)
        ep_hp0 = v['hp'][j0] / max(1, v['maxHp'][j0]) if v['alive'][j0] else None
        ep_dmg = sum(dmg.get(q, 0) for q in range(ep_start, r + 1)); ep_att = set().union(*[att.get(q, set()) for q in range(ep_start, r + 1)])
        en = [(name[c['id']], round(c['hp'][i] / max(1, c['maxHp'][i]), 2), cheb(p, (c['x'][i], c['y'][i]))) for c in rd['champions']
              if tm[c['id']] != team and c['alive'][i] and c['x'][i] is not None and cheb(p, (c['x'][i], c['y'][i])) <= 8]
        al = [(name[c['id']], cheb(p, (c['x'][i], c['y'][i]))) for c in rd['champions']
              if tm[c['id']] == team and c['id'] != P and c['alive'][i] and c['x'][i] is not None and cheb(p, (c['x'][i], c['y'][i])) <= 8]
        hl = 0
        it = v['items'][i] or []
        for a, b in zip(it[::2], it[1::2]):
            nm = ITEMS[a]
            if 'Health' in nm: hl += b * (1 if 'Shard' in nm else (5 if 'Greed' not in nm else 25))
        rows.append(dict(r=r, gems=e.get('gems', 0), hp_before=round(e.get('hp', 0) / max(1, v['maxHp'][i]), 3), maxhp=v['maxHp'][i],
                         f1=frac(1), f3=frac(3), f6=frac(6), f12=frac(12), ep_start=ep_start, ep_len=r - ep_start + 1, ep_hp0=None if ep_hp0 is None else round(ep_hp0, 3),
                         ep_dmg=round(ep_dmg), ep_att=len(ep_att), camp=('camp' in e), by=name.get(e.get('by')), gold=v['gold'][i], hshards=hl,
                         chan=v['chan'][i], foc=round(v['foc'][i]), spawn_d=spawn_d(sp, p), en=en, al=al,
                         rec=[x for x in rec if r - 15 <= x[0] <= r], campd=round(sum(campd.get(q, 0) for q in range(ep_start, r + 1)))))
    # gem/hp profile: max carried, rounds alive with gems>=50
    gm = [x for x in v['gems']]
    out.write(json.dumps(dict(mid=(re.search(r'(Flp|Mt3p)-f\d-f\d/.*', g['meta']['source']).group(0) if os.environ.get('LOCAL') else g['mid']), map=m['map']['name'], win=(m['result']['winner'] == team), rounds=m['result']['rounds'],
                              created=g['created'], who=who, trib=m['result']['gems'][team], otrib=m['result']['gems'][1-team], maxhp_end=v['maxHp'][-1], deaths=rows,
                              gems_max=max(gm), gems_lost=prisms[0]['stats']['collectedGems'] - prisms[0]['stats']['submittedGems'] - v['gems'][-1],
                              collected=prisms[0]['stats']['collectedGems'], submitted=prisms[0]['stats']['submittedGems'],
                              earned=prisms[0]['earnedGold'], spent=prisms[0]['stats']['spentGold'])) + '\n')
    n += 1
print(n)
