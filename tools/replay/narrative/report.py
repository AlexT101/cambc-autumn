"""Renders one game: the timeline, the fight transcripts and the cross-game episode lines."""

from collections import Counter

from analysis.data import chebyshev

from .combat import engagements
from .game import View
from .track import Track, short_item

VERSION = 1
WARD_FIGHT_WINDOW = 20   # rounds after a ward placement in which a nearby fight is reported
WARD_FIGHT_RADIUS = 8
LURK_MIN = 3
TURN_MIN = 4             # steps away from a leg's end that count as turning back
STATE_EVERY = 100
INF = 1 << 30


def P(p):
    return f'({p[0]},{p[1]})' if p else '-'


def pct(x):
    return f'{x:.0%}'


def dist_str(d):
    return '-' if d is None or d >= INF else str(d)


class Narrator:
    def __init__(self, d, mapinfo, teams, label):
        self.v = v = View(d, mapinfo, teams)
        self.M = mapinfo
        self.label = label
        self.fights = engagements(v)
        self.tr = Track(v, self.fights)
        self.fight_by_id = {f.id: f for f in self.fights}
        w = v.meta['result']['winner']
        self.result = {t: ('W' if t == w else 'L') for t in (0, 1)}
        self.map_name = v.meta['map']['name']

    # ---- shared bits

    def hp(self, c, r):
        """Health fraction at the end of round r (round 0: the start, full health)."""
        v = self.v
        if r <= 0:
            return 1.0
        return v.at(c, 'hp', r) / max(1, v.at(c, 'maxHp', r))

    def bag(self, c, r):
        return self.v.at(c, 'gems', r) if r > 0 else 0

    def prefix(self, c, r):
        """Cross-game episode prefix: map, game, round, team, champion, result, opponent."""
        v = self.v
        t = v.team[c]
        return (f'{self.map_name} {self.label} r{r} [{v.team_name[t]}] {v.type[c]} '
                f'({"AB"[t]},{self.result[t]} vs [{v.team_name[1 - t]}])')

    def team_prefix(self, t, r):
        v = self.v
        return f'{self.map_name} {self.label} r{r} [{v.team_name[t]}] ({"AB"[t]},{self.result[t]} vs [{v.team_name[1 - t]}])'

    def names(self, ids, team):
        return ','.join(self.v.ally_enemy(c, team) for c in sorted(ids)) or '-'

    def seen_by(self, c, r0, r1):
        """Enemy types that saw c at their turn starts in rounds r0..r1, with first round."""
        v = self.v
        first = {}
        for r in range(max(1, r0), min(v.N, r1) + 1):
            for e in v.at(c, 'seenBy', r):
                first.setdefault(e, r)
        return first

    def companions(self, c, r0, r1, d=3):
        v = self.v
        n = r1 - r0 + 1
        out = []
        for o in v.ids:
            if o == c or v.team[o] != v.team[c]:
                continue
            k = sum(1 for r in range(r0, r1 + 1) if v.pos(c, r) and v.pos(o, r) and chebyshev(v.pos(c, r), v.pos(o, r)) <= d)
            if k * 2 >= n:
                out.append(v.type[o])
        return out

    # ---- timeline items

    def leg_text(self, it, nxt_place):
        v, M = self.v, self.M
        c, t = it.c, self.v.team[it.c]
        if it.steps == 0:
            return ''
        frm = M.place(it.a, t)
        if it.d == 0:
            shape = 'loop back to its start tile'
        elif it.mono >= 0.9 and it.d is not None and it.steps <= 1.15 * it.d + 1:
            shape = 'direct'
        else:
            shape = f'indirect: {pct(it.mono)} of steps closer'
        s = f'walk r{it.r0}-{it.r1} {frm} -> {nxt_place} ({it.steps} steps{f", {it.dashes} dashes" if it.dashes else ""}' \
            f', walk dist {dist_str(it.d)}, {shape})'
        for tb in self.turnbacks(it):
            s += ' ' + tb
        comp = self.companions(c, it.r0, it.r1)
        if comp:
            s += ' with ' + ','.join(comp)
        sb = self.seen_by(c, it.r0, it.r1)
        if sb:
            s += ' seen by ' + ','.join(f'{v.type[e]}@r{r}' for e, r in sorted(sb.items(), key=lambda x: x[1]))
        enemies_half = [p for p in it.path[1:] if p and M.half_of(p) == 1 - t]
        if enemies_half and M.half_of(it.b or it.a) != 1 - t:
            s += f' via enemy half ({len(enemies_half)} rounds)'
        bushes = []
        for p in it.path[1:]:
            b = M.bush_of(p) if p else None
            if b is not None and (not bushes or bushes[-1] != b.name(t)):
                bushes.append(b.name(t))
        if bushes:
            s += ' through bush ' + ','.join(bushes[:4])
        return s

    def turnbacks(self, it):
        """Stretches of >= TURN_MIN steps that took the walker farther from the leg's end, with the landmark it got
        closest to on every step of the stretch (if any) and what it saw or lost around the turn."""
        v, M = self.v, self.M
        c, t = it.c, v.team[it.c]
        if not it.b or it.steps < 2 * TURN_MIN:
            return []
        fd = it.fd
        path = it.path
        rounds = list(range(it.r0 - 1, it.r1 + 1))
        out = []
        i = 1
        while i < len(path):
            j = i
            while j < len(path) and path[j] and path[j - 1] and fd.get(path[j], INF) > fd.get(path[j - 1], INF):
                j += 1
            if j - i >= TURN_MIN:
                a, b = path[i - 1], path[j - 1]
                best = None
                for f in M.landmarks:
                    ds = [M.dist_to(f, p) for p in path[i - 1:j]]
                    if all(ds[k + 1] < ds[k] for k in range(len(ds) - 1)) and ds[-1] > 0:
                        if best is None or ds[0] - ds[-1] > best[1][0] - best[1][-1]:
                            best = (f, ds)
                tr = rounds[j - 1]
                s = f'[turned back r{tr} at {P(b)} after {j - i} steps away from the destination'
                if best:
                    s += f', approaching {best[0].name(t)} d{best[1][0]}->d{best[1][-1]}'
                saw = sorted({e for r in range(tr - 1, tr + 2) for e in v.at(c, 'sees', r)})
                if saw:
                    s += ', saw ' + ','.join(v.type[e] for e in saw) + f' r{tr - 1}-{tr + 1}'
                lost = [e for r in range(tr - 3, tr + 2) for e in v.deaths.get(r, []) if v.team.get(e['v']) == t and e['v'] != c]
                if lost:
                    s += ', ally died ' + ','.join(f'{v.type[e["v"]]} r{e["r"]}' for e in lost)
                out.append(s + ']')
            i = max(j, i + 1)
        return out

    def anchor_text(self, it):
        v, M = self.v, self.M
        c, t = it.c, v.team[it.c]
        k = it.kind
        if k == 'camp':
            g = M.group(it.gid)
            s = f'CAMP {g.name(t)} r{it.r0}-{it.r1}'
            bits = []
            if it.woke and it.woke[1] == c:
                bits.append(f'woke it r{it.woke[0]}')
            if it.dealt:
                bits.append(f'dealt {it.dealt:.0f}' + (f' ({it.dealt / g.hp:.0%} of {g.hp:.0f} hp)' if g.hp else ''))
            if it.allies:
                bits.append('with ' + ','.join(v.type[a] for a in sorted(it.allies)))
            if it.taken:
                bits.append(f'took {it.taken:.0f} camp dmg')
            if it.cleared:
                by = it.cleared[1]
                bits.append(f'cleared r{it.cleared[0]}' + (f' (last hit {v.ally_enemy(by, t) if by != c else "self"})' if by in v.team else ''))
            if it.reset:
                r, left, cont, team = it.reset
                bits.append(f'capture reset r{r}' + (' contested' if cont else '') + f' ({left} rounds left)')
            if it.held:
                bits.append(f'stood on its tiles {len(it.held)} rounds')
            if it.capture:
                r, team, shares = it.capture
                if team == t and any(x == c for x, *_ in shares):
                    sh = ', '.join(f'{"self" if x == c else v.type[x]} {gm}g/{gd:.0f}$' for x, gm, gd in shares)
                    bits.append(f'captured r{r} ({sh})')
                elif team == t:
                    bits.append(f'ally {",".join(v.type[x] for x, *_ in shares)} captured r{r}')
                else:
                    bits.append(f'enemy {",".join(v.type[x] for x, *_ in shares)} captured r{r}')
            elif it.cleared and not it.capture:
                bits.append('left before capture')
            elif not it.cleared:
                gs = self.tr.group_at(it.gid, it.r1)
                if gs and gs.get('hp'):
                    bits.append(f'left with {gs["hp"]:.0f} hp standing')
            return s + ': ' + '; '.join(bits)
        if k == 'fight':
            f = it.fight
            dealt = sum(x[4] for x in f.its if x[2] == c and it.r0 <= x[1] <= it.r1)
            took = sum(x[4] for x in f.its if x[3] == c and it.r0 <= x[1] <= it.r1)
            bits = [f'dealt {dealt:.0f}', f'took {took:.0f}']
            ks = [e for e in f.kills if e.get('by') == c and it.r0 <= e['r'] <= it.r1]
            if ks:
                bits.append('killed ' + ','.join(f'{v.type[e["v"]]} r{e["r"]} (+{e.get("gemsTo", 0)}g)' for e in ks))
            if it.r1 >= max(x[1] for x in f.its if c in (x[2], x[3])):
                bits.append(f.exit.get(c, ''))
            return f'FIGHT {f.id} r{it.r0}-{it.r1}: ' + '; '.join(b for b in bits if b)
        if k == 'trib':
            st = it.start
            if not st:
                return f'TRIBUTE channel r{it.r0}-{it.r1}'
            alt = self.altar_name(st['altar'], t)
            s = f'TRIBUTE {alt} r{it.r0}-{it.r1} bag {st["gems"]}'
            if it.end:
                s += f' banked {it.end["gems"]} (team total {it.end["total"]})'
            elif it.cancel:
                s += f' CANCELLED r{it.cancel["r"]} ({it.cancel.get("cause")})'
            if it.seen:
                s += '; saw ' + ','.join(v.type[e] for e in sorted(it.seen))
            if it.hit:
                s += f'; took {it.hit:.0f} champion damage while channelling'
            return s
        if k == 'recall':
            rc = it.rc
            s = f'RECALL r{rc["r0"]}-{rc["r1"]} from {M.place(rc["from"], t)} bag {rc["gems"]} hp {pct(self.hp(c, rc["r0"] - 1))}'
            return s + (' -> home' if rc['done'] else f' interrupted ({rc.get("cause")})')
        if k == 'shop':
            return 'SHOP ' + self.shop_text(it.points)
        if k == 'dead':
            return self.death_text(it)
        if k == 'wait':
            p = it.at
            n = it.r1 - it.r0 + 1
            if p in M.spawn_set[t]:
                return f'IDLE {n} rounds r{it.r0}-{it.r1} at spawn.own'
            alt, da = M.nearest(p, M.altars)
            cmp, dc = M.nearest(p, M.groups)
            b = M.bush_of(p)
            s = f'IDLE {n} rounds r{it.r0}-{it.r1} at {M.where(p, t)} (no event; nearest altar {alt.name(t)} d{dist_str(da)}, camp {cmp.name(t)} d{dist_str(dc)}'
            s += f', in bush {b.name(t)})' if b else ')'
            sb = self.seen_by(c, it.r0, it.r1)
            s += '; unseen by enemies' if not sb else '; seen by ' + ','.join(v.type[e] for e in sb)
            return s
        if k == 'tp':
            ev = [e for r in range(it.r0, it.r1 + 1) for e in v.by_round[r] if e.get('a') == c and e['k'].startswith('teleport')]
            st = next((e for e in ev if e['k'] == 'teleport_start'), None)
            return f'TELEPORT r{it.r0}-{it.r1}' + (f' to {M.where(st["to"], t)}' if st else '')
        return k.upper()

    def altar_name(self, p, t):
        p = tuple(p)
        for a in self.M.altars:
            if a.anchor == p:
                return a.name(t)
        return str(p)

    def shop_text(self, points):
        items = Counter()
        gold = 0
        for e in points:
            if e['k'] in ('shop', 'sell'):
                gold += e.get('gold', 0)
                for n, d in (e.get('items') or {}).items():
                    items[short_item(n)] += d
                for n, d in (e.get('cons') or {}).items():
                    items[n] += d
        parts = [f'{n} x{d}' if d != 1 else n for n, d in items.items() if d > 0]
        return (', '.join(parts) or '(nothing)') + f' ({gold:+.0f} gold)'

    def death_text(self, it):
        v, M = self.v, self.M
        c, t = it.c, v.team[it.c]
        de = None
        for r in (it.r0 - 1, it.r0, it.r0 + 1):
            for e in v.deaths.get(r, []):
                if e['v'] == c:
                    de = e
        resp = next((r for r in range(it.r1, min(v.N, it.r1 + 2) + 1) if (r, c) in v.arrive and v.at(c, 'alive', r)), None)
        s = ''
        if de:
            if 'camp' in de:
                g = M.group(M.camp_group[de['camp']])
                s = f'DIED r{de["r"]} to camp {g.name(t)} at {M.place(de["at"], t)}, bag {de["gems"]} lost'
            elif de.get('linked') is not None:
                s = f'DIED r{de["r"]} (partner {v.type[de["linked"]]} died) at {M.place(de["at"], t)}, bag {de["gems"]} to killer'
            else:
                s = f'DIED r{de["r"]} killed by {v.ally_enemy(de["by"], t)} at {M.place(de["at"], t)}, bag {de["gems"]} to killer'
                if de.get('assists'):
                    s += ' (assists ' + ','.join(v.type[a] for a in de['assists']) + ')'
        else:
            s = f'DEAD r{it.r0}-{it.r1}'
        if it.points:
            s += '; bought while dead: ' + self.shop_text(it.points)
        if resp:
            s += f'; respawned r{resp}'
        return s

    def point_text(self, e, t):
        M = self.M
        k = e['k']
        if k == 'ward':
            return f'WARD at {M.where(e["to"], t)}'
        if k == 'lock_place':
            return f'LOCK on {self.altar_name(e["to"], t)}'
        if k == 'blocked':
            return f'bumped unseen unit at {P(e["to"])}'
        if k == 'tribute_blocked':
            return f'tribute blocked by enemy lock at {self.altar_name(e["altar"], t)}'
        if k == 'consumable':
            return 'used ' + ','.join(e.get('cons', {})) + (f' to {P(e["to"])}' if e.get('to') else '')
        return ''

    def points_text(self, points, t):
        out = Counter()
        order = []
        for e in points:
            if e['k'] in ('shop', 'sell'):
                continue
            s = self.point_text(e, t)
            if s:
                if s not in out:
                    order.append(s)
                out[s] += 1
        return [s + (f' x{out[s]}' if out[s] > 1 else '') for s in order]

    def timeline(self):
        v, M = self.v, self.M
        out = []
        for c in v.ids:
            t = v.team[c]
            items = self.tr.items[c]
            i = 0
            while i < len(items):
                it = items[i]
                pts = self.points_text(it.points, t)
                if it.kind == 'leg':
                    nxt = items[i + 1] if i + 1 < len(items) and items[i + 1].kind != 'leg' else None
                    if nxt is not None:
                        place = self.anchor_place(nxt)
                        lt = self.leg_text(it, place)
                        at = self.anchor_text(nxt)
                        pts += self.points_text(nxt.points, t)
                        out.append((it.r0 if lt else nxt.r0, c, (lt + ' -> ' if lt else '') + at + (' | ' + '; '.join(pts) if pts else '')))
                        i += 2
                        continue
                    lt = self.leg_text(it, M.place(it.b, t))
                    if lt or pts:
                        out.append((it.r0, c, (lt or f'r{it.r0}-{it.r1} at {M.place(it.b, t)}') + (' -> ' + '; '.join(pts) if pts else '')))
                    i += 1
                    continue
                out.append((it.r0, c, self.anchor_text(it) + (' | ' + '; '.join(pts) if pts else '')))
                i += 1
        lines = []
        for r, c, s in out:
            lines.append((r, 1, f'r{r:<4} {v.tn(c)}: {s}'))
        for f in self.fights:
            lines.append((f.r0, 0, 'r%-4d ' % f.r0 + self.fight_line(f, f.first_team, short=True)))
        for r in range(STATE_EVERY, v.N + 1, STATE_EVERY):
            lines.append((r, -1, self.state_line(r)))
        lines.sort(key=lambda x: (x[0], x[1]))
        return [s for _, _, s in lines]

    def anchor_place(self, it):
        v, M = self.v, self.M
        t = v.team[it.c]
        if it.kind == 'camp':
            return M.group(it.gid).name(t)
        if it.kind == 'trib' and it.start:
            return self.altar_name(it.start['altar'], t)
        if it.kind == 'fight':
            return f'fight {it.fight.id} at {M.place(v.pos(it.c, it.r0 - 1), t)}'
        return M.place(v.pos(it.c, it.r0 - 1) or v.pos(it.c, it.r0), t)

    def state_line(self, r):
        v = self.v
        parts = []
        for t in (0, 1):
            ids = [c for c in v.ids if v.team[c] == t]
            score = v.g.rounds['gems'][t][r - 1]
            carried = sum(v.at(c, 'gems', r) for c in ids)
            gold = sum(v.at(c, 'gold', r) for c in ids)
            parts.append(f'[{v.team_name[t]}] tributed {score} carried {carried} gold {gold} formation {self.formation(t, r)}')
        return f'r{r:<4} STATE ' + ' | '.join(parts)

    def formation(self, t, r):
        """Groups of living champions linked by Chebyshev distance <= 4, e.g. `2+1+1` (dead: d)."""
        v = self.v
        ids = [c for c in v.ids if v.team[c] == t]
        alive = [c for c in ids if v.pos(c, r)]
        par = {c: c for c in alive}

        def find(x):
            while par[x] != x:
                x = par[x]
            return x
        for i, a in enumerate(alive):
            for b in alive[i + 1:]:
                if chebyshev(v.pos(a, r), v.pos(b, r)) <= 4:
                    par[find(a)] = find(b)
        sizes = sorted(Counter(find(c) for c in alive).values(), reverse=True)
        return '+'.join(map(str, sizes)) + ('+' + 'd' * (len(ids) - len(alive)) if len(alive) < len(ids) else '') if sizes else 'all dead'

    # ---- fights

    def fight_line(self, f, team, short=False):
        v, M = self.v, self.M
        t = team
        s0, r0, a, x, amt, ap, vp = f.first
        side = lambda tt: [c for c in sorted(f.part) if v.team[c] == tt]
        head = (f'FIGHT {f.id} r{f.r0}-{f.r1} at {M.place(f.loc, t)}: [{v.team_name[t]}] {",".join(v.type[c] for c in side(t))} '
                f'vs [{v.team_name[1 - t]}] {",".join(v.type[c] for c in side(1 - t))}')
        pres = f'present {len(f.present[t])}v{len(f.present[1 - t])}'
        fh = f'first hit {v.ally_enemy(a, t)} -> {v.ally_enemy(x, t)}' + (' (stun)' if amt == 0 else f' {amt:.0f}') + f' r{r0}'
        if f.answered:
            fh += ', answered same round'
        if f.closing:
            cr, cc, ce = f.closing
            fh += f'; closed in: {v.ally_enemy(cc, t)} stepped within 4 of {v.ally_enemy(ce, t)} r{cr}'
        tags = []
        if f.blind:
            tags.append('blind')
        if f.ambush:
            tags.append(f'ambush({f.ambush_how})')
        if f.from_bush is not None:
            tags.append(f'hit from bush {f.from_bush.name(t)}')
        kills = [f'{v.ally_enemy(e["by"], t)} killed {v.ally_enemy(e["v"], t)} r{e["r"]} (bag {e["gems"]})' for e in f.kills]
        kills += [f'camp killed {v.ally_enemy(e["v"], t)} r{e["r"]} (bag {e["gems"]})' for e in f.camp_deaths]
        k_own = sum(1 for e in f.kills if v.team[e['by']] == t)
        k_opp = sum(1 for e in f.kills if v.team[e['by']] != t)
        res = f'kills {k_own}-{k_opp}'
        out = [head, pres, fh + (' [' + ' '.join(tags) + ']' if tags else ''), res]
        if kills:
            out.append('; '.join(kills))
        if not short:
            ex = [f'{v.ally_enemy(c, t)} {f.exit[c]}' for c in sorted(f.part)]
            out.append('exits: ' + ', '.join(ex))
        return ' | '.join(out)

    def transcript(self, f):
        v, M = self.v, self.M
        t0 = f.first_team
        L = [self.fight_line(f, t0), self.fight_sides(f), f'  hit list: ' + '; '.join(
            f'r{r} {v.ally_enemy(a, t0)}->{v.ally_enemy(x, t0)} {"stun" if amt == 0 else f"{amt:.0f}"}' for s, r, a, x, amt, *_ in f.its[:40])
            + (' ...' if len(f.its) > 40 else '')]
        lo, hi = max(1, f.r0 - 2), min(v.N, f.r1 + 2)
        for r in range(lo, hi + 1):
            ch = Counter()
            for e in v.by_round[r]:
                if e['k'] == 'camp_attack':
                    for x, d in [(e.get('tgt'), e.get('dmg', 0))] + [tuple(x) for x in e.get('xdmg', [])]:
                        if x in f.part:
                            ch[(e['g'], x)] += d
            for (gid, x), d in ch.items():
                L.append(f'  r{r} camp {M.group(gid).name(v.team[x])} hits {v.tn(x)} {d:.0f}')
            for c in v.slots(r)['_seq']:
                if c not in f.part:
                    continue
                p0, p1 = v.start_pos(c, r), v.pos(c, r)
                acts = self.turn_actions(c, r)
                died = any(e['v'] == c for e in v.deaths[r])
                if p0 is None and not acts:
                    continue
                st = v.at(c, 'turn', r)
                mv = f'{P(p0)}->{P(p1)}' if p0 != p1 and p1 else P(p0)
                if st == 5:
                    acts.insert(0, 'STUNNED')
                if st == 6:
                    acts.append('ran out of fuel')
                hp = f'hp {self.hp(c, r):.0%}' if v.at(c, 'alive', r) else 'DEAD'
                sees = ','.join(v.type[e] for e in v.at(c, 'sees', r)) or 'none'
                tags = f.tags.get((r, c), [])
                bush = M.bush_of(p1 or p0) if (p1 or p0) else None
                L.append(f'  r{r} t{v.slots(r)[c]} {v.tn(c)} {mv}{" bush" if bush else ""}: {"; ".join(acts) or "-"} | {hp} bag {v.at(c, "gems", r)}'
                         f' | sees {sees}' + (f' | {" ".join(tags)}' if tags else '') + (' | died' if died and v.at(c, 'alive', r) == 0 else ''))
        return L

    def fight_sides(self, f):
        v = self.v
        parts = []
        for t in (0, 1):
            ids = sorted(c for c in f.part if v.team[c] == t)
            st = [f'{v.type[c]} hp {self.hp(c, f.r0 - 1):.0%} bag {self.bag(c, f.r0 - 1)} dealt {f.dealt.get(c, 0):.0f} '
                  f'took {f.taken.get(c, 0):.0f}' for c in ids]
            parts.append(f'[{v.team_name[t]}] ' + '; '.join(st))
        return '  at start (end of r%d) hp, bag; whole-fight damage: ' % (f.r0 - 1) + ' || '.join(parts)

    def turn_actions(self, c, r):
        v, M = self.v, self.M
        t = v.team[c]
        out = []
        for e in v.by_round[r]:
            if e.get('a') != c or e['t'] < 0:
                continue
            k = e['k']
            if k in ('attack', 'cast'):
                tgt = e.get('tgt')
                what = 'atk' if k == 'attack' else f'{e.get("ab", "cast")}'
                bits = []
                for x, d in e.get('dmg', []):
                    bits.append(f'{v.ally_enemy(x, t)} {d:.0f}')
                for x, d in e.get('cdmg', []):
                    bits.append(f'camp {M.group(M.camp_group[x]).name(t)} {d:.0f}')
                if e.get('heal'):
                    bits += [f'heal {v.ally_enemy(x, t)} {d:.0f}' for x, d in e['heal']] if isinstance(e['heal'], list) else [f'heal {e["heal"]}']
                if e.get('shield') and what != 'Shield':
                    bits.append('shield')
                if e.get('stun'):
                    bits.append('stun ' + ','.join(v.ally_enemy(x, t) for x in e['stun']))
                if e.get('moved'):
                    bits.insert(0, f'to {P(e["moved"])}')
                if e.get('lock'):
                    bits.append(f'lock hit ({e.get("hits")} left)')
                if e.get('refl'):
                    bits.append(f'reflected {e["refl"]:.0f}')
                out.append(what + ' ' + ', '.join(bits) if bits else what + (' (no effect)' if not tgt else ''))
            elif k == 'ward':
                out.append(f'ward {P(e["to"])}')
            elif k == 'tribute_start':
                out.append(f'tribute start bag {e["gems"]}')
            elif k == 'lock_place':
                out.append('lock placed')
            elif k == 'teleport_start':
                out.append(f'teleport to {P(e["to"])}')
            elif k == 'recall_start':
                if any(rc['c'] == c and rc['r0'] == r for rc in self.tr.recalls):
                    out.append('recall start')
            elif k == 'blocked':
                out.append(f'bumped unseen unit {P(e["to"])}')
        for e in v.deaths[r]:
            if e.get('by') == c and 'linked' not in e:
                out.append(f'KILLED {v.ally_enemy(e["v"], t)} (+{e.get("gemsTo", 0)} gems, +{e.get("gold", 0):.0f} gold)')
        return out
