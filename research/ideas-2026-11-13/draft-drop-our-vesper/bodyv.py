import json, sys, math, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools')
import local
units = {r['map']: r for r in json.load(open('units-draft-drop-our-vesper--fuel200000.json'))}
out = {}
for o, body in (('F', 'fr8-g25'), ('M', 'mf-f9')):
    mine = local.cells(f'ddov-bp-{body}-b000'); ref = local.cells(f'fbe501-chy-525-{body}-m2560b000-fuel200000-Pv4')
    same = sum(mine[c] == ref[c] for c in mine.keys() & ref.keys()); print(body, 'determinism', same, 'of', len(mine.keys() & ref.keys()))
    d = local.drafts(f'ddov-bp-{body}-b000')
    out[o] = {f'{m}|{s}': v for (m, s), v in d.items()}
    print(body, 'drafts', len(d))
json.dump(out, open('bodypicks-b000.json', 'w'))
cand = {o: local.cells(f'fbe501-draft-drop-our-vesper-{b}-m2560b000-fuel200000-Pv4') for o, b in (('F', 'fr8-g25'), ('M', 'mf-f9'))}
refc = {o: local.cells(f'fbe501-chy-525-{b}-m2560b000-fuel200000-Pv4') for o, b in (('F', 'fr8-g25'), ('M', 'mf-f9'))}
lad = {l.strip() for l in open('/home/ubuntu/cambc-autumn/tools/ladder128.txt') if l.strip()}
def est(v):
    n = len(v); m = sum(v) / n; sd = math.sqrt(sum((a - m) ** 2 for a in v) / (n - 1))
    return f'{100*m:+.2f} ±{196*sd/math.sqrt(n):.2f} (n {n})'
for o in 'FM':
    g = collections.defaultdict(list); share = collections.Counter()
    for key, (ours, opp) in out[o].items():
        m, s = key.split('|')
        if m in lad or (m, s) not in cand[o] or (m, s) not in refc[o]: continue
        ov = 'Vesper Vale' in opp; share[ov] += 1
        if not (units.get(m) and units[m]['refV']): continue
        g[ov].append(cand[o][(m, s)] - refc[o][(m, s)])
    print(o, 'body drafts Vesper share (fresh games):', round(share[True] / (share[True] + share[False]), 3))
    for k in (True, False):
        if g[k]: print(f'   our-Vesper maps, body Vesper={k}: ban effect {est(g[k])}')
