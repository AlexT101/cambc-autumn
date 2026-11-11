#!/usr/bin/env python3
"""Paired read of arms against a base, each versus the Flp4 and Mt3q bodies, split by a map's big-group class.

    split.py TAG FEATS.jsonl BASE ARM...     # runs are replays/ab/bg-TAG-<bot>-<body>

Per (map, body) the score is the mean of the two sides; the arm's delta is paired with the base's on the same
map and body. CIs are normal, over (map, body) units."""
import json, sys, math, collections, os
ROOT = '/home/ubuntu/cambc-autumn'
tag, feats, base, arms = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
import re
norm = lambda n: re.sub(r'^f-\d+-', '', n)   # the merged suites' symlink prefix
F = {}
for l in open(feats):
    r = json.loads(l); F[norm(r['map'])] = r
BINS = [(0.3, 'under 30%'), (0.45, '30-45%'), (0.6, '45-60%'), (0.75, '60-75%'), (9, '75%+')]
def klass(r):
    gs = r['mine'] + r['shared']
    cl = lambda g: g['n'].get('gem_cluster', 0)
    gol = [g for g in gs if 'golem' in g['n'] and 'monolith' not in g['n']]
    rich = [g for g in gol if 7 * cl(g) >= g['gems'] - 7 * cl(g)]
    out = set()
    if rich: out.add('rich Golem group (clusters >= strikers)')
    if any(cl(g) > 0 for g in gol) and not rich: out.add('Golem + clusters, not rich')
    if gol and not any(cl(g) > 0 for g in gol): out.add('Golem, no clusters')
    if gol: out.add('any Golem group')
    if any('monolith' in g['n'] for g in gs): out.add('any Monolith')
    if not gol and not any('monolith' in g['n'] for g in gs): out.add('no Golem or Monolith')
    tot = sum(g['gems'] / g['resp'] for g in gs) or 1
    big = sum(g['gems'] / g['resp'] for g in gs if 'golem' in g['n'] or 'monolith' in g['n'] or g['hp'] >= 7000)
    if big / tot >= 0.6: out.add('big groups hold 60%+ of gems')
    mono = any('monolith' in g['n'] for g in gs)
    if mono: out.add('Monolith and Golem group' if gol else 'Monolith, no Golem group')
    if gol and not mono: out.add('Golem group, no Monolith')
    if big / tot >= 0.6: out.add('big 60%+, with Golem group' if gol else 'big 60%+, no Golem group')
    if gol: out.add('Golem group, big share under 60%' if big / tot < 0.6 else 'Golem group, big share 60%+')
    if gol:
        s = big / tot
        out.add('Golem group, big share ' + next(lab for hi, lab in BINS if s < hi))
    out.add('all fresh maps')
    return out
def load(bot, body):
    p = f'{ROOT}/replays/ab/bg-{tag}-{bot}-{body}/summary.json'
    if not os.path.exists(p):
        # A run still under way: its progress log, "[i/n] MAP A=1 B=2: bot 1 wins" (bot 1 is CAND).
        import glob, re
        out = collections.defaultdict(list)
        for lg in glob.glob(f'{ROOT}/replays/ab/bg-{tag}-{bot}-{body}/*.log'):
            for m in re.finditer(r'\] (\S+)\.map26a A=\d B=\d: bot (\d) wins', open(lg, errors='replace').read()):
                out[norm(m.group(1))].append(1.0 if m.group(2) == '1' else 0.0)
        return {k: sum(v) / len(v) for k, v in out.items() if len(v) == 2} or None
    s = json.load(open(p)); out = collections.defaultdict(list)
    for su in s['suites']:
        res = json.load(open(f"{ROOT}/{su['batch']}/results.json"))
        for m in res['matches']:
            if m.get('winner') is None: continue
            name = norm(os.path.basename(m['map']).replace('.map26a', ''))
            out[name].append(1.0 if m['winner'] == 0 else 0.0)   # winner is a bot index; bot 0 is CAND
    return {k: sum(v) / len(v) for k, v in out.items() if len(v) == 2}
def ci(xs):
    n = len(xs)
    if n < 2: return float('nan'), float('nan'), n
    m = sum(xs) / n; v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, 1.96 * math.sqrt(v / n), n
B = {b: load(base, b) for b in ('Flp4', 'Mt3q')}
order = ['all fresh maps', 'rich Golem group (clusters >= strikers)', 'Golem + clusters, not rich', 'Golem, no clusters', 'any Golem group', 'any Monolith', 'big groups hold 60%+ of gems', 'no Golem or Monolith',
         'Monolith, no Golem group', 'Monolith and Golem group', 'Golem group, no Monolith', 'big 60%+, with Golem group', 'big 60%+, no Golem group', 'Golem group, big share under 60%'] + ['Golem group, big share ' + lab for _, lab in BINS]
for arm in arms:
    A = {b: load(arm, b) for b in ('Flp4', 'Mt3q')}
    print(f"\nResults against {base} (paired, {arm} minus {base}, each versus the bodies; fresh ladder-v2 maps, tag {tag})")
    print("| map class | maps | arm win% | base win% | delta, points (95% CI) of n games | Fish body | Mite body |")
    print("|---|---|---|---|---|---|---|")
    for k in order:
        d = {'Flp4': [], 'Mt3q': []}; aw = []; bw = []
        for body in ('Flp4', 'Mt3q'):
            if not A[body] or not B[body]: continue
            for m, a in A[body].items():
                if m in B[body] and m in F and k in klass(F[m]):
                    d[body].append(a - B[body][m]); aw.append(a); bw.append(B[body][m])
        allv = d['Flp4'] + d['Mt3q']
        if not allv: continue
        m, h, n = ci(allv); mf, hf, nf = ci(d['Flp4']); mm, hm, nm = ci(d['Mt3q'])
        print(f"| {k} | {len(set(x for b in ('Flp4','Mt3q') if A[b] for x in A[b] if x in F and k in klass(F[x])))} | {100*sum(aw)/len(aw):.1f} | {100*sum(bw)/len(bw):.1f} | {100*m:+.2f} ±{100*h:.2f} of {2*n} | {100*mf:+.2f} ±{100*hf:.2f} | {100*mm:+.2f} ±{100*hm:.2f} |")
