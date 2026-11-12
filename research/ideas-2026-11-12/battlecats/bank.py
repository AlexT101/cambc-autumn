"""Banking: tributes, carriers, locks, teleport crystals, recalls, wards, shopping. BattleCats against its opponents.
python3 bank.py [ver,...]"""
import sys, collections
import fl
vers = sys.argv[1].split(',') if len(sys.argv) > 1 else ['cur']
G = fl.load(lambda g: g['ver'] in vers)
print(len(G), 'games', vers, collections.Counter(g['oc'] for g in G))

def altar_side(g, alt, t):
    do = fl.cheb(alt, fl.spawn_c(g, t)); de = fl.cheb(alt, fl.spawn_c(g, 1 - t))
    return 'own' if do < de - 2 else 'enemy' if de < do - 2 else 'mid'

for who in ('bc', 'opp'):
    n = len(G); T = []; outc = collections.Counter(); by = collections.Counter(); side = collections.Counter(); bags = []
    first = []; big = 0; bigdone = 0
    for g in G:
        t = g['bc'] if who == 'bc' else 1 - g['bc']
        mine = [x for x in g['tribs'] if g['team'][x[1]] == t]
        if mine: first.append(mine[0][0])
        for r, a, gems, dur, alt, oc, er, tot in mine:
            T.append(gems); outc[oc] += 1; by[g['name'][a]] += 1; side[altar_side(g, alt, t)] += 1
            if gems >= 100:
                big += 1; bigdone += oc == 'end'
    m = len(T); Ts = sorted(T)
    q = lambda p: Ts[int(p * (m - 1))] if m else 0
    print(f'\n== {who}: tributes {m / n:.1f}/game, bag at start p25/50/75/90 {q(.25)}/{q(.5)}/{q(.75)}/{q(.9)}, first tribute round median {fl.med(first)}')
    print(f'  outcome: {", ".join(f"{k} {fl.pct(v, m)}" for k, v in outc.most_common())}; 100+ bags {big / n:.2f}/game, completed {fl.pct(bigdone, big)}')
    print(f'  who: {", ".join(f"{k} {fl.pct(v, m)}" for k, v in by.most_common(7))}; altar: {", ".join(f"{k} {fl.pct(v, m)}" for k, v in side.most_common())}')

# carry: team carried gems at checkpoints
for who in ('bc', 'opp'):
    row = []
    for r in ('200', '400', '600', '1000'):
        S = [g for g in G if r in g['ck']]
        if S: row.append(f'r{r} {fl.mean(g["ck"][r]["carry"][g["bc"] if who == "bc" else 1 - g["bc"]] for g in S):.0f}')
    print(f'{who} team carried gems: ' + ', '.join(row))

# Prism: its bag and fate
pb = []; pd = []
for g in G:
    for cid, nm in g['name'].items():
        if nm == 'Prism' and g['team'][cid] == g['bc']:
            pd.append(sum(1 for d in g['deaths'] if d[1] == cid))
            pb.append(sum(d[3] or 0 for d in g['deaths'] if d[1] == cid))
if pd: print(f'\nBC Prism: in {len(pd)} games, deaths {fl.mean(pd):.2f}/game, gems lost on death {fl.mean(pb):.0f}/game')

# locks
for who in ('bc', 'opp'):
    L = []; first = []; during = 0; sides = collections.Counter(); near = []
    for g in G:
        t = g['bc'] if who == 'bc' else 1 - g['bc']
        mine = [x for x in g['locks'] if x[2] == t]
        if mine: first.append(mine[0][0])
        for r, a, tm, alt, et, nd in mine:
            L.append(r); during += bool(et); sides[altar_side(g, alt, t)] += 1; near.append(nd)
    n = len(G); m = len(L) or 1
    print(f'\n== {who} locks: {len(L) / n:.2f}/game, games with any {fl.pct(len(first), n)}, first lock round median {fl.med(first)}, '
          f'during an enemy tribute there {fl.pct(during, m)}; altar {dict((k, fl.pct(v, m)) for k, v in sides.items())}; '
          f'nearest enemy at placement median {fl.med(near)}')
    des = sum(1 for g in G for x in g['lockdes'] if x[1] != (g['bc'] if who == 'bc' else 1 - g['bc']))
    print(f'  enemy locks destroyed by {who}: {des / n:.2f}/game')

# crystals, recalls, wards
for who in ('bc', 'opp'):
    tp = []; tpg = []; rc = []; rcg = []; wd = []
    for g in G:
        t = g['bc'] if who == 'bc' else 1 - g['bc']
        x = [p for p in g['tps'] if g['team'][p[1]] == t]; tp.append(len(x)); tpg += [p[4] for p in x]
        y = [p for p in g['recalls'] if g['team'][p[1]] == t]; rc.append(len(y)); rcg += [p[2] or 0 for p in y]
        wd.append(sum(1 for w in g['wards'] if g['team'][w[1]] == t))
    print(f'{who}: teleports {fl.mean(tp):.2f}/game (bag median {fl.med(tpg)}), completed recalls {fl.mean(rc):.1f}/game (bag median {fl.med(rcg)}), wards {fl.mean(wd):.0f}/game')

# shopping: emblem families per champion type (final emblems), BC only
ITEMS = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospector', 'Hunter', 'Skirmish', 'Greed', 'Collectors']
STAT = ['Strength', 'Focus', 'Health']
emb = collections.defaultdict(collections.Counter); cnt = collections.Counter(); shards = collections.defaultdict(collections.Counter)
cons = collections.defaultdict(lambda: [0, 0, 0, 0])
for g in G:
    for cid, nm in g['name'].items():
        if g['team'][cid] != g['bc']: continue
        cnt[nm] += 1
        L = g['items'][str(cid)]
        for i in range(0, len(L), 2):
            it, c = L[i], L[i + 1]
            fam, kind, stat = ITEMS[it // 6], ('Emblem' if it % 2 else 'Shard'), STAT[(it % 6) // 2]
            if kind == 'Emblem': emb[nm][f'{fam}-{stat[0]}'] += c
            else: shards[nm][stat] += c
        for j, c in enumerate(g['cons'][str(cid)]): cons[nm][j] += c
print('\nBC builds (per game): emblems; shards bought by stat; consumables [crystal, control ward, lock, scroll]')
for nm in sorted(cnt, key=lambda k: -cnt[k]):
    n = cnt[nm]
    print(f'  {nm} ({n}): ' + ', '.join(f'{k} {v / n:.1f}' for k, v in emb[nm].most_common(5)) +
          ' | shards ' + ', '.join(f'{k[0]} {v / n:.0f}' for k, v in shards[nm].most_common()) + ' | cons ' + str([round(x / n, 2) for x in cons[nm]]))
