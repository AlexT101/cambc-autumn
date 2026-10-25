"""Cross-game episode lines: one line per episode, each starting with
`<map> <game> r<round> [<team>] <champion> (<side>,<W|L> vs [<opponent>])` so grep by team, champion or map works.

Facts only. Where a field is omniscient (positions the champion could not see), it says `(omniscient)`."""

from collections import defaultdict

from analysis.data import chebyshev

from .report import P, WARD_FIGHT_RADIUS, WARD_FIGHT_WINDOW, LURK_MIN, dist_str, pct
from .track import short_item

OPENING_END = 150
WARD_REVEAL_WINDOW = 40


def build(n):
    ep = defaultdict(list)
    fights(n, ep)
    deaths(n, ep)
    tributes(n, ep)
    recalls(n, ep)
    wards(n, ep)
    shops(n, ep)
    camps(n, ep)
    locks(n, ep)
    lurks(n, ep)
    openings(n, ep)
    return ep


def fights(n, ep):
    v = n.v
    for f in n.fights:
        for t in (0, 1):
            if not any(v.team[c] == t for c in f.part):
                continue
            ep['fights'].append(n.team_prefix(t, f.r0) + ' ' + n.fight_line(f, t))
        s, r, a, x, amt, ap, vp = f.first
        if f.blind:
            t = v.team[a]
            lurk = 'before: unseen by every enemy for 3 rounds, ' + (
                f'in bush {f.lurk_bush.name(t)}' if f.ambush_how == 'bush' else 'standing still') if f.ambush else                 'victim did not see the attacker at its last turn start'
            k_own = sum(1 for e in f.kills if v.team[e['by']] == t)
            k_opp = sum(1 for e in f.kills if v.team[e['by']] != t)
            bush = n.M.bush_of(ap) if ap else None
            camps_hit = sorted({n.M.group(n.M.camp_group[cp]).name(t) for rr in range(max(1, r - 3), r) for e in v.by_round[rr]
                                if e.get('a') == a and e['k'] in ('attack', 'cast') for cp, _ in e.get('cdmg', [])})
            if camps_hit:
                lurk += ' (hitting camp ' + ','.join(camps_hit) + ' meanwhile)'
            ep['ambush'].append(n.prefix(a, r) + f' {"AMBUSH" if f.ambush else "BLIND-HIT"} {f.id} on enemy {v.type[x]}'
                                f' from {n.M.where(ap, t)}{"" if bush else " (not a bush)"} at range {chebyshev(ap, vp) if ap and vp else "-"}; '
                                f'{lurk}; first dmg '
                                f'{"stun" if amt == 0 else f"{amt:.0f}"}; fight kills {k_own}-{k_opp}; victim hp {pct(n.hp(x, r - 1))} bag {n.bag(x, r - 1)}')


def deaths(n, ep):
    v, M, tr = n.v, n.M, n.tr
    fight_at = {}
    for f in n.fights:
        for e in f.kills + f.camp_deaths:
            fight_at[e['s'], e['v']] = f
    for r in range(1, v.N + 1):
        for e in v.deaths[r]:
            c = e['v']
            t = v.team[c]
            f = fight_at.get((e['s'], c))
            doing = _doing(n, c, r)
            if 'camp' in e:
                killer = f'camp {M.group(M.camp_group[e["camp"]]).name(t)}'
            elif e.get('linked') is not None:
                killer = f'partner {v.type[e["linked"]]} died'
            else:
                killer = f'enemy {v.type[e["by"]]}' + (f' (assists {",".join(v.type[a] for a in e["assists"])})' if e.get('assists') else '')
            seen = set()
            for rr in range(max(1, r - 3), r + 1):
                seen |= set(v.at(c, 'sees', rr))
            at = tuple(e['at'])
            allies = [o for o in v.ids if v.team[o] == t and o != c and v.pos_at(o, r, e['s']) and chebyshev(v.pos_at(o, r, e['s']), at) <= 4]
            enemies = [o for o in v.ids if v.team[o] != t and v.pos_at(o, r, e['s']) and chebyshev(v.pos_at(o, r, e['s']), at) <= 8]
            chan = [x for x in v.by_round[r] if x.get('a') == c and x['k'] in ('recall_cancel', 'tribute_cancel', 'teleport_cancel')
                    and x.get('cause') == 'death']
            real_rec = any(rc['c'] == c and rc['r1'] == r and not rc['done'] for rc in tr.recalls)
            ch = ''
            for x in chan:
                if x['k'] == 'recall_cancel' and not real_rec:
                    continue
                ch = ' while ' + x['k'].split('_')[0] + ' channelling'
            fs = ''
            if f:
                fs = f'; in {f.id} (r{f.r0}-{f.r1}, present {len(f.present[t])}v{len(f.present[1 - t])}, first hit by ' \
                     f'{"own" if f.first_team == t else "enemy"} team{", blind" if f.blind else ""})'
            ep['deaths'].append(n.prefix(c, r) + f' DIED at {M.where(at, t)} to {killer}; bag {e["gems"]} '
                                f'{"lost" if "camp" in e else "to killer"}; hp before the blow {e.get("hp", 0):.0f} ({pct(e.get("hp", 0) / max(1, v.at(c, "maxHp", r - 1)))}){ch}; was {doing}{fs}; '
                                f'saw in last 3 rounds: {",".join(v.type[x] for x in sorted(seen)) or "none"}; '
                                f'allies within 4: {len(allies)}, enemies within 8: {len(enemies)} (omniscient)')


