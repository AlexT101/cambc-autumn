"""Read fork_arms.py's output: cand - base win (points) by fork round, paired on (game, fork, body member), SE clustered by game.
    py fork_read.py OUT_DIR"""
import sys, json, glob, collections, math
d = sys.argv[1]
ours = {}
for f in glob.glob(f'{d}/games-*.jsonl'):
    for l in open(f):
        g = json.loads(l); ours[g['id']] = g['ours']
A = collections.defaultdict(dict)
for l in open(f'{d}/out.jsonl'):
    x = json.loads(l)
    if x.get('type') != 'arm' or 'winner' not in x or x.get('error'): continue
    lab, k = x['label'].split('+')
    w = 0.5 if x['winner'] is None else float(x['winner'] == ours[x['game']])
    A[(x['game'], x['fork'], k)][lab] = w
by = collections.defaultdict(lambda: collections.defaultdict(list))
for (g, f, k), v in A.items():
    if 'base' in v and 'cand' in v:
        for key in (f, 'all'): by[key][g].append((v['cand'] - v['base'], v['base'], v['cand']))
for key in sorted(by, key=str):
    gs = by[key]; n = sum(len(v) for v in gs.values())
    diffs = [sum(x[0] for x in v) for v in gs.values()]; cnt = [len(v) for v in gs.values()]
    mean = sum(diffs) / n
    se = math.sqrt(sum((d_ - c * mean) ** 2 for d_, c in zip(diffs, cnt))) / n
    b = sum(x[1] for v in gs.values() for x in v) / n; c = sum(x[2] for v in gs.values() for x in v) / n
    fl = sum(1 for v in gs.values() for x in v if x[0] != 0)
    print(f'fork {key}: {n} pairs ({len(gs)} games): base {b:.1%}, cand {c:.1%}, cand - base {mean*100:+.2f} +- {se*100:.2f} points; flips {fl}')
