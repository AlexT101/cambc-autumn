"""oof.py CAND [FUELTAG] : OOF turns a game for CAND and chy-525 over the fgate runs present (fr8-g25, mf-f9, pool v4)."""
import json, sys, glob, os
cand = sys.argv[1]; tag = sys.argv[2] if len(sys.argv) > 2 else ''
R = '/home/ubuntu/cambc-autumn/replays/ab/'
for body in ('fr8-g25', 'mf-f9'):
    tot = {}
    for bot in (cand, 'chy-525'):
        t = g = 0; bs = []
        for f in sorted(glob.glob(f'{R}fbe501-{bot}-{body}-m2560b*{tag}-Pv4/summary.json')):
            n = os.path.basename(os.path.dirname(f))
            if tag == '' and 'fuel' in n: continue
            x = json.load(open(f)); t += x['oof']['cand'][0]; g += x['games']; bs.append(n.split('-m2560')[1][:4])
        tot[bot] = (t, g, bs)
    (ct, cg, cb), (rt, rg, rb) = tot[cand], tot['chy-525']
    common = sorted(set(cb) & set(rb))
    print(f'{body}: {cand} {ct/max(cg,1):.2f}/game ({cg} games, {cb}) | chy-525 {rt/max(rg,1):.2f}/game ({rg} games, {rb}) | ratio {(ct/max(cg,1))/(rt/max(rg,1)) if rt else 0:.3f}')
