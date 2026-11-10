"""Model-free check of one cell: Hajek IPW win rates by arm for (type, k), from raw decisions of some batches."""
import json, subprocess, sys, collections
lab, batches, T, K = sys.argv[1], sys.argv[2].split(','), int(sys.argv[3]), int(sys.argv[4])
cfg = json.load(open(f'replays/emblab/{lab}/config.json'))
games = {}
want = {f'b{int(b):03d}' for b in batches}
for l in open(f'replays/emblab/{lab}/games.jsonl'):
    if l[8:12] in want or l[7:11] in want:
        g = json.loads(l)
        if 'winner' in g and g.get('draft_ok') is not False: games[g['id']] = g
F=["monster","power","durability","treasure","jungle","home","bruiser","tribute","capture","prospector","hunter","skirmish","greed","collectors"]; St=["str","foc","hp"]
nm=lambda a: F[a//3]+'-'+St[a%3]
acc = collections.defaultdict(lambda: [0.0, 0.0, 0])   # key -> [sum w y, sum w, n]
for b in batches:
    p = subprocess.Popen(['zstd', '-dc', f'replays/emblab/{lab}/decisions/b{int(b):03d}.jsonl.zst'], stdout=subprocess.PIPE, text=True)
    needle = f'"type": {T}, "k": {K},'
    for l in p.stdout:
        if needle not in l: continue
        d = json.loads(l)
        g = games.get(d['id'])
        if g is None: continue
        y = 1.0 if g['winner'] == d['team'] else 0.0
        pf = cfg['p_uniform'] if d['mode'] == 1 else cfg['p_force'][d['k']]
        P = (1 - pf + pf * d['qb']) if d['chosen'] == d['base'] else pf * d['q']
        side = 'AB'[d['team']]
        src, opp, picks = g.get('src' + side), g['opp'], g['picks']
        arm = 'BASE' if d['chosen'] == d['base'] else nm(d['chosen'])
        for key in ((arm, 'all'), (arm, 'src=' + str(src)), (arm, 'opp=' + opp), (arm, f'picks={picks}')):
            a = acc[key]; a[0] += y / P; a[1] += 1 / P; a[2] += 1
        if d['chosen'] == d['base']:
            a = acc[('base:' + nm(d['base']), 'all')]; a[0] += y / P; a[1] += 1 / P; a[2] += 1
groups = sorted({k[1] for k in acc})
for grp in groups:
    base = acc.get(('BASE', grp))
    if not base: continue
    print(f'== {grp}: base policy {100*base[0]/base[1]:.1f}% (n {base[2]})')
    rows = [(k[0], v) for k, v in acc.items() if k[1] == grp and k[0] != 'BASE' and v[2] >= (150 if grp == 'all' else 400)]
    rows.sort(key=lambda r: -r[1][0] / r[1][1])
    for arm, v in rows[:14 if grp == 'all' else 5]:
        m = v[0] / v[1]
        print(f'   {arm:22s} {100*m:.1f}%  ({100*(m - base[0]/base[1]):+.1f} vs base)  n {v[2]}  ~se {100*(0.25/v[2])**.5:.1f}')
