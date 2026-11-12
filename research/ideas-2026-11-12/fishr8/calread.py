"""Calibration table: our win % against each Fish body (replays/ab/fr-<bot>-<body>-ladder-all-k*, pooled) beside
live against Fish r8 (capture rows, ours.json; paired only where both exist).   py calread.py BODY..."""
import json, glob, os, sys, math
R = '/home/ubuntu/cambc-autumn/replays/ab/'
BOTS = [(115, 'oc-dfuel-506'), (116, 'charybdis-p3'), (117, 'c520-ps'), (118, 'lab-emb6-c520-ps')]
o = json.load(open(os.path.expanduser('~/tmp-offload/fishr8/ours.json')))
def ci(w, n):
    if not n: return ''
    p = w / n; h = 1.96 * math.sqrt(p * (1 - p) / n); return f'{100 * p:.1f} ({100 * (p - h):.1f}-{100 * (p + h):.1f}) of {n}'
bodies = sys.argv[1:]
print('| our bot | live r8 | ' + ' | '.join(bodies) + ' |'); print('|---' * (2 + len(bodies)) + '|')
for v, b in BOTS:
    L = [x for x in o.values() if x['refset'] == 'r8' and x['version'] == v and x['result']]
    row = [f'v{v} {b}', ci(sum(x['result'] == 'win' for x in L), len(L))]
    for bd in bodies:
        w = n = 0
        for d in glob.glob(f'{R}fr-{b}-{bd}-ladder-all-k*/summary.json'):
            s = json.load(open(d)); w += s['cand_wins']; n += s['games']
        row.append(f'{100 * w / n:.1f} of {n}' if n else '-')
    print('| ' + ' | '.join(row) + ' |')
