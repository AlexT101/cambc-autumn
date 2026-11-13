"""Prism follow-up: time budget by destination, capture provenance, capture rate. python3 prism_study.py [--threads N]"""
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from statistics import mean

import extract_study as X

OUTP = X.OUT.parent / 'out_prism'


def top_type(tys):
    for t in ('Monolith', 'Golem', 'Elk', 'Wolf'):
        if t in tys:
            return t
    return 'gems' if 'Gem cluster' in tys else 'gold'


def work(d):
    g = X.Game(d)
    V = X.View(d, None)
    mp = g.map
    N = len(g.rounds['round'])
    src = X.WT / [s['source'] for s in g.meta['sources'] if s['source'].endswith('-12.repl26a')][0]
    D, _ = X.parse_D(src)
    W = g.winner
    team_of, name = g.team_of, g.name_of
    ids = [c['id'] for c in g.champs]
    C = {c: g.ch(c) for c in ids}
    ng = len(mp.groups)
    bl = set(mp.walls) | set(mp.holes) | set(mp.altars)
    gdist = {grp['id']: X.bfs(mp, grp['tiles'], bl) for grp in mp.groups}
    altar_d = X.bfs(mp, [(a[0] + dx, a[1] + dy) for a in mp.altars for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                         if (a[0] + dx, a[1] + dy) not in bl], bl)
    spawn_tiles = []
    for t in (0, 1):
        s = mp.spawn[t]
        spawn_tiles.append([(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)])
    sp_d = [X.bfs(mp, spawn_tiles[t], bl | set(spawn_tiles[1 - t])) for t in (0, 1)]
    rows = sorted(g.rounds['groups'], key=lambda x: x[0])
    gst = [[None] * ng for _ in range(N + 2)]
    cur = [None] * ng
    k = 0
    for r in range(1, N + 2):
        while k < len(rows) and rows[k][0] <= r - 1:
            cur[rows[k][1]] = rows[k]
            k += 1
        gst[r] = list(cur)
    gst[1] = [next((x for x in rows if x[1] == gi), None) for gi in range(ng)]

    def spos(c, r):
        return g.pos(c, g.start_idx(r)) if r > 1 else V.pos(c, 0)

    camp_group = {c['id']: c['group'] for c in mp.camps}
    hit_r = defaultdict(lambda: defaultdict(set))  # champ -> round -> groups hit
    cyc_dmg = defaultdict(lambda: defaultdict(float))  # (group, cycle idx) -> champ -> dmg
    cycle = [0] * ng
    clears = []  # (r, s, g, by)
    caps = []
    respawns = defaultdict(list)
    for e in g.events:
        k_ = e['k']
        if k_ in ('attack', 'cast') and e.get('cdmg'):
            for cc, amt in e['cdmg']:
                gi = camp_group[cc]
                hit_r[e['a']][e['r']].add(gi)
                cyc_dmg[(gi, cycle[gi])][e['a']] += amt
        elif k_ == 'group_clear':
            clears.append((e['r'], e['s'], e['g'], e.get('by'), cycle[e['g']]))
        elif k_ == 'capture':
            caps.append((e['r'], e['s'], e['g'], e['team'], e['shares'], cycle[e['g']]))
        elif k_ == 'group_respawn':
            cycle[e['g']] += 1
            respawns[e['g']].append(e['r'])

    def clear_of(gi, r):
        cl = [x for x in clears if x[2] == gi and x[0] <= r]
        return cl[-1] if cl else None

    prisms = [c for c in ids if name[c] == 'Prism']
    res = {'dir': d, 'winner': W, 'N': N, 'prisms': [], 'teamcap': {}}
    # team capture gems by phase
    for t in (0, 1):
        tc = [0, 0]
        for r, s, gi, tm, shares, cy in caps:
            if tm == t:
                tc[r > 300] += sum(x[1] for x in shares)
        res['teamcap'][str(t)] = tc
    for p in prisms:
        t = team_of[p]
        allies = [c for c in g.team_ids[t] if c != p]
        willows = [c for c in allies if name[c] == 'Willow']
        budget = Counter()
        willow_walk = Counter()
        alive = [0, 0]
        for r in range(1, N + 1):
            i = r - 1
            if not C[p]['alive'][i] or C[p]['turn'][i] == 4:
                continue
            ph = int(r > 300)
            alive[ph] += 1
            x = D.get((r, p), ('?', -1, -1))
            ch, fg = x[0], x[1]
            tk = C[p]['turn'][i]
            p0 = spos(p, r)
            p1 = g.pos(p, i)
            moved = p0 is not None and p1 is not None and p0 != p1
            hits = hit_r[p].get(r)
            cls = None
            if tk == 3 or ch in 'TKQkt':
                cls = {'T': 'tribute', 'K': 'recall', 'Q': 'capture-recall', 'k': 'recall', 't': 'tribute'}.get(ch, 'channel')
            elif hits:
                cls = 'clear:' + top_type(mp.groups[next(iter(hits))]['types'])
            elif p1 and p1 in mp.group_tiles and gst[min(r + 1, N + 1)][mp.group_tiles[p1]] and gst[min(r + 1, N + 1)][mp.group_tiles[p1]][2] == 2:
                cls = 'hold'
            elif ch == 'R':
                cls = 'retreat'
            elif ch in 'CA':
                cls = 'chase'
            elif ch in 'BW':
                cls = 'to altar (B/W)'
            elif ch in 'HS' or (p0 and mp.in_spawn(t, p0)):
                cls = 'home/spawn (H/S)'
            elif ch == 'r':
                cls = 'prism_recovery (r)'
            elif moved and 0 <= fg < ng:
                row = gst[r][fg]
                st = row[2] if row else 1
                if st == 2:
                    cl = clear_of(fg, r)
                    who = 'none' if not cl or cl[3] not in team_of else ('self' if cl[3] == p else ('ally' if team_of[cl[3]] == t else 'enemy'))
                    cls = 'walk to cleared, clear by ' + who
                elif st == 1:
                    # will the Prism hit it within 40 rounds?
                    own = any(fg in hit_r[p].get(rr, ()) for rr in range(r, min(N, r + 40) + 1))
                    cls = 'walk to live, Prism hits it' if own else 'walk to live, Prism does not hit it'
                else:
                    cls = 'walk to respawning'
            elif moved:
                cls = 'walk, no target (' + ch + ')'
            else:
                cls = 'still (' + ch + ')'
            budget[f'{ph}|{cls}'] += 1
            if moved and cls.startswith('walk') and willows:
                wn = min((X.chebyshev(p1, g.pos(w, i)) for w in willows if g.pos(w, i)), default=99)
                willow_walk[f'{ph}|{"willow<=3" if wn <= 3 else "willow>3"}'] += 1
        # captures with the Prism in shares
        pcaps = []
        for r, s, gi, tm, shares, cy in caps:
            sh = {x[0]: x for x in shares}
            if p not in sh:
                continue
            dm = cyc_dmg.get((gi, cy), {})
            mine = dm.get(p, 0)
            ally = sum(v for c, v in dm.items() if c in allies)
            enemy = sum(v for c, v in dm.items() if team_of.get(c) == 1 - t)
            cl = [x for x in clears if x[2] == gi and x[4] == cy]
            clby = cl[-1][3] if cl else None
            if clby is not None and team_of.get(clby) == 1 - t:
                who = 'enemy cleared'
            elif mine > 0 and ally == 0:
                who = 'Prism alone'
            elif mine > 0:
                who = 'Prism with allies'
            elif ally > 0:
                who = 'allies only'
            else:
                who = 'unknown'
            # hold start: walk back while on the group's tiles
            tiles = {tuple(tt) for tt in mp.groups[gi]['tiles']}
            h = r - 1
            while h > 1 and g.pos(p, h - 2) in tiles:
                h -= 1
            w = 0
            rr = h - 1
            while rr > 1 and spos(p, rr) and g.pos(p, rr - 1) and spos(p, rr) != g.pos(p, rr - 1) and not hit_r[p].get(rr):
                w += 1
                rr -= 1
            pcaps.append({'r': r, 'who': who, 'gems': sh[p][1], 'total': sum(x[1] for x in shares), 'n_share': len(shares),
                          'walk': w, 'hold': r - h, 'type': top_type(mp.groups[gi]['types']), 'share': mine / (mine + ally) if mine + ally else None})
        # ally-cleared gem groups near the Prism
        near = []
        for r, s, gi, by, cy in clears:
            if by not in team_of or team_of[by] != t or by == p or mp.groups[gi]['gems'] == 0:
                continue
            pp = spos(p, r)
            if not pp or not C[p]['alive'][r - 1]:
                continue
            dd = gdist[gi].get(pp, 99)
            if dd > 15:
                continue
            nxt = [x for x in caps if x[2] == gi and x[5] == cy]
            if not nxt:
                out = 'uncaptured'
                gems = mp.groups[gi]['gems']
            else:
                c0 = nxt[0]
                gems = sum(x[1] for x in c0[4])
                if c0[3] != t:
                    out = 'enemy captured'
                elif any(x[0] == p for x in c0[4]):
                    out = 'Prism shared'
                else:
                    out = 'ally only'
            near.append({'r': r, 'dist': dd, 'out': out, 'gems': gems, 'type': top_type(mp.groups[gi]['types']),
                         'pch': D.get((r, p), ('?',))[0], 'pcarry': C[p]['gems'][r - 1]})
        capg = [0, 0]
        for c_ in pcaps:
            capg[c_['r'] > 300] += c_['gems']
        res['prisms'].append({'id': p, 't': t, 'won': t == W, 'alive': alive, 'budget': dict(budget), 'willow': dict(willow_walk),
                              'caps': pcaps, 'near': near, 'capg': capg, 'n_prism_team': sum(1 for c in prisms if team_of[c] == t),
                              'has_willow': bool(willows)})
    OUTP.mkdir(exist_ok=True)
    (OUTP / f'{d}.json').write_text(json.dumps(res))
    return d


