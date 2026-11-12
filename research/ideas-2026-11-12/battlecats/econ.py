"""Economy: what BattleCats captures first, where, and how its income compares. Both teams measured the same way.
python3 econ.py [ver,...]"""
import sys, collections
import fl
vers = sys.argv[1].split(',') if len(sys.argv) > 1 else ['cur']
G = fl.load(lambda g: g['ver'] in vers)
print(len(G), 'games', vers, collections.Counter(g['oc'] for g in G))

def gside(g, q, t):
    tiles = q[4]; so, se = fl.spawn_c(g, t), fl.spawn_c(g, 1 - t)
    do = min(fl.cheb(x, so) for x in tiles); de = min(fl.cheb(x, se) for x in tiles)
    return ('own' if do < de - 2 else 'enemy' if de < do - 2 else 'mid'), do

for who in ('bc', 'opp'):
    first = collections.Counter(); firstn = collections.defaultdict(collections.Counter)
    side300 = collections.Counter(); type300 = collections.Counter(); r1 = []; caps300 = []
    rank_d = []
    for g in G:
        t = g['bc'] if who == 'bc' else 1 - g['bc']
        Q = {q[0]: q for q in g['groups']}
        mine = [c for c in g['caps'] if c[2] == t]
        if mine: r1.append(mine[0][0])
        caps300.append(sum(1 for c in mine if c[0] <= 300))
        for i, c in enumerate(mine[:5]):
            q = Q[c[1]]; s, d = gside(g, q, t)
            firstn[i][(fl.gtype(q[1]), s)] += 1
        for c in mine:
            if c[0] > 300: break
            q = Q[c[1]]; s, d = gside(g, q, t); side300[s] += 1; type300[fl.gtype(q[1])] += 1
        # distance rank of the first capture among groups (by distance from own spawn)
        if mine:
            q = Q[mine[0][1]]; ds = sorted(gside(g, x, t)[1] for x in g['groups'])
            rank_d.append(ds.index(gside(g, q, t)[1]))
    print(f'\n== {who}: first capture round median {fl.med(r1)}, captures by r300 mean {fl.mean(caps300):.1f}')
    print(' first-capture distance rank among all groups (0 = nearest):', collections.Counter(rank_d).most_common(6))
    for i in range(3):
        n = sum(firstn[i].values())
        print(f' capture #{i + 1}:', ', '.join(f'{k[0]}/{k[1]} {fl.pct(v, n)}' for k, v in firstn[i].most_common(7)))
    n = sum(side300.values())
    print(' captures r<=300 by side:', {k: fl.pct(v, n) for k, v in side300.items()}, ' by type:', {k: fl.pct(v, n) for k, v in type300.most_common()})

# income timeline by opponent class
print('\n== checkpoints (BC minus opponent), mean over games')
for oc in ('us', 'Fish', 'Mite', 'other'):
    S = [g for g in G if g['oc'] == oc]
    if not S: continue
    row = []
    for r in ('100', '200', '400', '600', '1000'):
        T = [g for g in S if r in g['ck']]
        if not T: continue
        dg = fl.mean(g['ck'][r]['gems'][g['bc']] - g['ck'][r]['gems'][1 - g['bc']] for g in T)
        de = fl.mean(g['ck'][r]['earned'][g['bc']] - g['ck'][r]['earned'][1 - g['bc']] for g in T)
        dk = fl.mean(g['ck'][r]['kills'][g['bc']] - g['ck'][r]['kills'][1 - g['bc']] for g in T)
        row.append(f'r{r}: gems {dg:+.0f} gold {de:+.0f} kills {dk:+.1f} (n{len(T)})')
    print(f' {oc} ({len(S)} games, BC wins {fl.pct(sum(1 for g in S if g["win"]), len(S))}):', ' | '.join(row))

# steals: BC captures of groups on the enemy's side, and enemy captures on BC's side, per game
for who in ('bc', 'opp'):
    st = []
    for g in G:
        t = g['bc'] if who == 'bc' else 1 - g['bc']
        Q = {q[0]: q for q in g['groups']}
        st.append(sum(1 for c in g['caps'] if c[2] == t and gside(g, Q[c[1]], t)[0] == 'enemy'))
    print(f'{who}: enemy-side captures per game {fl.mean(st):.1f}')

# share recipients: who takes capture gems (carrier), BC
tot = collections.Counter(); totg = collections.Counter()
for g in G:
    for c in g['caps']:
        if c[2] != g['bc']: continue
        for cid, gems, gold in c[3]:
            tot[g['name'][cid]] += gems; totg[g['name'][cid]] += gold
s = sum(tot.values())
print('\nBC capture gems by champion:', ', '.join(f'{k} {fl.pct(v, s)}' for k, v in tot.most_common()))
s = sum(totg.values())
print('BC capture gold by champion:', ', '.join(f'{k} {fl.pct(v, s)}' for k, v in totg.most_common()))
