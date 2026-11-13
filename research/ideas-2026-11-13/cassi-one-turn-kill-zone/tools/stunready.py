"""At the body's last turns before its late death to Vesper: was its own stun (Cassi slot 1) ready, Vesper within 4 and seen, and did it cast?
python3 stunready.py EXT  (local, extract.mjs output)"""
import gzip, json, os, sys, collections
ext = sys.argv[1]
cheb = lambda a, b: 99 if None in a or None in b else max(abs(a[0] - b[0]), abs(a[1] - b[1]))
idx = json.load(open(ext + '/index.json'))['games']
T = collections.defaultdict(collections.Counter); n = 0
for g in idx:
    us = 0 if g['source'].endswith('-12.repl26a') else 1
    d = ext + '/' + g['dir']; m = json.load(open(d + '/meta.json'))
    ours = {c['name']: c['id'] for c in m['champions'] if c['team'] == us}; fish = {c['name']: c['id'] for c in m['champions'] if c['team'] != us}
    if 'Cassi' not in ours or 'Vesper Vale' not in fish: continue
    cid = ours['Cassi']; vid = fish['Vesper Vale']
    evs = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    kills = [e for e in evs if e['k'] == 'death' and e['v'] == cid and 'linked' not in e and e['r'] >= 300 and e.get('by') == vid]
    if not kills: continue
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt')); ri = {v: i for i, v in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    ca, ve = C[cid], C[vid]
    casts = collections.defaultdict(list)
    for e in evs:
        if e.get('a') == cid and e['k'] == 'cast': casts[e['r']].append((e.get('ab'), e.get('tgt')))
    for e in kills:
        n += 1
        for k in range(1, 5):
            r = e['r'] - k; j = ri[r]
            # state at the end of round r-1 ~ start of Cassi's turn in round r
            jp = j - 1
            ready = ca['cd1'][jp] == 0
            dd = cheb((ca['x'][jp], ca['y'][jp]), (ve['x'][jp], ve['y'][jp]))
            seen = vid in (ca['sees'][jp] or [])
            stunned_v = any(ab == 'CC' and t == vid for ab, t in casts[r])
            stun_any = any(ab == 'CC' for ab, t in casts[r])
            T[k]['ready'] += ready; T[k]['ready_in4_seen'] += ready and dd <= 4 and seen; T[k]['ready_in6_seen'] += ready and dd <= 6 and seen
            T[k]['cast_on_vesper'] += stunned_v; T[k]['cast_other'] += stun_any and not stunned_v
            T[k]['v_stunned'] += ve['stun'][jp] > 0
print('Cassi late deaths to Vesper:', n)
for k in range(1, 5):
    print(f' round death-{k}: ' + ', '.join(f'{a} {b}' for a, b in T[k].items()))
