"""pzone2.py EXT [--maxr 300] [--show N]: at each enemy-Prism turn start with its stun cast ready, our champions within 4 whose health its two casts cover:
what each did on its turn since the Prism last moved (the Prism cannot walk and cast, so it stood there through that turn)."""
import sys, collections, statistics as st, json
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv')
from tracelib import *
ext = sys.argv[1]; maxr = int(sys.argv[sys.argv.index('--maxr') + 1]) if '--maxr' in sys.argv else 300
allhp = '--allhp' in sys.argv
rows = []; ngames = 0
for gm in games(ext):
    typ = gm.typ; team = gm.team; cand = gm.cand
    pr = [i for i in typ if typ[i] == 'Prism' and team[i] != cand]
    if not pr: continue
    pr = pr[0]; ngames += 1; P = gm.ch[pr]
    blocked = {tuple(t) for k in ('walls', 'holes', 'altars') for t in gm.map[k]} | {(c['x'], c['y']) for c in gm.map['camps']}
    W, H = gm.map['width'], gm.map['height']
    pos = {i: (gm.ch[i]['x'][0], gm.ch[i]['y'][0]) for i in typ}
    hpnow = {i: gm.ch[i]['hp'][0] for i in typ}
    last_cast = {0: -99, 1: -99}
    turn = {i: None for i in typ}  # the champion's latest turn: dict(r, start, end, hit, s)
    cur = {}
    ptprev = None  # Prism's previous turn end step
    deaths = collections.defaultdict(list)
    for e in gm.ev:
        if e['k'] == 'death': deaths[e['v']].append((e['r'], e.get('by')))
    seen_turn = set()
    for e in gm.ev:
        r = e['r']
        if r > maxr: break
        a = e.get('a'); k = e['k']
        if a in typ and e['t'] >= 0 and k in ('move', 'attack', 'cast', 'blocked', 'recall_start', 'recall_cancel', 'tribute_start', 'shop', 'ward', 'consumable'):
            if (a, r) not in seen_turn:
                seen_turn.add((a, r))
                if a == pr and pos[pr] is not None:
                    # the Prism's turn starts: evaluate the zone
                    i = r - 2
                    if i >= 0:
                        cc = r >= last_cast[0] + 8; aoe = r + 1 >= last_cast[1] + 8
                        F = P['foc'][i]
                        if cc:
                            for v in typ:
                                if team[v] != cand or pos[v] is None or not gm.ch[v]['alive'][i]: continue
                                d1 = cheb(pos[v], pos[pr])
                                if d1 > 4: continue
                                c = gm.ch[v]; hp = hpnow[v]
                                burst = 1.5 * F + (F if aoe else 0) + (70 if d1 <= 3 else 0)
                                if typ[v] == 'Marcella': burst = 1.5 * F + (35 if d1 <= 3 else 0)
                                if hp > burst and not allhp: continue
                                if cheb(pos[v], gm.spawn_c(cand)) <= 2: continue
                                t = turn[v]
                                acted = t is not None and ptprev is not None and t['s'] > ptprev
                                tr = t['r'] if acted else None
                                d0 = cheb(t['start'], pos[pr]) if acted and t['start'] else d1
                                # could a single step have reached distance 5? (terrain only)
                                st0 = t['start'] if acted and t['start'] else pos[v]
                                out = any(cheb((st0[0] + dx, st0[1] + dy), pos[pr]) >= 5 and 0 <= st0[0] + dx < W and 0 <= st0[1] + dy < H and (st0[0] + dx, st0[1] + dy) not in blocked
                                          for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy) if d0 >= 4 else False
                                if not acted:
                                    # no events since the Prism moved: idle, stunned, channelling or out of fuel; its turn round by turn code
                                    rr = r if c['turn'][r - 1] in (5, 6) and False else None
                                dec = gm.dec(v, tr) if tr else None
                                if dec is None:
                                    # find a D line in r or r-1 with a stunned/idle turn
                                    dec = 'stun' if (c['turn'][r - 1] == 5 or c['turn'][r - 2] == 5) else 'idle'
                                wh = gm.lines(v, tr, 'WH') if tr else []; stl = gm.lines(v, tr, 'ST') if tr else []
                                rows.append({'game': gm.g['source'].split('/')[-1], 'v': typ[v], 'vid': v, 'r': r, 'tr': tr, 'd0': d0, 'd1': d1, 'out': out, 'dec': dec, 'wh': wh[0][6] if wh else '-',
                                             'st': (stl[0][5], stl[0][6], stl[0][9], stl[0][10]) if stl else None, 'hp': hp / max(1, c['maxHp'][i]), 'F': F, 'ratio': hp / burst,
                                             'hitc': t['hitc'] if acted else False, 'hitcamp': t['hitcamp'] if acted else False, 'moved': t['moved'] if acted else False,
                                             'saw': pr in c['sees'][(tr or r) - 1], 'died': any(r <= dr <= r + 2 for dr, by in deaths[v]), 'diedp': any(r <= dr <= r + 2 and by == pr for dr, by in deaths[v]),
                                             'al': sum(1 for k2 in typ if team[k2] == cand and k2 != v and pos[k2] and cheb(pos[k2], pos[pr]) <= 5), 'pidx': len(rows), 'cast': False, 'win': gm.win})
                                cur.setdefault(r, []).append(len(rows) - 1)
                turn[a] = {'r': r, 'start': pos[a], 'end': pos[a], 's': e['s'], 'hitc': False, 'hitcamp': False, 'moved': False}
            t = turn[a]; t['s'] = e['s']
            if k == 'move': pos[a] = tuple(e['to']); t['moved'] = True
            elif k == 'cast':
                if e.get('moved'): pos[a] = tuple(e['moved']); t['moved'] = True
                if a == pr:
                    last_cast[e.get('slot', 0)] = r
                    if e.get('slot', 0) == 0:
                        for idx in cur.get(r, []):
                            if rows[idx]['vid'] == e.get('tgt'): rows[idx]['cast'] = True
            if k in ('attack', 'cast'):
                if any(x[0] in typ for x in (e.get('dmg') or [])): t['hitc'] = True
                if e.get('camp') is not None: t['hitcamp'] = True
            if a == pr: ptprev = e['s']
        if k in ('attack', 'cast', 'camp_attack'):
            for (x, dmg) in (e.get('dmg') or []) if isinstance(e.get('dmg'), list) else []:
                if x in hpnow: hpnow[x] -= dmg
            if k == 'camp_attack' and e.get('tgt') in hpnow and not isinstance(e.get('dmg'), list): hpnow[e['tgt']] -= e.get('dmg') or 0
        if k == 'recall_end': pos[a] = tuple(e['to'])
        elif k == 'respawn': pos[a] = tuple(e['at'])
        elif k == 'teleport_end': pos[a] = tuple(e['to'])
        elif k == 'death': pos[e['v']] = None
        # resync health at round boundaries
        if e['t'] == -1 and r >= 2:
            for i2 in typ: hpnow[i2] = gm.ch[i2]['hp'][r - 2] if gm.ch[i2]['alive'][r - 2] else 0
            for i2 in typ:
                if gm.ch[i2]['alive'][r - 2] and pos[i2] is None: pos[i2] = (gm.ch[i2]['x'][r - 2], gm.ch[i2]['y'][r - 2])
