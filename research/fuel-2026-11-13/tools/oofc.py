"""oofc.py CAND... : OOF turns a game for each CAND and chy-525 on the batches every one of them played."""
import json, sys, glob, os
R = '/home/ubuntu/cambc-autumn/replays/ab/'
bots = sys.argv[1:] + ['chy-525']
for body in ('fr8-g25', 'mf-f9'):
    per = {}
    for bot in bots:
        d = {}
        for f in glob.glob(f'{R}fbe501-{bot}-{body}-m2560b*-Pv4/summary.json'):
            n = os.path.basename(os.path.dirname(f))
            if 'fuel' in n: continue
            x = json.load(open(f)); d[n.split('-m2560')[1][:4]] = (x['oof']['cand'][0], x['games'])
        per[bot] = d
    common = sorted(set.intersection(*(set(d) for d in per.values())))
    ref = sum(per['chy-525'][b][0] for b in common) / sum(per['chy-525'][b][1] for b in common)
    out = [f'{body} {common}: chy-525 {ref:.3f}']
    for bot in bots[:-1]:
        v = sum(per[bot][b][0] for b in common) / sum(per[bot][b][1] for b in common)
        out.append(f'{bot} {v:.3f} ({100*(v/ref-1):+.1f}%)')
    print(' | '.join(out))
