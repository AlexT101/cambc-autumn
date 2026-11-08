"""Paired live games (vA vs vB, same map/side/opp ref): first round positions / items / casts differ, and who flips."""
import json, gzip, os, sys, collections
H = os.path.expanduser('~/tmp-offload/')
sys.path.insert(0, H + 'emblem/tools'); from live_items import load
A, B = int(sys.argv[1]), int(sys.argv[2])
G = {}; L = {}
for gj, ana in ((H + 'bigl/games.json', H + 'bigl/ana'), (H + 'emblem/games9091.json', H + 'emblem/ana')):
    L.update(load(ana)); G.update(json.load(open(gj)))
cells = collections.defaultdict(dict)
for mid, g in G.items():
    if g['version'] in (A, B) and g.get('refset') == 'r2' and mid in L:
        cells[(g['map'], g['side'], g['opp_name'], g.get('position'))][g['version']] = (mid, g)
def first_diff(da, db, us):
    Ra = json.load(gzip.open(da + '/rounds.json.gz')); Rb = json.load(gzip.open(db + '/rounds.json.gz'))
    n = min(len(Ra['round']), len(Rb['round']))
    pos = items = None; who = None
    for i in range(n):
        for ca, cb in zip(Ra['champions'], Rb['champions']):
            if pos is None and (ca['x'][i] != cb['x'][i] or ca['y'][i] != cb['y'][i]): pos = i + 1; who = ('us' if ca['team'] == us else 'them')
            if items is None and ca['team'] == us and ca['items'][i] != cb['items'][i]: items = i + 1
        if pos is not None and items is not None: break
    return pos, items, who
out = []
for k, v in cells.items():
    if A in v and B in v:
        (ma, ga), (mb, gb) = v[A], v[B]
        us = 0 if ga['side'] == 'a' else 1
        p, it, who = first_diff(L[ma], L[mb], us)
        out.append(dict(cell=k, ra=ga['result'], rb=gb['result'], pos=p, items=it, who=who, opp_picks=ga['opp_picks'], our=ga['our_picks']))
json.dump(out, open(H + f'emblem/diverge-{A}-{B}.json', 'w'))
same = [o for o in out if o['pos'] is None]; print('pairs', len(out), 'identical', len(same))
fl = [o for o in out if o['ra'] != o['rb']]
print('flips', len(fl), 'for A', sum(o['ra'] == 'win' for o in fl), 'for B', sum(o['rb'] == 'win' for o in fl))
shopfirst = [o for o in out if o['pos'] and o['items'] and o['items'] <= o['pos']]
print('items diverge at or before positions:', len(shopfirst), 'of', sum(1 for o in out if o['pos']))
for grp, name in ((shopfirst, 'shop-first'), ([o for o in out if o['pos'] and not (o['items'] and o['items'] <= o['pos'])], 'other-first')):
    f = [o for o in grp if o['ra'] != o['rb']]
    print(f'  {name}: n={len(grp)} flips {len(f)}: A {sum(o["ra"]=="win" for o in f)} B {sum(o["rb"]=="win" for o in f)}')
