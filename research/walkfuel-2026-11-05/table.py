"""table.py NAME...: one markdown row per A/B (wfscratch/res/NAME.metrics + replays/ab/NAME/summary.md), then pooled."""
import ast, math, re, sys

ROOT = "/home/ubuntu/cambc-autumn/.claude/worktrees/agent-ab4ebc4c0ecb8a725"
GATES = ['farm-partial-evaluation', 'turn-order', 'farm-no-route', 'static-descend', 'crow-flies-farm',
         'step-guard-entry', 'prey-cut-short']


def parse(name):
    m = open(f'{ROOT}/wfscratch/res/{name}.metrics').read()
    tot = re.search(r'\*\*total\*\* \| ([\d.]+) \| (\d+) \| ([\d.]+)-([\d.]+)', open(f'{ROOT}/replays/ab/{name}/summary.md').read())
    r = {'win': float(tot[1]), 'games': int(tot[2]), 'ci': (tot[3], tot[4])}
    bots = re.findall(r'^(\S+): OOF (\d+).*\n  rounds (\{.*\})\n.*\n  champion-game run sizes (\{.*\})', m, re.M)
    for (bot, oof, rounds, runs), side in zip(bots, ('c', 'r')):
        rounds, runs = ast.literal_eval(rounds), ast.literal_eval(runs)
        r[side] = {'oof': int(oof), 'r1': rounds['1'], 'r2_10': rounds['2-10'], 'run50': runs['>=50']}
    sc = re.findall(r'^(\S+) \d+ (\{.*\})$', m.split('== shortcuts')[1].split('== bymap')[0], re.M)
    for (bot, d), side in zip(sc, ('c', 'r')):
        d = ast.literal_eval(d)
        r[side].update({g: d.get(g, 0) for g in GATES})
    by = dict(re.findall(r'(g[^:\s]+):([\d.]+)\((\d+)\)', m.split('== bymap')[1]) and
              [(k, (float(v), int(n))) for k, v, n in re.findall(r'(g[^:\s]+):([\d.]+)\((\d+)\)', m.split('== bymap')[1])])
    r['by'] = by
    return r


def k(x):
    return f'{x / 1000:.1f}k' if x < 1e6 else f'{x / 1e6:.3f}M'


def row(label, r):
    c, f = r['c'], r['r']
    by = ' / '.join(f"{r['by'][g][0]:.1f}" for g in ('g<12', 'g12-23', 'g24-47', 'g48+'))
    n48 = r['by']['g48+'][1]
    cells = [label, f"{r['win']:.1f} ({r['ci'][0]}-{r['ci'][1]})", f"{r['games']:,}",
             f"{k(c['oof'])} / {k(f['oof'])}", f"{k(c['r1'])} / {k(f['r1'])}", f"{k(c['r2_10'])} / {k(f['r2_10'])}",
             f"{c['run50']:,} / {f['run50']:,}"]
    cells += [f"{k(c[g])} / {k(f[g])}" for g in GATES]
    cells.append(f'{by} ({n48})')
    return '| ' + ' | '.join(cells) + ' |'


def pool(rs):
    games = sum(r['games'] for r in rs)
    win = sum(r['win'] * r['games'] for r in rs) / games
    # per-suite CIs are binomial on games; pool the same way (map-pair correlation ignored, as ab.py does)
    se = math.sqrt(win / 100 * (1 - win / 100) / games) * 100
    out = {'win': win, 'games': games, 'ci': (f'{win - 1.96 * se:.1f}', f'{win + 1.96 * se:.1f}')}
    for side in 'cr':
        out[side] = {key: sum(r[side][key] for r in rs) for key in rs[0][side]}
    out['by'] = {}
    for g in rs[0]['by']:
        n = sum(r['by'][g][1] for r in rs)
        out['by'][g] = (sum(r['by'][g][0] * r['by'][g][1] for r in rs) / n, n)
    return out


hdr = ['run', 'win % (CI)', 'games', 'OOF cand / ref', 'round 1', 'rounds 2-10', 'runs of 50+'] + GATES + \
      ['by groups <12 / 12-23 / 24-47 / 48+ (48+ games)']
print('| ' + ' | '.join(hdr) + ' |')
print('|' + '---|' * len(hdr))
groups = {}
for name in sys.argv[1:]:
    label, _, grp = name.partition('=')
    r = parse(label)
    print(row(label, r))
    for g in grp.split(',') if grp else []:
        groups.setdefault(g, []).append(r)
for g, rs in groups.items():
    print(row(f'**{g}** pooled', pool(rs)))