N = len(rows)
fr = lambda L, f: f"{sum(1 for x in L if f(x))} ({sum(1 for x in L if f(x)) / max(1, len(L)):.2f})"
print(ngames, 'games with an enemy Prism;', N, f'zone moments by r{maxr} ({N/ngames:.2f} a game)')
print(' the Prism cast its stun on that champion:', fr(rows, lambda x: x['cast']), '| died within 2 rounds', fr(rows, lambda x: x['died']), 'to the Prism', fr(rows, lambda x: x['diedp']))
print(' Prism focus median', st.median(x['F'] for x in rows), 'hp share', round(st.median(x['hp'] for x in rows), 2), 'saw Prism', fr(rows, lambda x: x['saw']), 'allies within 5 of Prism', round(st.mean(x['al'] for x in rows), 2))
print(' turn since the Prism moved: decision', collections.Counter(x['dec'] for x in rows).most_common(10))
print(' (d0 -> d1):', sorted(collections.Counter((min(x['d0'], 7), x['d1']) for x in rows).items()))
print(' a step out to 5+ existed (terrain only):', fr(rows, lambda x: x['out']))
for dec in ('R', 'F', 'C', 'A', 'P', 'B', 'K', 'stun', 'idle', '?'):
    s = [x for x in rows if x['dec'] == dec]
    if s: print(f"   {dec}: {len(s)} | step out existed {fr(s, lambda x: x['out'])} | walked in (d0>4) {fr(s, lambda x: x['d0'] > 4)} | hit a champion {fr(s, lambda x: x['hitc'])} a camp {fr(s, lambda x: x['hitcamp'])} | stunned-cast {fr(s, lambda x: x['cast'])} died {fr(s, lambda x: x['died'])} | hp {st.median(x['hp'] for x in s):.2f} | WH {collections.Counter(x['wh'] for x in s).most_common(4)} ST {collections.Counter(x['st'][:2] if x['st'] else None for x in s).most_common(3)}")
json.dump(rows, open('/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv/pzone2.json', 'w'))
