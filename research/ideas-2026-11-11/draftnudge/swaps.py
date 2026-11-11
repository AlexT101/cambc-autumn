"""What the nudges actually swapped, and what each swap did: every (map, changed team) played by any arm of a stage
(each counted once), grouped by the champions that left and joined, paired against the base on the same map.
    py swaps.py STAGE [min_maps]"""
import sys, os, json, collections, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run, nudge
s = run.stage(sys.argv[1]); mn = int(sys.argv[2]) if len(sys.argv) > 2 else 40
nudge.W = run.W
mp = run.maps_of(s); base, _ = run.results(s, 'base'); bt = run.teams(s, 'base')
maps = {m['name']: m for m in nudge.load_maps(s['feat'])}
S = {}
def model_gap(name, a, b):
    """Base model's score of team b minus team a on the map (logit)."""
    m = maps[name]; p = m['picks']
    if p not in S: S[p] = {}
    if name not in S[p]: S[p][name] = nudge.scores(m['z'][None, :], p)[0]
    idx = {tuple(T): i for i, T in enumerate(nudge.COMBOS[p].tolist())}
    f = lambda t: idx[tuple(sorted(nudge.EN.index(c) for c in t.split(',')))]
    return S[p][name][f(b)] - S[p][name][f(a)]
seen = {}; 
for arm in s['arms']:
    if arm.endswith('X'): continue  # the copy arms change whole teams
    res, _ = run.results(s, arm); tm = run.teams(s, arm)
    for name, *_ in mp:
        if tm[name] == bt[name] or (name, tm[name]) in seen: continue
        d = {o: [res[(name, o, sd)][0] - base[(name, o, sd)][0] for sd in 'ab' if (name, o, sd) in res and (name, o, sd) in base] for o in 'FM'}
        if not (d['F'] and d['M']): continue
        seen[(name, tm[name])] = (float(np.mean(d['F'] + d['M'])), float(np.mean(d['F'])), float(np.mean(d['M'])), model_gap(name, bt[name], tm[name]))
by = collections.defaultdict(list); out_c = collections.defaultdict(list); in_c = collections.defaultdict(list)
for (name, t), v in seen.items():
    a, b = set(bt[name].split(',')), set(t.split(','))
    o, i = sorted(a - b), sorted(b - a)
    by[('+'.join(o), '+'.join(i))].append(v)
    if len(o) == 1: out_c[o[0]].append(v); in_c[i[0]].append(v)
def line(label, v):
    u = np.array([x[0] for x in v]); se = u.std(ddof=1) / math.sqrt(len(u)) if len(u) > 1 else float('nan')
    return (f'{label:42s} {len(v):6d} {100 * u.mean():+7.2f} ±{196 * se:5.2f} {100 * np.mean([x[1] for x in v]):+8.2f} {100 * np.mean([x[2] for x in v]):+8.2f} '
            f'{25 * np.mean([x[3] for x in v]):+10.2f}')
hdr = f'{"":42s} {"maps":>6s} {"measured pts":>14s} {"vs Fish":>8s} {"vs Mite":>8s} {"model pts":>10s}'
allv = list(seen.values())
print(f'{len(seen)} distinct changed (map, team) pairs over the nudge arms; measured = arm minus base on the same map (4 games each), model = the draft model\'s own prediction\n')
print(hdr); print(line('all changed teams', allv))
print('\nsingle swaps, by the champion that LEFT our team'); print(hdr)
for c, v in sorted(out_c.items(), key=lambda t: -len(t[1])): print(line('  - ' + c, v))
print('\nsingle swaps, by the champion that JOINED'); print(hdr)
for c, v in sorted(in_c.items(), key=lambda t: -len(t[1])): print(line('  + ' + c, v))
print(f'\nswaps seen on at least {mn} maps'); print(hdr)
for (o, i), v in sorted(by.items(), key=lambda t: -len(t[1])):
    if len(v) >= mn: print(line(f'  {o} -> {i}', v))
# calibration: measured against the model's prediction, by predicted-cost bin
g = np.array([x[3] for x in allv]); u = np.array([x[0] for x in allv])
print('\nmodel calibration (changed teams binned by the model\'s predicted change)'); print(f'{"predicted (pts)":>24s} {"maps":>6s} {"mean predicted":>15s} {"measured":>16s}')
qs = np.quantile(g, [0, .2, .4, .6, .8, 1])
for lo, hi in zip(qs[:-1], qs[1:]):
    i = (g >= lo) & (g <= hi)
    print(f'{25 * lo:+10.2f} .. {25 * hi:+8.2f} {i.sum():6d} {25 * g[i].mean():+15.2f} {100 * u[i].mean():+9.2f} ±{196 * u[i].std(ddof=1) / math.sqrt(i.sum()):.2f}')
