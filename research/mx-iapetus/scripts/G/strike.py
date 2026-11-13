# Line G: before an enemy Prism kills our Prism's 100+ bag, did ours have a cast ready with the killer in its reach, and
# where did its casts go? Usage: strike.py EXTRACT_DIR CAND_NAME
import json, gzip, sys, collections
A, cand = sys.argv[1].rstrip('/') + '/', sys.argv[2]
idx = json.load(open(A + 'index.json'))['games']
C = collections.Counter(); n = 0
for r in idx:
    if cand not in r['teams']: continue
    ct = r['teams'].index(cand)
    d = r['dir']
    m = json.load(open(A + d + '/meta.json')); name = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    R = json.load(gzip.open(A + d + '/rounds.json.gz')); ri = {x: i for i, x in enumerate(R['round'])}
    ch = {int(c['id']): c for c in R['champions']}
    ev = [json.loads(l) for l in gzip.open(A + d + '/events.jsonl.gz', 'rt')]
    for e in ev:
        if e['k'] != 'death' or e.get('gems', 0) < 100 or team.get(e['v']) != ct or name.get(e['v']) != 'Prism': continue
        k = e.get('by')
        if name.get(k) != 'Prism': continue
        v = e['v']; rd = e['r']; n += 1
        # our last 3 rounds alive before the death, positions at the previous round's end (our turn start)
        chances = used = 0; elsewhere = 0
        for x in range(rd - 3, rd + 1):
            i = ri.get(x - 1)
            if i is None: continue
            if not ch[v]['alive'][i] or not ch[k]['alive'][i]: continue
            dd = max(abs(ch[v]['x'][i] - ch[k]['x'][i]), abs(ch[v]['y'][i] - ch[k]['y'][i]))
            c0, c1 = ch[v]['cd0'][i], ch[v]['cd1'][i]
            stun_ok = dd <= 4 and c0 <= 0
            aoe_ok = dd <= 5 and c1 <= 0
            ours = [q for q in ev if q['r'] == x and q.get('a') == v and q['k'] == 'cast']
            hit_k = any(k in [t for t, _ in q.get('dmg', [])] for q in ours)
            if stun_ok or aoe_ok:
                chances += 1
                if hit_k: used += 1
                elif ours: elsewhere += 1
        C['deaths'] += 1
        C['had a ready cast on the killer in the last 3 turns'] += chances > 0
        C['  and cast at it'] += used > 0
        C['  cast elsewhere instead (camp/other)'] += used == 0 and elsewhere > 0
        C['  held the cast'] += chances > 0 and used == 0 and elsewhere == 0
        # killer's Focus x 1.5 vs our health at that point: did a first stun by ours kill it?
        i = ri.get(rd - 1)
        if i is not None:
            C['our stun (1.5 Focus) >= its health'] += 1.5 * ch[v]['foc'][i] >= ch[k]['hp'][i]
            C['its stun >= our health'] += 1.5 * ch[k]['foc'][i] >= ch[v]['hp'][i]
print('games', len([r for r in idx if cand in r['teams']]))
for key, val in C.items(): print(f'  {key}: {val}')
