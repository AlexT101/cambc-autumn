# Early deaths (round < T): damage the victim took from camps vs champions in the 15 rounds before, the group
# it stood near (side), local numbers; for both sides. usage: early.py T OUT.pkl
import json, gzip, os, sys, pickle, collections
import numpy as np
T = int(sys.argv[1])
ana = os.path.expanduser('~/tmp-offload/bigl/ana'); games = json.load(open(os.path.expanduser('~/tmp-offload/bigl/games.json')))
idx = json.load(open(ana + '/index.json'))['games']
rows = []; done = set()
for g in idx:
    m = os.path.basename(g['source']).split('.')[0]; gm = games.get(m)
    if not gm or g['dir'] in done: continue
    done.add(g['dir'])
    d = ana + '/' + g['dir']
    meta = json.load(open(d + '/meta.json'))
    mp = json.load(open(ana + '/maps/' + os.path.basename(meta['mapFile'])))
    ev = []
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > T: break
        ev.append(e)
    us = 0 if gm['side'] == 'a' else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    camp_g = {c['id']: c['group'] for c in mp['camps']}; gside = {q['id']: q['side'] for q in mp['groups']}
    campdmg = collections.defaultdict(list); champdmg = collections.defaultdict(list); atk_camp = collections.defaultdict(list)
    for e in ev:
        if e['k'] == 'camp_attack':
            campdmg[e['tgt']].append((e['r'], e['dmg'], e['g']))
            for x in e.get('xdmg', []) or []:
                campdmg[x[0]].append((e['r'], x[1], e['g']))
        elif e['k'] in ('attack', 'cast'):
            if e.get('camp') is not None:
                atk_camp[e['a']].append((e['r'], camp_g.get(e['camp'])))
            for tid, amt in (e.get('dmg') or []):
                if tid in team: champdmg[tid].append((e['r'], amt, e['a']))
        elif e['k'] == 'death' and not e.get('linked'):
            v = e['v']; r = e['r']
            cd = sum(a for rr, a, _ in campdmg[v] if r - 15 <= rr <= r)
            hd = sum(a for rr, a, _ in champdmg[v] if r - 15 <= rr <= r)
            att = set(a for rr, a, _ in champdmg[v] if r - 15 <= rr <= r)
            farm = [gq for rr, gq in atk_camp[v] if r - 20 <= rr <= r]
            # was the killer side farming too?
            kfarm = [gq for a in att for rr, gq in atk_camp[a] if r - 20 <= rr <= r]
            fg = collections.Counter(farm).most_common(1)
            s = gside.get(fg[0][0]) if fg else None
            where = None if s is None else ('shared' if s == -1 else ('own' if s == team[v] else 'enemy'))
            rows.append(dict(dir=g['dir'], win=gm['result'] == 'win', ours=team[v] == us, r=r, victim=typ[v],
                             killer=typ.get(e.get('by'), 'camp'), campdmg=cd, champdmg=hd, attackers=len(att),
                             farming=bool(farm), farm_where=where, killer_farming=bool(kfarm), bag=e.get('gems', 0),
                             opp=gm['opp_name'], map=gm['map']))
pickle.dump(rows, open(sys.argv[2], 'wb')); print(len(rows))
