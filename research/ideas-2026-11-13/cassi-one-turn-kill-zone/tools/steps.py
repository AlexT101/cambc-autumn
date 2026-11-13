"""Cassi's own moves in the 6 rounds before her late deaths to Vesper (czk-trace debug stdout + replay):
does the step end within Vesper's strike reach (5 dash ready, 4 reset ready, else 3) while Cassi saw her? By decision.
python3 steps.py EXT"""
import gzip, json, os, sys, zipfile, collections
ext = sys.argv[1]; ROOT = '/home/ubuntu/cambc-autumn/'
cheb = lambda a, b: 99 if None in a or None in b else max(abs(a[0] - b[0]), abs(a[1] - b[1]))
idx = json.load(open(ext + '/index.json'))['games']
T = collections.Counter(); n = 0
for g in idx:
    us = 0 if g['source'].endswith('-12.repl26a') else 1
    d = ext + '/' + g['dir']; m = json.load(open(d + '/meta.json'))
    ours = {c['name']: c['id'] for c in m['champions'] if c['team'] == us}; fish = {c['name']: c['id'] for c in m['champions'] if c['team'] != us}
    if 'Cassi' not in ours or 'Vesper Vale' not in fish: continue
    cid = ours['Cassi']; vid = fish['Vesper Vale']
    evs = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    kills = [e for e in evs if e['k'] == 'death' and e['v'] == cid and 'linked' not in e and e['r'] >= 300 and e.get('by') == vid]
    if not kills: continue
    out = zipfile.ZipFile(ROOT + g['source'] if not os.path.isabs(g['source']) else g['source']).read('team-a.stdout' if us == 0 else 'team-b.stdout').decode(errors='replace').splitlines()
    D = {}
    for l in out:
        v = l.split()
        if len(v) >= 4 and v[0] == 'D':
            try:
                if int(v[2]) == cid: D[int(v[1])] = v[3]
            except ValueError: pass
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt')); ri = {v: i for i, v in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    ve = C[vid]; ca = C[cid]
    # Vesper's position during Cassi's move: replay the round's moves in order
    for e in kills:
        n += 1
        r0 = e['r']
        for x in evs:
            if not (r0 - 6 <= x['r'] < r0) or x.get('a') != cid or x['k'] != 'move': continue
            r = x['r']; j = ri[r] - 1
            # Vesper's tile at Cassi's move: her last move/dash this round before step s, else last round's
            vp = (ve['x'][j], ve['y'][j])
            for y in evs:
                if y['r'] == r and y.get('a') == vid and y['s'] < x['s'] and (y['k'] == 'move' or (y['k'] == 'cast' and y.get('ab') == 'Dash')):
                    vp = tuple(y.get('to') if y['k'] == 'move' else y.get('moved') or y.get('to'))
            cd0, cd1 = ve['cd0'][j], ve['cd1'][j]
            reach = 5 if cd1 == 0 else 4 if cd0 == 0 else 3
            seen = vid in (ca['sees'][j] or [])
            before, after = cheb(tuple(x['f']), vp), cheb(tuple(x['to']), vp)
            dec = D.get(r, '?')
            if seen:
                T[(dec, 'into' if after <= reach < before else 'stays-in' if after <= reach else 'out')] += 1
print('Cassi deaths:', n)
for k, v in sorted(T.items(), key=lambda kv: -kv[1]): print(k, v)