def _doing(n, c, r):
    """What the champion's track says it was doing in round r (the last item that started by then)."""
    names = {'trib': 'tributing', 'recall': 'recalling', 'wait': 'idle', 'shop': 'shopping', 'tp': 'teleporting',
             'leg': 'walking', 'fight': 'fighting'}
    cur = None
    for it in n.tr.items[c]:
        if it.r0 > r:
            break
        if it.kind != 'dead' or it.r0 < r:
            cur = it
    if cur is None or cur.kind == 'dead':
        return '?'
    if cur.kind == 'camp':
        return f'at camp {n.M.group(cur.gid).name(n.v.team[c])}'
    return names.get(cur.kind, cur.kind)


def _gains(n, c):
    """Gem gains per champion: (round, amount, source)."""
    v, M = n.v, n.M
    out = []
    t = v.team[c]
    for r in range(1, v.N + 1):
        for e in v.by_round[r]:
            if e['k'] == 'capture':
                for x, gm, gd in e['shares']:
                    if x == c and gm:
                        out.append((r, gm, M.group(e['g']).name(t)))
            elif e['k'] == 'death' and e.get('by') == c and e.get('gemsTo'):
                out.append((r, e['gemsTo'], f'kill {v.type[e["v"]]}'))
    return out


def tributes(n, ep):
    v, M = n.v, n.M
    for c in v.ids:
        t = v.team[c]
        gains = _gains(n, c)
        last_bank = 0
        items = n.tr.items[c]
        for i, it in enumerate(items):
            if it.kind == 'dead':
                last_bank = it.r0
            if it.kind != 'trib' or not it.start:
                continue
            st = it.start
            r = st['r']
            alt = n.altar_name(st['altar'], t)
            src = [g for g in gains if last_bank < g[0] <= r]
            agg = defaultdict(int)
            for _, gm, s in src:
                agg[s] += gm
            leg = items[i - 1] if i and items[i - 1].kind == 'leg' else None
            choice = ''
            if leg and leg.a:
                best, bd = M.nearest(leg.a, M.altars)
                chosen = next(a for a in M.altars if a.anchor == tuple(st['altar']))
                cd = M.dist_to(chosen, leg.a)
                choice = f'; from leg start {M.place(leg.a, t)}: chosen altar d{dist_str(cd)}' + (
                    '' if best is chosen else f', nearest {best.name(t)} d{dist_str(bd)}')
            locks = v.g.rounds['locks'][min(r, v.N) - 1]
            lk = [L for L in locks if (L[1], L[2]) == tuple(st['altar'])]
            lock = ''
            if lk:
                lock = '; locks on altar: ' + ','.join(('own' if L[0] == t else 'enemy') + f'({L[3]} hits left)' for L in lk)
            near = [o for o in v.ids if v.team[o] != t and v.pos(o, r) and chebyshev(v.pos(o, r), tuple(st['altar'])) <= 8]
            if it.end:
                res = f'banked {it.end["gems"]} r{it.end["r"]} (team total {it.end["total"]})'
            elif it.cancel:
                res = f'CANCELLED r{it.cancel["r"]} by {it.cancel.get("cause")}'
            else:
                res = 'unfinished at game end'
            ep['tributes'].append(n.prefix(c, r) + f' TRIBUTE at {alt} bag {st["gems"]} channel {st["dur"]} -> {res}; '
                                  f'bag from: {", ".join(f"{s} {g}" for s, g in agg.items()) or "-"} since r{last_bank}; '
                                  f'hp {pct(n.hp(c, r - 1))}; enemies seen during channel: {",".join(v.type[e] for e in sorted(it.seen)) or "none"}; '
                                  f'enemies within 8 of altar: {len(near)} (omniscient){choice}{lock}')
            if it.end:
                last_bank = it.end['r']


