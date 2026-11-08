# Camp clears in the decoded scrims: for each wake episode (group_wake -> group_clear), who woke it, who cleared
# (cleared by the waker's team = own clear, by the other = stolen), rounds taken, camp damage dealt by each team,
# and the champions of the waker that left (recalled/died) mid-clear. usage: clears.py OUT.pkl
import json, gzip, os, sys, pickle, collections
ana = os.path.expanduser('~/tmp-offload/bigl/ana'); games = json.load(open(os.path.expanduser('~/tmp-offload/bigl/games.json')))
idx = json.load(open(ana + '/index.json'))['games']
rows = []; done = set()
for g in idx:
    m = os.path.basename(g['source']).split('.')[0]; gm = games.get(m)
    if not gm or g['dir'] in done: continue
    done.add(g['dir']); d = ana + '/' + g['dir']
    meta = json.load(open(d + '/meta.json')); mp = json.load(open(ana + '/maps/' + os.path.basename(meta['mapFile'])))
    G = {q['id']: q for q in mp['groups']}; camp_g = {c['id']: c['group'] for c in mp['camps']}
    team = {c['id']: c['team'] for c in meta['champions']}; us = 0 if gm['side'] == 'a' else 1
    open_ = {}
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l); k = e['k']
        if k == 'group_wake' and e['g'] not in open_:
            by = e.get('by'); wt = team.get(by) if by is not None else None
            open_[e['g']] = dict(r0=e['r'], waker=wt, dmg=[0.0, 0.0], camp_hits=[0.0, 0.0], left=0)
        elif k in ('attack', 'cast') and e.get('camp') is not None:
            gq = camp_g.get(e['camp'])
            if gq in open_ and e['a'] in team:
                open_[gq]['dmg'][team[e['a']]] += sum(a for _, a in (e.get('cdmg') or [])) if e.get('cdmg') else 0
        elif k == 'camp_attack' and e['g'] in open_ and e.get('tgt') in team:
            open_[e['g']]['camp_hits'][team[e['tgt']]] += e.get('dmg', 0)
        elif k == 'group_clear' and e['g'] in open_:
            o = open_.pop(e['g']); by = e.get('by'); ct = team.get(by)
            q = G[e['g']]
            rows.append(dict(dir=g['dir'], win=gm['result'] == 'win', opp=gm['opp_name'], map=gm['map'], g=e['g'],
                             types=tuple(sorted(set(q['types']))), gems=q['gems'], side=q['side'], us=us,
                             r0=o['r0'], r1=e['r'], waker=o['waker'], clearer=ct, dmg=o['dmg'], camp_hits=o['camp_hits']))
        elif k == 'group_sleep' and e['g'] in open_:
            o = open_.pop(e['g'])
            rows.append(dict(dir=g['dir'], win=gm['result'] == 'win', opp=gm['opp_name'], map=gm['map'], g=e['g'],
                             types=tuple(sorted(set(G[e['g']]['types']))), gems=G[e['g']]['gems'], side=G[e['g']]['side'], us=us,
                             r0=o['r0'], r1=e['r'], waker=o['waker'], clearer='slept', dmg=o['dmg'], camp_hits=o['camp_hits']))
pickle.dump(rows, open(sys.argv[1], 'wb')); print(len(rows))