def report():
    G = [json.loads(p.read_text()) for p in sorted(OUTP.glob('*.json'))]
    NG = len(G)
    P = [p for g in G for p in g['prisms']]
    WL = {True: 'winner', False: 'loser'}
    pct = lambda a, b: f'{100 * a / b:.1f}%' if b else '-'
    print(f'games {NG}; Prism bodies {len(P)} (winner {sum(p["won"] for p in P)}, loser {sum(not p["won"] for p in P)}); '
          f'teams with 2 Prisms {sum(1 for p in P if p["n_prism_team"] > 1)}; Prism teams with Willow {pct(sum(p["has_willow"] for p in P), len(P))}')
    print('\n== P1 time budget (share of alive rounds)')
    for ph in (0, 1):
        for won in (True, False):
            sub = [p for p in P if p['won'] == won]
            b = Counter()
            for p in sub:
                for k, v in p['budget'].items():
                    if int(k[0]) == ph:
                        b[k[2:]] += v
            tot = sum(b.values())
            ww = Counter()
            for p in sub:
                for k, v in p['willow'].items():
                    if int(k[0]) == ph:
                        ww[k[2:]] += v
            print(f'  {"r1-300" if ph == 0 else "r301+"} {WL[won]} ({tot / len(sub):.0f} alive rounds/Prism): walk rounds with a Willow within 3 '
                  f'{pct(ww["willow<=3"], ww["willow<=3"] + ww["willow>3"])}')
            for k, v in b.most_common(18):
                print(f'      {k:42s} {pct(v, tot)}')
    print('\n== P2 Prism captures')
    for won in (True, False):
        cs = [c for p in P if p['won'] == won for c in p['caps']]
        n = len(cs)
        npr = sum(1 for p in P if p['won'] == won)
        print(f'  {WL[won]}: {n / npr:.1f} captures/Prism-game, gems/capture {mean(c["gems"] for c in cs):.1f}')
        for who in ('Prism alone', 'Prism with allies', 'allies only', 'enemy cleared', 'unknown'):
            s = [c for c in cs if c['who'] == who]
            if s:
                ws = sorted(c['walk'] for c in s)
                print(f'    {who:18s} {pct(len(s), n):>6s} of captures, {pct(sum(c["gems"] for c in s), sum(c["gems"] for c in cs)):>6s} of gems, '
                      f'gems/cap {mean(c["gems"] for c in s):.1f}, sharers {mean(c["n_share"] for c in s):.2f}, '
                      f'walk before hold q50 {ws[len(ws) // 2]} q75 {ws[3 * len(ws) // 4]}, hold rounds {mean(c["hold"] for c in s):.1f}, '
                      f'types {Counter(c["type"] for c in s).most_common(3)}')
        wm = [c for c in cs if c['who'] == 'Prism with allies' and c['share'] is not None]
        if wm:
            print(f'    Prism share of its team damage when clearing with allies: mean {mean(c["share"] for c in wm):.2f}')
    print('  ally-cleared gem groups within 15 steps of the Prism at the clear:')
    for won in (True, False):
        ns = [x for p in P if p['won'] == won for x in p['near']]
        npr = sum(1 for p in P if p['won'] == won)
        c = Counter(x['out'] for x in ns)
        gm = Counter()
        for x in ns:
            gm[x['out']] += x['gems']
        print(f'    {WL[won]}: {len(ns) / npr:.1f}/Prism-game; ' + ', '.join(f'{k} {v / npr:.1f}/game ({gm[k] / npr:.0f} gems)' for k, v in c.most_common()))
        ao = [x for x in ns if x['out'] == 'ally only']
        if ao:
            print(f'      ally-only: dist q50 {sorted(x["dist"] for x in ao)[len(ao) // 2]}, Prism D then {Counter(x["pch"] for x in ao).most_common(5)}, '
                  f'types {Counter(x["type"] for x in ao).most_common(3)}, Prism carrying q50 {sorted(x["pcarry"] for x in ao)[len(ao) // 2]}')
    print('\n== P3 Prism capture gems per 100 alive rounds')
    for won in (True, False):
        sub = [p for p in P if p['won'] == won]
        for ph in (0, 1):
            g_ = sum(p['capg'][ph] for p in sub)
            a = sum(p['alive'][ph] for p in sub)
            print(f'  {WL[won]} {"r1-300" if ph == 0 else "r301+"}: {100 * g_ / a:.1f} gems/100 alive rounds')
        tg = sum(g['teamcap'][str(p['t'])][0] + g['teamcap'][str(p['t'])][1] for g in G for p in g['prisms'] if p['won'] == won)
        print(f'    Prism share of team capture gems {pct(sum(sum(p["capg"]) for p in sub), tg)}')
    # result vs r300 Prism gems (games with exactly one Prism a side)
    rows = []
    for g in G:
        byt = defaultdict(list)
        for p in g['prisms']:
            byt[p['t']].append(p)
        if len(byt[0]) != 1 or len(byt[1]) != 1:
            continue
        a, b = byt[0][0], byt[1][0]
        rows.append((a['capg'][0] - b['capg'][0], g['teamcap']['0'][0] - g['teamcap']['1'][0], 1 if g['winner'] == 0 else 0,
                     a['capg'][0], b['capg'][0]))

    def corr(xs, ys):
        mx, my = mean(xs), mean(ys)
        sx = sum((x - mx) ** 2 for x in xs) ** 0.5
        sy = sum((y - my) ** 2 for y in ys) ** 0.5
        return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else float('nan')
    print(f'  games with one Prism a side: {len(rows)}')
    print(f'    corr(A-B Prism capture gems by r300, A wins) {corr([r[0] for r in rows], [r[2] for r in rows]):.2f}; '
          f'corr(A-B team capture gems by r300, A wins) {corr([r[1] for r in rows], [r[2] for r in rows]):.2f}; '
          f'corr(A-B team non-Prism capture gems) {corr([r[1] - r[0] for r in rows], [r[2] for r in rows]):.2f}')
    hi = [r for r in rows if r[0] != 0]
    print(f'    side whose Prism had more capture gems by r300 won {pct(sum((r[0] > 0) == (r[2] == 1) for r in hi), len(hi))} ({len(hi)} games); '
          f'side with more team capture gems by r300 won {pct(sum((r[1] > 0) == (r[2] == 1) for r in rows if r[1]), sum(1 for r in rows if r[1]))}')
    for lo, hi_ in ((0, 1), (1, 50), (50, 100), (100, 10 ** 6)):
        s = [r for r in rows for v, w in ((r[3], r[2]), (r[4], 1 - r[2])) if lo <= v < hi_]
    buckets = defaultdict(lambda: [0, 0])
    for r in rows:
        for v, w in ((r[3], r[2]), (r[4], 1 - r[2])):
            b = 0 if v == 0 else 1 if v < 40 else 2 if v < 80 else 3
            buckets[b][0] += 1
            buckets[b][1] += w
    print('    win rate by own Prism capture gems by r300: ' + ', '.join(
        f'{["0", "1-39", "40-79", "80+"][b]}: {pct(v[1], v[0])} (n {v[0]})' for b, v in sorted(buckets.items())))


if __name__ == '__main__':
    if '--report' not in sys.argv:
        th = int(sys.argv[sys.argv.index('--threads') + 1]) if '--threads' in sys.argv else 12
        idx = json.loads((X.AN / 'index.json').read_text())['games']
        dirs = sorted({r['dir'] for r in idx if r['ok']})
        with ProcessPoolExecutor(th) as ex:
            list(ex.map(work, dirs))
    report()