def recalls(n, ep):
    v, M = n.v, n.M
    for rc in n.tr.recalls:
        c = rc['c']
        t = v.team[c]
        r = rc['r0']
        seen = set()
        for rr in range(max(1, r - 3), r + 1):
            seen |= set(v.at(c, 'sees', rr))
        after = ''
        if rc['done']:
            pts = [e for rr in range(rc['r1'], min(v.N, rc['r1'] + 3) + 1) for e in v.by_round[rr]
                   if e.get('a') == c and e['k'] in ('shop', 'sell')]
            after = '; then shop ' + n.shop_text(pts) if pts else '; no purchase within 3 rounds'
        dmg = [x for x in v.by_round[rc['r1']] if x.get('a') == c and x['k'] == 'recall_cancel']
        res = 'home r%d' % rc['r1'] if rc['done'] else f'INTERRUPTED r{rc["r1"]} by {rc.get("cause")}'
        ep['recalls'].append(n.prefix(c, r) + f' RECALL from {M.where(rc["from"], t)} (walk home {dist_str(M.dspawn[t].get(rc["from"]))}) '
                             f'bag {rc["gems"]} hp {pct(n.hp(c, r - 1))} gold {v.at(c, "gold", r - 1)} -> {res}; '
                             f'enemies seen in last 3 rounds: {",".join(v.type[e] for e in sorted(seen)) or "none"}{after}')
    for c, k in n.tr.feints.items():
        if k >= 20:
            ep['habits'].append(n.prefix(c, 1) + f' HABIT recall started and cancelled at the next turn {k} times (never reported as recalls)')


