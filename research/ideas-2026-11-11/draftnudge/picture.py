"""Pick-rate picture: ocean 506's model draft against Fish's and Mite's ladder drafts, by pick count.
    py picture.py WORK   (WORK holds ladder-top.json from extract.py and teams-base-{ladder,v2}.txt from model.mjs teams)"""
import json, sys, collections
W = sys.argv[1]
CH = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi & Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'Heart of Ruin']
enum = lambda n: n.lower().replace(' & ', '_and_').replace(' ', '_')
E2N = {enum(c): c for c in CH}
rows = json.load(open(f'{W}/ladder-top.json'))
FISH, MITE, US = 'Intercontinental Fish', 'Mite', 'stellar best girl'
def cells(team, lo, hi='9'):
    c = collections.defaultdict(list)
    for r in rows:
        if r['team'] == team and lo <= r['day'] <= hi: c[(r['map'], r['side'])].append(r['picks'])
    return c
def rates(c):
    """Inclusion per champion by pick count, every (map, side) cell weighted equally, repeats within a cell equally."""
    out = {}
    for p in (3, 4, 5, 0):
        cc = [v for v in c.values() if p == 0 or len(v[0]) == p]
        inc = collections.Counter()
        for v in cc:
            for picks in v:
                for x in picks: inc[x] += 1 / len(v) / len(cc)
        out[p] = inc
    return out
def ocean(f):
    c = {}
    for l in open(f):
        k, p, name, t = l.split()
        c[(name, 'x')] = [[E2N[x] for x in t.split(',')]]
    return c
T = {'ocean506 ladder': rates(ocean(f'{W}/teams-base-ladder.txt')), 'ocean506 fresh': rates(ocean(f'{W}/teams-base-v2.txt')),
     'Fish 11-09..11': rates(cells(FISH, '2026-11-09')), 'Mite 11-09..11': rates(cells(MITE, '2026-11-09')),
     'Fish 11-06..08': rates(cells(FISH, '2026-11-06', '2026-11-08')), 'Mite 11-06..08': rates(cells(MITE, '2026-11-06', '2026-11-08'))}
oth = collections.defaultdict(list)
for r in rows:
    if r['day'] >= '2026-11-09' and r['rank'] <= 10 and r['team'] not in (FISH, MITE, US): oth[(r['team'], r['map'], r['side'])].append(r['picks'])
T['other top10'] = rates(oth)
for p in (3, 4, 5, 0):
    print(f'\n== {"all pick counts" if p == 0 else f"{p} picks"}: % of teams holding the champion ==')
    print(f'{"":14s}' + ''.join(f'{k:>16s}' for k in T))
    for c in sorted(CH, key=lambda c: -T['ocean506 ladder'][p][c]):
        print(f'{c:14s}' + ''.join(f'{100 * T[k][p][c]:16.0f}' for k in T))
# Stability: share of (map, side) cells with more than one comp, and cells whose modal comp changed between windows
for team in (FISH, MITE):
    a, b = cells(team, '2026-11-06', '2026-11-08'), cells(team, '2026-11-09')
    multi = sum(len({tuple(sorted(x)) for x in v}) > 1 for v in b.values())
    mode = lambda v: collections.Counter(tuple(sorted(x)) for x in v).most_common(1)[0][0]
    ch = sum(mode(a[k]) != mode(b[k]) for k in a.keys() & b.keys())
    print(f'{team}: {len(b)} cells 11-09..11, {multi} with more than one comp; modal comp changed since 11-06..08 on {ch} of {len(a.keys() & b.keys())} cells; drafts {sum(map(len, b.values()))}')
