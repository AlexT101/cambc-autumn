"""Large paired batches on fresh maps against fixed compiled Fish and Mite bodies: four noise draws of each
(spar-dvn1..4-Flp4 / -Mt3qro), each on its own quarter of the panel's maps, so an arm is eight ab.py batches.
The runtime-configured bodies (runtime506-*) need a runner the shared fastrunner is not (`--prepare-only` is unknown).

    py batch.py prep PANEL SEED_FIRST SEED_LAST        # split ~/tmp-offload/comms2/maps/fresh-<seed> into four suites
    py batch.py run PANEL [--fuel N] ARM [ARM ...]     # each arm (bots/variants/ARM) against both bodies, all at once
    py batch.py report PANEL[,PANEL] BASE ARM [ARM ...] [--fuel N]

A cell is (map, side, body). Arms are compared with BASE on the cells both finished; the unit of the interval is a map
(its cells' mean difference), since a map's games are correlated.
"""
import json, math, os, subprocess, sys, collections
R = os.path.dirname(os.path.abspath(__file__)) + '/../../../'
D = os.path.expanduser('~/tmp-offload/comms2/')
BODY = {'F': 'Flp4', 'M': 'Mt3qro'}
K = 4

def name(arm, panel, o, fuel, k): return f'cmb-{arm}-{panel}{k}-{o}' + (f'-fuel{fuel}' if fuel != 100000 else '')

def prep(panel, first, last):
    files = []
    for seed in range(first, last + 1):
        d = f'{D}maps/fresh-{seed}'
        files += [f'{d}/{f}' for f in sorted(os.listdir(d)) if f.endswith('.map26a')]
    assert len(files) == len({os.path.basename(f) for f in files})
    for k in range(K): os.makedirs(f'{D}panels/{panel}{k}')
    for i, f in enumerate(sorted(files, key=os.path.basename)): os.symlink(f, f'{D}panels/{panel}{i % K}/{os.path.basename(f)}')
    print(panel, len(files), 'maps')

def run(panel, fuel, arms):
    # One slot group for every batch of ours: the pool shares by group, and 56 groups would crowd the other sessions out.
    env = dict(os.environ, CAMBC_BIN=f'{R}tools/fastengine/runner/fastrunner', FASTRUNNER_MODE='native', CAMBC_SLOT_GROUP='comms2', CAMBC_SLOT_WEIGHT='2')
    procs = []
    for arm in arms:
        for o in 'FM':
            for k in range(K):
                n = name(arm, panel, o, fuel, k)
                if os.path.exists(f'{R}replays/ab/{n}/summary.json'): continue
                cmd = [sys.executable, f'{R}tools/ab.py', f'variants/{arm}', f'variants/spar-dvn{k + 1}-{BODY[o]}', '--no-test-draft', '--fuel', str(fuel),
                       '--suites', f'{D}panels/{panel}{k}', '--keep-replays', '1', '--name', n]
                procs.append((n, subprocess.Popen(cmd, cwd=R, env=env, stdout=open(f'{D}logs/{n}.log', 'w'), stderr=subprocess.STDOUT)))
    bad = [n for n, p in procs if p.wait() != 0]
    print('failed:', bad) if bad else print('ok', len(procs))
    return 1 if bad else 0

def cells(n):
    s = json.load(open(f'{R}replays/ab/{n}/summary.json'))
    out = {}; oof = [0, 0]; errors = s['errors']
    for suite in s['suites']:
        res = json.load(open(R + suite['batch'] + '/results.json'))
        for m in res['matches']:
            if m.get('winner') is None: continue
            out[(os.path.basename(m['map'])[:-7], tuple(m['order']))] = 1.0 if m['winner'] == 0 else 0.0
            oof[0] += m['oof_turns'][0]; oof[1] += 1
    return out, oof, errors

def stat(units):
    n = len(units); m = sum(units) / n
    sd = math.sqrt(sum((u - m) ** 2 for u in units) / (n - 1))
    return 100 * m, 196 * sd / math.sqrt(n)

def report(panels, base, arms, fuel):
    print(f'Results against {base} (fuel {fuel}, panels {",".join(panels)}; fresh ladder-v2 maps, both sides, spar-dvn1..4-Flp4 / -Mt3qro):')
    print('| arm | win % | base win % | paired diff (95% CI) | games | Fish diff | Mite diff | flips | OOF turns/game arm, base |')
    print('|---|---|---|---|---|---|---|---|---|')
    for arm in arms:
        by_map = collections.defaultdict(list); by_o = {'F': collections.defaultdict(list), 'M': collections.defaultdict(list)}
        wins = [0.0, 0.0]; n = 0; flips = 0; oofs = [0, 0, 0, 0]
        for panel in panels:
            for o in 'FM':
                for k in range(K):
                    try: x, ox, _ = cells(name(arm, panel, o, fuel, k)); y, oy, _ = cells(name(base, panel, o, fuel, k))
                    except FileNotFoundError: continue
                    for c in x.keys() & y.keys():
                        d = x[c] - y[c]
                        by_map[(panel, c[0])].append(d); by_o[o][(panel, c[0])].append(d)
                        wins[0] += x[c]; wins[1] += y[c]; n += 1; flips += d != 0
                    oofs[0] += ox[0]; oofs[1] += ox[1]; oofs[2] += oy[0]; oofs[3] += oy[1]
        if not n: print(f'| {arm} | no games |'); continue
        m, ci = stat([sum(v) / len(v) for v in by_map.values()])
        split = []
        for o in 'FM':
            mo, co = stat([sum(v) / len(v) for v in by_o[o].values()]) if len(by_o[o]) > 1 else (float('nan'), float('nan'))
            split.append(f'{mo:+.2f} ±{co:.2f}')
        print(f'| {arm} | {100 * wins[0] / n:.2f} | {100 * wins[1] / n:.2f} | {m:+.2f} ({m - ci:+.2f}..{m + ci:+.2f}) | {n} | {split[0]} | {split[1]} | {100 * flips / n:.1f}% |'
              f' {oofs[0] / max(1, oofs[1]):.2f}, {oofs[2] / max(1, oofs[3]):.2f} |')

if __name__ == '__main__':
    a = sys.argv[1:]
    fuel = 100000
    if '--fuel' in a: i = a.index('--fuel'); fuel = int(a[i + 1]); del a[i:i + 2]
    os.makedirs(D + 'logs', exist_ok=True); os.makedirs(D + 'panels', exist_ok=True)
    if a[0] == 'prep': prep(a[1], int(a[2]), int(a[3]))
    elif a[0] == 'run': sys.exit(run(a[1], fuel, a[2:]))
    elif a[0] == 'report': report(a[1].split(','), a[2], a[3:], fuel)