def wards(n, ep):
    v, M = n.v, n.M
    for c in v.ids:
        t = v.team[c]
        wl = [e for r in range(1, v.N + 1) for e in v.by_round[r] if e['k'] == 'ward' and e.get('a') == c]
        for i, e in enumerate(wl):
            r = e['r']
            w = tuple(e['to'])
            end = wl[i + 1]['r'] if i + 1 < len(wl) else v.N
            me = v.pos_at(c, r, e['s']) or v.start_pos(c, r)
            fov = M.vision.fov(w, 6)
            b = M.bush_of(w)
            alt, da = M.nearest(w, M.altars)
            cmp, dc = M.nearest(w, M.groups)
            cover_alt = [a.name(t) for a in M.altars if a.anchor in fov or any((a.anchor[0] + dx, a.anchor[1] + dy) in fov
                                                                                  for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
            cover_camp = [g.name(t) for g in M.groups if any(x in fov for x in g.tiles)]
            half = {t: 'own half', 1 - t: 'enemy half', -1: 'middle'}[M.half_of(w)]
            # Ward-only sightings: enemies the placer saw at its turn starts while they stood in the ward's view but
            # outside its own.
            reveal = {}
            for rr in range(r + 1, min(end, r + WARD_REVEAL_WINDOW) + 1):
                sees = v.at(c, 'sees', rr)
                if not sees:
                    continue
                ts = v.turn_step(c, rr)
                mp = v.start_pos(c, rr)
                own = M.vision.fov(mp) if mp else frozenset()
                for x in sees:
                    px = v.pos_at(x, rr, ts)
                    if px and px in fov and px not in own:
                        reveal.setdefault(x, rr)
            near_f = [f for f in n.fights if r <= f.r0 <= r + WARD_FIGHT_WINDOW and f.loc and chebyshev(f.loc, w) <= WARD_FIGHT_RADIUS]
            fs = '; fights within 8 in next 20 rounds: ' + (', '.join(f'{f.id} r{f.r0} (kills {sum(1 for k in f.kills if v.team[k["by"]] == t)}-{sum(1 for k in f.kills if v.team[k["by"]] != t)})' for f in near_f) or 'none')
            ep['wards'].append(n.prefix(c, r) + f' WARD at {M.where(w, t)}{"" if b else " on open ground"}, {half}, '
                               f'placed from {P(me)} (dist {chebyshev(me, w) if me else "-"}); nearest altar {alt.name(t)} d{dist_str(da)}, '
                               f'nearest camp {cmp.name(t)} d{dist_str(dc)}; view covers altars [{",".join(cover_alt)}] camps [{",".join(cover_camp)}] '
                               f'({len(fov)} tiles); lasted {end - r} rounds; ward-only sightings: '
                               f'{", ".join(f"{v.type[x]} r{rr}" for x, rr in sorted(reveal.items(), key=lambda z: z[1])) or "none"}{fs}')


def shops(n, ep):
    v = n.v
    for c in v.ids:
        for it in n.tr.items[c]:
            pts = [e for e in it.points if e['k'] in ('shop', 'sell')]
            if not pts:
                continue
            r = pts[0]['r']
            sp = n.M.spawn_set[v.team[c]]
            where = 'while dead' if not v.at(c, 'alive', r) or it.kind == 'dead' else                 'on spawn' if v.pos(c, r) in sp or v.start_pos(c, r) in sp else 'in the field'
            ep['shop'].append(n.prefix(c, pts[0]['r']) + f' SHOP {where}: {n.shop_text(pts)}; gold left {v.at(c, "gold", pts[-1]["r"])}; '
                              f'items now {_items(v, c, pts[-1]["r"])}')


def _items(v, c, r):
    flat = v.at(c, 'items', r)
    names = v.item_names
    return ','.join(f'{short_item(names[flat[i]])}x{flat[i + 1]}' if flat[i + 1] > 1 else short_item(names[flat[i]])
                    for i in range(0, len(flat), 2)) or '-'


def camps(n, ep):
    v, M = n.v, n.M
    life_dmg = defaultdict(lambda: [0.0, 0.0])
    last_hit = {}
    contested = defaultdict(int)
    for r in range(1, v.N + 1):
        for e in v.by_round[r]:
            k = e['k']
            if k == 'group_respawn':
                life_dmg.pop(e['g'], None)
                contested.pop(e['g'], None)
            elif k in ('attack', 'cast') and e.get('cdmg'):
                for camp, amt in e['cdmg']:
                    life_dmg[M.camp_group[camp]][v.team[e['a']]] += amt
            elif k == 'group_clear':
                last_hit[e['g']] = e.get('by')
            elif k == 'capture_reset' and e.get('contested'):
                contested[e['g']] += 1
            elif k == 'capture':
                g = M.group(e['g'])
                t = e['team']
                d = life_dmg.get(e['g'], [0.0, 0.0])
                tot = d[0] + d[1]
                share = d[t] / tot if tot else 0
                tags = []
                if g.half == 1 - t:
                    tags.append('STEAL (enemy half)')
                if tot and share < 0.5:
                    tags.append('DENIAL (enemy did most damage)')
                if contested.get(e['g']):
                    tags.append(f'contested x{contested[e["g"]]}')
                lh = last_hit.get(e['g'])
                c = e['shares'][0][0] if e['shares'] else None
                who = ','.join(f'{v.type[x]} {gm}g/{gd:.0f}$' for x, gm, gd in e['shares'])
                line = (n.team_prefix(t, r) + f' CAPTURE {g.name(t)} ({g.info}) by {who}; own team dealt {share:.0%} of its damage'
                        f'{"; last hit " + v.ally_enemy(lh, t) if lh in v.team else ""}' + (' [' + ', '.join(tags) + ']' if tags else ''))
                ep['camps'].append(line)
                life_dmg.pop(e['g'], None)
                contested.pop(e['g'], None)


def locks(n, ep):
    v, M = n.v, n.M
    for r in range(1, v.N + 1):
        for e in v.by_round[r]:
            if e['k'] == 'lock_place':
                c = e['a']
                t = v.team[c]
                cancels = [x for x in v.by_round[r] if x['k'] == 'tribute_cancel' and x.get('cause') == 'lock' and x['s'] == e['s']]
                dest = next((x['r'] for rr in range(r, v.N + 1) for x in v.by_round[rr]
                             if x['k'] == 'lock_destroyed' and x['team'] == t and tuple(x['at']) == tuple(e['to'])), None)
                ep['locks'].append(n.prefix(c, r) + f' LOCK on {n.altar_name(e["to"], t)}; cancelled tributes: '
                                   f'{",".join(v.ally_enemy(x["a"], t) for x in cancels) or "none"}; '
                                   f'{"destroyed r%d" % dest if dest else "never destroyed"}')
            elif e['k'] == 'tribute_blocked':
                c = e['a']
                ep['locks'].append(n.prefix(c, r) + f' TRIBUTE BLOCKED by enemy lock at {n.altar_name(e["altar"], v.team[c])} (bag {e["gems"]})')


def lurks(n, ep):
    """>= LURK_MIN consecutive rounds in one bush cluster, seen by no enemy at their turn starts."""
    v, M = n.v, n.M
    for c in v.ids:
        t = v.team[c]
        r = 1
        while r <= v.N:
            p = v.pos(c, r)
            b = M.bush_of(p) if p else None
            if b is None or v.at(c, 'seenBy', r) or p in M.spawn_set[t]:
                r += 1
                continue
            j = r
            while j + 1 <= v.N and v.pos(c, j + 1) and M.bush_of(v.pos(c, j + 1)) is b and not v.at(c, 'seenBy', j + 1):
                j += 1
            still = sum(1 for rr in range(r + 1, j + 1) if v.pos(c, rr) == v.pos(c, rr - 1))
            busy = any(e.get('a') == c and e['k'] in ('attack', 'cast') for rr in range(r, j + 1) for e in v.by_round[rr])
            if j - r + 1 >= LURK_MIN and still >= LURK_MIN - 1 and not busy:
                passed = set()
                for rr in range(r, j + 1):
                    for o in v.ids:
                        if v.team[o] != t and v.pos(o, rr) and chebyshev(v.pos(o, rr), v.pos(c, rr)) <= 4:
                            passed.add(o)
                hit = None
                for f in n.fights:
                    if r <= f.r0 <= j + 3:
                        fh = f.first
                        if fh[2] == c:
                            hit = f
                            break
                out = f'first hit {hit.id} on enemy {v.type[hit.first[3]]} r{hit.first[1]}{" (ambush)" if hit.ambush else ""}' if hit else \
                    next((f'joined {f.id}' for f in n.fights if c in f.part and r <= f.r0 <= j + 3), 'no fight')
                camp = next((it for it in n.tr.items[c] if it.kind == 'camp' and r <= it.r0 <= j + 3), None)
                if camp and not hit:
                    out += f', then camp {M.group(camp.gid).name(t)} r{camp.r0}'
                ep['lurks'].append(n.prefix(c, r) + f' LURK in bush {b.name(t)} at {M.place(v.pos(c, r), t)} r{r}-{j} ({j - r + 1} rounds, '
                                   f'{still} without moving), unseen by enemies; enemies within 4 meanwhile: '
                                   f'{",".join(v.type[o] for o in sorted(passed)) or "none"} (omniscient); outcome: {out}')
            r = j + 1


def openings(n, ep):
    v, M = n.v, n.M
    for c in v.ids:
        t = v.team[c]
        seq = []
        for it in n.tr.items[c]:
            if it.r0 > OPENING_END:
                break
            k = it.kind
            if k == 'camp':
                g = M.group(it.gid)
                cap = it.capture and it.capture[1] == t and any(x == c for x, *_ in it.capture[2])
                seq.append(f'{g.name(t)}({"cap" if cap else "clr" if it.cleared else "hit"} r{it.r1})')
            elif k == 'trib' and it.start:
                seq.append(f'TRIB {n.altar_name(it.start["altar"], t)} {it.start["gems"]}g r{it.r0}')
            elif k == 'fight':
                seq.append(f'{it.fight.id} r{it.r0}')
            elif k == 'dead':
                seq.append(f'DIED r{it.r0}')
            elif k == 'recall':
                seq.append(f'RECALL r{it.r0}')
            elif k == 'wait' and it.r1 - it.r0 >= 4:
                seq.append(f'idle {M.place(it.at, t)} {it.r1 - it.r0 + 1}r')
            elif k == 'shop':
                seq.append('shop')
            for e in it.points:
                if e['k'] == 'ward':
                    seq.append(f'ward {M.place(e["to"], t)}')
        ep['openings'].append(n.prefix(c, 1) + ' OPENING r1-150: ' + ' > '.join(seq))
