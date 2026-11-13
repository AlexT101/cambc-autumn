#!/usr/bin/env python3
"""Join the trace copy's BCP lines (our turn's branch and prey()'s verdict on each visible 50+ carrier) with replay
truth: Fish's Vesper distance from the carrier, ours within 6, other Fish within 8, and how the carrier's spell ended.

    python3 tracejoin.py BATCH_DIR EXT_DIR OPP_NAME

BCP fields: round, our handle, branch, carrier handle, pair gems, dist, verdict, carrier hp frac, our hp frac,
our gems, carrier on our ground, carrier channel (0 none, 1 recall, 2 tribute, 3 teleport).
Verdicts: - prey not run; v/s/t/i/c not preyable (vision, near its spawn, teleport, out-of-range healthy carrier we
cannot intercept, pack covers); p preyable (chase_aim only); S not reached (a better target taken); f fuel cut;
l lost fight shared; L fight lost; Y linked self falls; E escapes; A chased; K/J pressed / team-pressed chase.
"""
import collections, gzip, json, os, sys, zipfile

batch, ext, opp = sys.argv[1], sys.argv[2], sys.argv[3]
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
idx = json.load(open(os.path.join(ext, 'index.json')))['games']
bysrc = {os.path.basename(g['source']): g['dir'] for g in idx}
why_all = collections.Counter(); why_opp = collections.Counter(); why_iso = collections.Counter()
branch_opp = collections.Counter(); spell_end_opp = collections.Counter()
eps = []; ng = 0; cross = collections.Counter()
for f in sorted(os.listdir(batch)):
    if not f.endswith('.repl26a') or f not in bysrc: continue
    us = 0 if f[:-8].endswith('-12') else 1
    z = zipfile.ZipFile(os.path.join(batch, f))
    lines = [l.split() for l in z.read('team-%s.stdout' % 'ab'[us]).decode(errors='replace').splitlines() if l.startswith('BCP ')]
    d = os.path.join(ext, bysrc[f])
    m = json.load(open(d + '/meta.json')); ng += 1
    names = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt')); C = {c['id']: c for c in R['champions']}; ri = {r: k for k, r in enumerate(R['round'])}
    ours = [c for c in C.values() if c['team'] == us]; fish = [c for c in C.values() if c['team'] != us]
    fv = [c for c in fish if names[c['id']] == 'Vesper Vale']
    deaths = {}
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'death' and team.get(e['v']) != us: deaths.setdefault(e['v'], []).append((e['r'], e.get('by')))
    for L in lines:
        r, me, br, h, gems, dist, why = int(L[1]), int(L[2]), L[3], int(L[4]), int(L[5]), int(L[6]), L[7]
        k = ri.get(r)
        if k is None or h not in C: continue
        c = C[h]
        if c['x'][k] is None: continue
        pos = (c['x'][k], c['y'][k])
        vd = min([cheb((v['x'][k], v['y'][k]), pos) for v in fv if v['alive'][k] and v['x'][k] is not None] or [99])
        twin = {'Cassi': 'Issac', 'Issac': 'Cassi'}.get(names[h])
        no = sum(1 for o in ours if o['alive'][k] and o['x'][k] is not None and cheb((o['x'][k], o['y'][k]), pos) <= 6)
        fo = sum(1 for g in fish if g['id'] != h and g['alive'][k] and g['x'][k] is not None and names[g['id']] not in ('Vesper Vale', twin)
                 and cheb((g['x'][k], g['y'][k]), pos) <= 8)
        killed = any(r <= dr <= r + 15 and b is not None and team.get(b) == us for dr, b in deaths.get(h, []))
        why_all[why] += 1
        if names[h] == 'Vesper Vale': continue
        if vd > 8 and no >= 2:
            why_opp[why] += 1; branch_opp[br] += 1; cross[(why, br)] += 1
            why_opp['killed15:' + why] += killed
            if fo == 0: why_iso[why] += 1; why_iso['killed15:' + why] += killed
print('games', ng)
def show(c, label):
    tot = sum(v for k, v in c.items() if not k.startswith('killed'))
    print(f'{label}: {tot} unit-turns ({tot/ng:.1f}/game)')
    for k, v in sorted(((k, v) for k, v in c.items() if not k.startswith('killed')), key=lambda kv: -kv[1]):
        kk = c.get('killed15:' + k)
        print(f'   {k}  {v:6d} {v/tot:6.1%}' + (f'   carrier killed by us within 15: {kk/v:.0%}' if kk is not None else ''))
show(why_all, 'all BCP lines (incl. Vesper)')
show(why_opp, 'non-Vesper carrier, Fish Vesper >8, 2+ of ours within 6')
show(why_iso, ' ... and no other Fish within 8')
print('branches in opp:', {k: f'{v/sum(branch_opp.values()):.0%}' for k, v in branch_opp.most_common()})

print('why x branch (opp), top 25:')
tot = sum(cross.values())
for (w, b), v in cross.most_common(25): print(f'   {w} {b} {v:6d} {v/tot:.1%}')
