"""Model-free: win rate under the base (table) against under the current logic's arm, for (type, k range), by draft source."""
import json, subprocess, sys, collections
lab, batches, T, K0, K1 = sys.argv[1], sys.argv[2].split(','), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
cfg = json.load(open(f'replays/emblab/{lab}/config.json'))
want = {f'b{int(b):03d}' for b in batches}
games = {}
for l in open(f'replays/emblab/{lab}/games.jsonl'):
    if l[8:12] in want:
        g = json.loads(l)
        if 'winner' in g and g.get('draft_ok') is not False: games[g['id']] = g
acc = collections.defaultdict(lambda: [0.0, 0.0, 0, 0.0, 0.0, 0, 0])  # base: swy, sw, n ; current: swy, sw, n ; rows where they differ
for b in batches:
    p = subprocess.Popen(['zstd', '-dc', f'replays/emblab/{lab}/decisions/b{int(b):03d}.jsonl.zst'], stdout=subprocess.PIPE, text=True)
    needle = f'"type": {T}, "k": '
    for l in p.stdout:
        if needle not in l: continue
        d = json.loads(l)
        if not (K0 <= d['k'] <= K1): continue
        g = games.get(d['id'])
        if g is None: continue
        y = 1.0 if g['winner'] == d['team'] else 0.0
        pf = cfg['p_uniform'] if d['mode'] == 1 else cfg['p_force'][d['k']]
        src = g.get('src' + 'AB'[d['team']])
        for key in ('all', 'src=' + str(src), 'opp=' + g['opp']):
            a = acc[key]
            a[6] += d['current'] != d['base']
            if d['chosen'] == d['base']:
                w = 1 / (1 - pf + pf * d['qb']); a[0] += w * y; a[1] += w; a[2] += 1
                if d['current'] == d['base']: a[3] += w * y; a[4] += w; a[5] += 1
            elif d['chosen'] == d['current']:
                w = 1 / (pf * d['q']); a[3] += w * y; a[4] += w; a[5] += 1
for key in sorted(acc):
    a = acc[key]
    if a[1] and a[4]:
        print(f"{key:14s} base {100*a[0]/a[1]:.2f}% (n {a[2]})  current logic {100*a[3]/a[4]:.2f}% (n {a[5]})  diff {100*(a[3]/a[4]-a[0]/a[1]):+.2f}  rows where they differ {a[6]}")
