"""Would ally-to-ally messages (strike pledges, stun claims) raise kill conversion? Replay-only measurement over
each enemy champion X's interval I: from just after X's turn in round r to just before its turn in round r+1 (or
its death). Every hit the hunting team lands in I lands before X can react.

Metrics (per hunting team): 1 kill-interval decomposition (X at <= 25% / 40% effective health, off its spawn, a
hunter within 4), 2 missed focus kills and split rate, 3 unneeded hits and the finisher, 4 wasted stuns,
5 round-boundary doubles in metric-1 intervals. Effective health = hp + shield (damage amounts include shield).

usage: python3 research/turn-order-2026-11-02/scripts/comms_replay.py run EXTRACT_DIR OUT.pkl [--self NAME] [--procs 40]
       python3 research/turn-order-2026-11-02/scripts/comms_replay.py report OUT.pkl [OUT2.pkl ...] [--teams A,B,...]
       python3 research/turn-order-2026-11-02/scripts/comms_replay.py show EXTRACT_DIR DIR X ROUND
`--self NAME` names both teams NAME (self-play batches).
"""
import json
import pickle
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tolib import G, cheb, index  # noqa: E402

MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Heart of Ruin', 'Issac'}
UNIT_CAST_RANGE = 4
STUN_UNIT = {('Prism', 0), ('Tavi', 1), ('Ren', 0), ('Cassi', 1)}
STUN_AOE = {('Ryth', 0), ('Heart of Ruin', 1)}
MULT = {('Prism', 0): 1.5, ('Prism', 1): 1.0, ('Stellar', 0): 2, ('Stellar', 1): 1.4, ('Marcella', 1): 2,
        ('Cassi', 0): 2, ('Tavi', 1): 1.6, ('Ren', 0): 1.1, ('Ryth', 0): 1.0, ('Heart of Ruin', 1): 1.5}
REL = {'attack', 'cast', 'camp_attack', 'death'}
POSK = {'move', 'cast', 'respawn', 'recall_end', 'teleport_end', 'death'}
THRS = (25, 40)
# 'w' engagement: distance from which the champion can hit this turn (unit casts 4, Ryth's 3x3 ground cast 5,
# dash + melee 3, Vesper walk + reset + attack 4); the default engagement is attack range + 1.
REACH = {'Prism': 4, 'Stellar': 4, 'Marcella': 4, 'Cassi': 4, 'Tavi': 4, 'Ren': 4, 'Ryth': 5, 'Vendetta': 3,
         'Issac': 3, 'Heart of Ruin': 3, 'Vesper Vale': 4, 'Willow': 4}


def dmg_to(e, x):
    """Damage (incl. shield absorbed) champion x takes in event e."""
    k = e['k']
    d = 0.0
    if k in ('attack', 'cast'):
        for v, a in e.get('dmg') or []:
            if v == x:
                d += a
        if e.get('reflBy') is not None and e.get('a') == x:
            d += e.get('refl') or 0
    elif k == 'camp_attack':
        if e.get('tgt') == x:
            d += e.get('dmg') or 0
        xd = e.get('xdmg') or []
        if isinstance(xd, dict):
            xd = list(xd.items())
        for v, a in xd:
            if int(v) == x:
                d += a
    return d


def cdmg(e):
    v = e.get('cdmg') or 0
    return sum(a for _, a in v) if isinstance(v, list) else v


def heal_to(e, x):
    return sum(a for v, a in (e.get('heal') or []) if v == x) if e['k'] == 'cast' else 0.0


class Game:
    def __init__(self, ex, row, selfname=None):
        g = self.g = G(ex, row['dir'])
        self.names = [selfname, selfname] if selfname else list(row['teams'])
        mp = json.load(open(f"{ex}/maps/{g.meta['map']['hash']}.json"))
        self.spawn = mp['spawn']
        self.rng = {c: (1 if g.type[c] in MELEE else 3) for c in g.ids}
        self.reach = {c: REACH.get(g.type[c], self.rng[c] + 1) for c in g.ids}
        self.rel = defaultdict(list)
        self.posev = defaultdict(list)
        for e in g.events:
            if e['k'] in REL:
                self.rel[e['r']].append(e)
            if e['k'] in POSK:
                self.posev[e['r']].append(e)
        self._snap = {}

    def on_spawn(self, c, p):
        sp = self.spawn[self.g.team[c]]
        return sp['minX'] <= p[0] <= sp['maxX'] and sp['minY'] <= p[1] <= sp['maxY']

    def snap(self, r, t):
        """Positions of every champion after slot t of round r (t = -1: after the round phases)."""
        k = (r, t)
        s = self._snap.get(k)
        if s is not None:
            return s
        g = self.g
        s = {c: g.pos(c, r - 1) for c in g.ids}
        for e in self.posev[r]:
            if e['t'] > t:
                break
            kk = e['k']
            if kk == 'death':
                s[e['v']] = None
            elif kk == 'move':
                s[e['a']] = tuple(e['to'])
            elif kk == 'cast':
                if e.get('moved'):
                    s[e['a']] = tuple(e['moved'])
            elif kk == 'respawn':
                s[e['a']] = tuple(e['at'])
            else:
                s[e['a']] = tuple(e['to'])
        self._snap[k] = s
        return s

    def interval(self, x, r):
        """Events (attack/cast/camp_attack/death) of x's interval after round r's turn, truncated at x's death."""
        g = self.g
        sx = g.order(r)[1][x]
        sx1 = g.order(r + 1)[1][x]
        ev = [e for e in self.rel[r] if e['t'] > sx] + [e for e in self.rel[r + 1] if e['t'] < sx1]
        death = None
        for i, e in enumerate(ev):
            if e['k'] == 'death' and e['v'] == x:
                death = e
                j = i
                while j + 1 < len(ev) and ev[j + 1]['s'] == e['s']:
                    j += 1
                ev = ev[:j + 1]
                break
        return sx, sx1, ev, death


def targets(g, e):
    """Enemy champions an attack/cast hit (damage > 0), stunned, or unit-targeted."""
    a = e['a']
    ta = g.team[a]
    out = set()
    for v, amt in e.get('dmg') or []:
        if amt > 0 and v in g.team and g.team[v] != ta:
            out.add(v)
    for v in e.get('stun') or []:
        if v in g.team and g.team[v] != ta:
            out.add(v)
    tg = e.get('tgt')
    if tg is not None and 'camp' not in e and tg in g.team and g.team[tg] != ta:
        out.add(tg)
    return out


def champ_dmg(g, e, only=None):
    ta = g.team[e['a']]
    return sum(amt for v, amt in (e.get('dmg') or []) if v in g.team and g.team[v] != ta and (only is None or v in only))


def is_unit_cast(e):
    return e['k'] == 'cast' and e.get('ab') in ('Damage', 'CC')


def reach(G_, e):
    """Range from the action's tile at which the actor could have hit another champion with this action."""
    if e['k'] == 'attack':
        return G_.rng[e['a']]
    if is_unit_cast(e):
        return UNIT_CAST_RANGE
    return None


def est_full(G_, e, r):
    """Uncapped damage of an action against a champion (the killing blow's recorded damage is capped)."""
    g = G_.g
    a = e['a']
    ty = g.type[a]
    if e['k'] == 'attack':
        d = g.at(a, 'str', r - 1)
    else:
        m = MULT.get((ty, e.get('slot')))
        if m is None:
            return 0.0
        d = m * g.at(a, 'foc', r - 1)
    if ty == 'Heart of Ruin':
        mx = g.at(a, 'maxHp', r - 1)
        d *= 1 + 0.5 * max(0.0, 1 - g.at(a, 'hp', r - 1) / mx)
    return d


def one(args):
    ex, row, selfname = args
    try:
        GG = Game(ex, row, selfname)
    except Exception as ex_:  # noqa: BLE001
        return {'error': str(ex_), 'dir': row['dir']}
    g = GG.g
    K = [Counter(), Counter()]  # per hunting team
    examples = []
    mex = []
    val = Counter()
    # ------------------------------------------------------------------ intervals (metrics 1, 2, 3, 5)
    for r in range(2, g.N):
        seq_r, slot_r, _ = g.order(r)
        seq_n, slot_n, _ = g.order(r + 1)
        for x in g.ids:
            if g.pos(x, r - 1) is None:
                continue
            t = 1 - g.team[x]
            hunters = g.members[t]
            sx, sx1 = slot_r[x], slot_n[x]
            if any(d['v'] == x and d['t'] <= sx for d in g.deaths[r]):
                continue
            # quick reject: no hunter action on a champion in I, x not low, no death
            sx_, sx1_, ev, death = GG.interval(x, r)
            mx = g.at(x, 'maxHp', r)
            e_end = (g.hp(x, r) + (g.at(x, 'shield', r) or 0)) if g.alive(x, r) else 0.0
            after_dmg = sum(dmg_to(e, x) for e in GG.rel[r] if e['t'] > sx)
            after_heal = sum(heal_to(e, x) for e in GG.rel[r] if e['t'] > sx)
            e0 = e_end + after_dmg - after_heal
            hacts = [e for e in ev if e['k'] in ('attack', 'cast') and e['a'] in g.team and g.team[e['a']] == t]
            hits_champ = [e for e in hacts if targets(g, e)]
            low = e0 <= 0.40 * mx
            if not (low or hits_champ or death):
                continue
            sn = GG.snap(r, sx)
            px = sn[x]
            if px is None or GG.on_spawn(x, px):
                continue
            dmg_I = sum(dmg_to(e, x) for e in ev)
            heal_I = sum(heal_to(e, x) for e in ev)
            if death is not None:
                # validation: hp before the killing step from our reconstruction vs the death event's hp
                pre = e0 - sum(dmg_to(e, x) - heal_to(e, x) for e in ev if e['s'] < death['s'])
                if not death.get('linked'):
                    val['deaths'] += 1
                    ok = abs(pre - death['hp']) <= 1.0 + 0.002 * mx
                    shielded = (g.at(x, 'shield', r - 1) or 0) > 0 or any(
                        q['k'] == 'cast' and q['a'] == x and q.get('shield') for q in GG.rel[r])
                    val['death_hp_ok'] += ok
                    val['death_hp_shield'] += (not ok) and shielded and pre > death['hp']
                    if not ok and not shielded and len(examples) < 40:
                        examples.append(('valfail', x, r, round(pre, 1), death['hp']))
            dead = death is not None
            cause = None
            if dead:
                if death.get('linked'):
                    cause = 'linked'
                elif death.get('by') in hunters:
                    cause = 'hunter'
                elif death.get('camp') is not None:
                    cause = 'camp'
                else:
                    cause = 'other'
            dkey = (death['r'], death['t']) if dead else (10 ** 9, 0)
            # hunter schedule in I
            sched = {}
            for c in hunters:
                tt = []
                if slot_r[c] > sx:
                    tt.append((r, slot_r[c]))
                if slot_n[c] < sx1:
                    tt.append((r + 1, slot_n[c]))
                sched[c] = tt
            acts_by = defaultdict(list)
            for e in hacts:
                acts_by[e['a']].append(e)
            # running effective health of x before step s
            steps = [(e['s'], dmg_to(e, x) - heal_to(e, x)) for e in ev]

            def e_at(s):
                return e0 - sum(d for ss, d in steps if ss < s)

            near4 = [c for c in hunters if sn[c] is not None and cheb(sn[c], px) <= 4]
            frac = e0 / mx
            # ---------------- primary target per hitter (split rate)
            prim = {}
            for c, es in acts_by.items():
                tot = Counter()
                for e in es:
                    for v, amt in e.get('dmg') or []:
                        if v in g.team and g.team[v] != g.team[c] and amt > 0:
                            tot[v] += amt
                    for v in targets(g, e):
                        tot[v] += 1e-6
                if tot:
                    prim[c] = max(tot, key=tot.get)
            x_hit = any(x in targets(g, e) for e in hacts)
            # ---------------- metric 1 / 5
            for thr, mode in [(t_, m_) for t_ in THRS for m_ in ('', 'w')]:
                if frac > thr / 100 or not near4:
                    continue
                k = K[t]
                p = f'm1{mode}.{thr}.'
                k[p + 'n'] += 1
                if dead:
                    k[p + 'died'] += 1
                    k[p + 'died_' + cause] += 1
                n_eng = 0
                n_sched_eng = 0
                double = False
                for c in hunters:
                    pc = sn[c]
                    if pc is None or cheb(pc, px) > (GG.reach[c] if mode else GG.rng[c] + 1):
                        continue
                    n_sched_eng += len(sched[c])
                    double |= len(sched[c]) == 2
                    turns = [(rr, ss) for rr, ss in sched[c] if (rr, ss) <= dkey and g.at(c, 'turn', rr) not in (0, 4)]
                    if not turns:
                        continue
                    n_eng += 1
                    k[p + 'eng'] += 1
                    es = acts_by.get(c, [])
                    if len(sched[c]) == 2:
                        # the doubled hunter: how many of its two turns hit x (second may be cut by x's death)
                        hr = {e['r'] for e in es if x in targets(g, e)}
                        k[p + 'dh'] += 1
                        k[p + f'dh_hit{len(hr)}'] += 1
                        k[p + 'dh_cut'] += len(turns) < 2
                    tg = set()
                    camp = False
                    for e in es:
                        tg |= targets(g, e)
                        camp |= ('camp' in e) or bool(e.get('cdmg')) or bool(e.get('lock'))
                        k[p + 'dmg_eng_x'] += sum(a for v, a in (e.get('dmg') or []) if v == x)
                        k[p + 'dmg_eng_other'] += champ_dmg(g, e) - sum(a for v, a in (e.get('dmg') or []) if v == x)
                        k[p + 'dmg_eng_camp'] += cdmg(e)
                    if x in tg:
                        cl = 'x'
                    elif tg:
                        cl = 'other'
                    elif camp:
                        cl = 'camp'
                    else:
                        codes = [g.at(c, 'turn', rr) for rr, _ in turns]
                        cl = ('none_acted' if 1 in codes else 'none_channel' if 3 in codes else
                              'none_stunned' if 5 in codes else 'none_idle' if 2 in codes else 'none_misc')
                        # could it have hit x? x visible and in attack range at a free turn's start
                        for rr, ss in turns:
                            if g.at(c, 'turn', rr) not in (1, 2):
                                continue
                            pc0 = GG.snap(rr, ss - 1)[c]
                            if pc0 is not None and cheb(pc0, px) <= GG.rng[c] and x in (g.sees(c, rr) or []):
                                k[p + 'none_could'] += 1
                                sstep = min((e['s'] for e in GG.rel[rr] if e['t'] >= ss), default=10 ** 12)
                                if g.at(c, 'str', rr - 1) >= e_at(sstep):
                                    k[p + 'none_could_kill'] += 1
                                break
                        if cl == 'none_acted':
                            # what the first acting turn did instead: recall start, or a walk closer/level/away
                            rr, ss = next((rr, ss) for rr, ss in turns if g.at(c, 'turn', rr) == 1)
                            mine = [q for q in g.by_round[rr] if q.get('a') == c and q['t'] == ss]
                            d0 = GG.snap(rr, ss - 1)[c]
                            d1 = GG.snap(rr, ss)[c]
                            k[p + 'na_recall'] += any(q['k'] == 'recall_start' for q in mine)
                            if d0 is None or d1 is None:
                                sub = 'other'
                            else:
                                a0, a1 = cheb(d0, px), cheb(d1, px)
                                sub = 'closer' if a1 < a0 else 'away' if a1 > a0 else 'still' if d0 == d1 else 'level'
                                k[p + 'na_endrange'] += a1 <= GG.rng[c]
                                if GG.rng[c] == 1:
                                    k[p + 'na_melee_endrange'] += a1 <= 1
                            k[p + 'na_' + sub] += 1
                            k[p + 'na_melee'] += GG.rng[c] == 1
                            k[p + 'na_seen'] += x in (g.sees(c, rr) or [])
                    k[p + 'cl_' + cl] += 1
                    if cl.startswith('none'):
                        k[p + 'cl_none'] += 1
                k[p + 'dmg_all_x'] += sum(sum(a for v, a in (e.get('dmg') or []) if v == x) for e in hacts)
                if n_eng:
                    k[p + 'with_eng'] += 1
                    k[p + 'with_eng_died'] += dead
                    k[p + 'with_eng_died_hunter'] += cause == 'hunter'
                b = min(n_sched_eng, 4)
                k[p + f'sched{b}'] += 1
                k[p + f'sched{b}_died'] += dead
                if n_sched_eng:
                    kk = 'dbl' if double else 'sgl'
                    k[p + kk] += 1
                    k[p + kk + '_died'] += dead
                    k[p + kk + '_hunter'] += cause == 'hunter'
                hitters = [c for c in prim]
                if len(hitters) >= 2 and x_hit:
                    k[p + 'n2hit'] += 1
                    k[p + 'split'] += len({prim[c] for c in hitters}) > 1
                if len(examples) < 40 and thr == 25 and not mode:
                    examples.append(('m1', x, r, 'died' if dead else 'surv'))
            # split over all intervals where x is hit
            if x_hit and len(prim) >= 2:
                K[t]['all.n2hit'] += 1
                K[t]['all.split'] += len({prim[c] for c in prim}) > 1
            # ---------------- metric 2: x survives, a hunter hit someone else with x in reach
            if not dead:
                e_rem = e0 - dmg_I + heal_I
                red_all = 0.0
                miss = miss_vis = miss_ys = miss_vis_ys = False
                cand = False
                for c, es in acts_by.items():
                    red = 0.0
                    red_vis = 0.0
                    ys = set()
                    for e in es:
                        tg = targets(g, e)
                        if not tg or x in tg:
                            continue
                        rg = reach(GG, e)
                        if rg is None or cheb(tuple(e['f']), px) > rg:
                            continue
                        d = champ_dmg(g, e) if e['k'] == 'attack' else champ_dmg(g, e, {e.get('tgt')})
                        red += d
                        if x in (g.sees(c, e['r']) or []):
                            red_vis += d
                        ys |= tg
                    if red <= 0:
                        continue
                    cand = True
                    red_all += red
                    ysurv = not any(q['k'] == 'death' and q['v'] in ys for q in ev)
                    if red >= e_rem:
                        if len(mex) < 5 and frac <= 0.25:
                            mex.append(('m2', x, r, c, round(red, 1), round(e_rem, 1), sorted(ys), ysurv))
                        miss = True
                        miss_ys |= ysurv
                    if red_vis >= e_rem and red_vis > 0:
                        miss_vis = True
                        miss_vis_ys |= ysurv
                k = K[t]
                for p in ['m2.all.'] + [f'm2.{thr}.' for thr in THRS if frac <= thr / 100 and near4]:
                    k[p + 'n'] += 1
                    if cand:
                        k[p + 'cand'] += 1
                        k[p + 'miss'] += miss
                        k[p + 'miss_ysurv'] += miss_ys
                        k[p + 'miss_vis'] += miss_vis
                        k[p + 'miss_vis_ysurv'] += miss_vis_ys
                        k[p + 'miss_pooled'] += red_all >= e_rem
                    # camp variant: hitters that hit only camps with x in reach of their action tile
                    camp_miss = False
                    for c in hunters:
                        es = acts_by.get(c, [])
                        if not es or any(targets(g, e) for e in es):
                            continue
                        red = 0.0
                        for e in es:
                            if not (('camp' in e) or e.get('cdmg')):
                                continue
                            rg = reach(GG, e)
                            if rg is None or cheb(tuple(e['f']), px) > rg or x not in (g.sees(c, e['r']) or []):
                                continue
                            red += g.at(c, 'str', e['r'] - 1) if e['k'] == 'attack' else cdmg(e)
                        if red > 0:
                            k[p + 'camp_cand'] += 1
                            camp_miss |= red >= e_rem
                    k[p + 'camp_miss'] += camp_miss
            # ---------------- metric 3: x killed directly by a hunter
            if dead and cause == 'hunter':
                k = K[t]
                hits = []
                other_d = 0.0
                for e in ev:
                    d = dmg_to(e, x)
                    if e['k'] in ('attack', 'cast') and e['a'] in hunters:
                        if d <= 0:
                            continue
                        if e['s'] == death['s'] and e['a'] == death['by']:
                            d = max(d, est_full(GG, e, e['r']))
                        hits.append((e, d))
                    else:
                        other_d += d
                need = e0 + heal_I
                total = other_d + sum(d for _, d in hits)
                k['m3.kills'] += 1
                k['m3.hits'] += len(hits)
                un = 0
                for e, d in hits:
                    if total - d >= need:
                        un += 1
                        rg = reach(GG, e) or UNIT_CAST_RANGE
                        s2 = GG.snap(e['r'], e['t'] - 1)
                        alt = any(s2[y] is not None and cheb(s2[y], tuple(e['f'])) <= rg
                                  for y in g.members[1 - t] if y != x and g.alive(y, e['r'] - 1))
                        k['m3.unneeded_alt'] += alt
                k['m3.unneeded'] += un
                k['m3.kills_unneeded'] += un > 0
                ds = sorted((d for _, d in hits), reverse=True)
                acc, m = other_d, 0
                for d in ds:
                    if acc >= need:
                        break
                    acc += d
                    m += 1
                k['m3.excess'] += len(hits) - m
                k['m3.kills_excess'] += len(hits) > m
                per = Counter()
                for e in ev:
                    if e['k'] in ('attack', 'cast') and e['a'] in hunters:
                        per[e['a']] += sum(a for v, a in (e.get('dmg') or []) if v == x)
                fin = death['by']
                tot = sum(per.values())
                k['m3.fin_top'] += bool(per) and per[fin] >= max(per.values())
                k['m3.fin_share'] += per[fin] / tot if tot > 0 else 1.0
                k['m3.hitters'] += len(per)
                if len(per) >= 2:
                    k['m3.multi'] += 1
                    k['m3.multi_fin_top'] += per[fin] >= max(per.values())
                k['m3.kill_gems'] += death.get('gems') or 0
    # ------------------------------------------------------------------ metric 4: stuns
    pending = {}  # victim -> (round, slot) of the turn the stun removes
    who = defaultdict(set)  # (victim, removed turn) -> stunning hunters (attempts)
    armed = {}
    for e in g.events:
        k_ = e['k']
        if k_ not in ('attack', 'cast'):
            continue
        a = e['a']
        ty = g.type[a]
        r, tt = e['r'], e['t']
        stun_act = False
        if k_ == 'cast':
            if ty == 'Marcella' and e.get('slot') == 0:
                armed[a] = (r, tt)
            key = (ty, e.get('slot'))
            if key in STUN_UNIT:
                stun_act = True
                kind = 'unit'
                if 'camp' in e:
                    K[g.team[a]]['m4.camp_target'] += 1
                    stun_act = False
                vs = {e['tgt']} if e.get('tgt') in g.team and g.team[e['tgt']] != g.team[a] else set()
            elif key in STUN_AOE:
                vs = targets(g, e)
                stun_act = bool(vs)
                kind = 'aoe'
        else:
            if ty == 'Marcella' and armed.get(a) == (r, tt):
                del armed[a]
                stun_act = 'camp' not in e and not e.get('lock')
                kind = 'unit'
                vs = {e['tgt']} if e.get('tgt') in g.team and g.team[e['tgt']] != g.team[a] else set()
        newly = set(e.get('stun') or [])
        if stun_act and vs:
            k = K[g.team[a]]
            k['m4.actions'] += 1
            k[f'm4.{kind}.actions'] += 1
            any_new = False
            for v in vs:
                k['m4.targets'] += 1
                pend = pending.get(v)
                if v in newly:
                    st = 'new'
                    any_new = True
                elif pend is not None and (r, tt) < pend:
                    st = 'dup'
                elif g.type[v] == 'Marcella':
                    st = 'immune'
                elif any(d['v'] == v and d['s'] == e['s'] for d in g.deaths[r]):
                    st = 'killed'
                else:
                    st = 'other'
                k['m4.' + st] += 1
                k[f'm4.{kind}.{st}'] += 1
                k[f'm4.type.{ty}.{st}'] += 1
                if st in ('new', 'dup'):
                    nt = pend if st == 'dup' else None
                    if nt is None:
                        sv = g.order(r)[1][v]
                        nt = (r, sv) if sv > tt else (r + 1, g.order(r + 1)[1][v])
                    who[(v, nt)].add(a)
                if st == 'new':
                    sv = g.order(r)[1][v]
                    nt = (r, sv) if sv > tt else (r + 1, g.order(r + 1)[1][v])
                    # stun spent on a target that then died before the removed turn
                    died = any(d['v'] == v and (d['r'], d['t']) < nt and d['s'] >= e['s']
                               for rr in (r, r + 1) for d in g.deaths[rr])
                    k['m4.new_then_died'] += died
            k['m4.actions_wasted'] += not any_new
            k[f'm4.{kind}.actions_wasted'] += not any_new
        for v in newly:
            sv = g.order(r)[1][v]
            pending[v] = (r, sv) if sv > tt else (r + 1, g.order(r + 1)[1][v])
    for (v, nt), s in who.items():
        K[1 - g.team[v]]['m4.windows'] += 1
        K[1 - g.team[v]]['m4.windows_multi'] += len(s) >= 2
    for t in (0, 1):
        K[t]['games'] += 1
        K[t]['wins'] += g.meta['result']['winner'] == t
        K[t]['rounds'] += g.N
    return {'dir': row['dir'], 'names': GG.names, 'K': K, 'val': val, 'examples': examples[:10], 'mex': mex}


def run(ex, outp, selfname, procs):
    seen, todo = set(), []
    for r in index(ex):
        if not r['ok'] or r['dir'] in seen:
            continue
        seen.add(r['dir'])
        todo.append((ex, r, selfname))
    with ProcessPoolExecutor(procs) as pool:
        res = list(pool.map(one, todo, chunksize=8))
    pickle.dump(res, open(outp, 'wb'))
    v = Counter()
    for x in res:
        v.update(x.get('val', {}))
    print(len(res), 'games;', sum(1 for x in res if 'error' in x), 'errors; validation', dict(v))


def pct(a, b):
    return f'{100 * a / b:.1f}%' if b else '-'


def report(paths, teams):
    agg = defaultdict(Counter)
    for pth in paths:
        for x in pickle.load(open(pth, 'rb')):
            if 'error' in x:
                continue
            for t in (0, 1):
                agg[x['names'][t]].update(x['K'][t])
                if 'astraeus' not in x['names'][t] and x['names'][t] != x['names'][1 - t]:
                    agg['ladder (all teams)'].update(x['K'][t])
    if not teams:
        teams = [n for n, _ in sorted(agg.items(), key=lambda kv: -kv[1]['games'])][:12]
    cols = [t for t in teams if t in agg]
    w = 14

    def line(label, f):
        print(f'{label:<44}' + ''.join(f'{str(f(agg[t])):>{w}}' for t in cols))

    print(f'{"":<44}' + ''.join(f'{t[:w - 1]:>{w}}' for t in cols))
    line('games', lambda k: k['games'])
    line('win rate', lambda k: pct(k['wins'], k['games']))
    for thr in THRS:
        p = f'm1.{thr}.'
        print(f'--- metric 1/5: X at <= {thr}% eff. health, off spawn, hunter within 4')
        line('intervals', lambda k: k[p + 'n'])
        line('  per game', lambda k: f"{k[p + 'n'] / max(1, k['games']):.2f}")
        line('X dies in I', lambda k: pct(k[p + 'died'], k[p + 'n']))
        line('  by hunter / linked / camp', lambda k: f"{pct(k[p + 'died_hunter'], k[p + 'n'])}/{k[p + 'died_linked']}/{k[p + 'died_camp']}")
        line('intervals with an engaged hunter', lambda k: pct(k[p + 'with_eng'], k[p + 'n']))
        line('  X dies (with engaged)', lambda k: pct(k[p + 'with_eng_died'], k[p + 'with_eng']))
        line('engaged hunter-intervals', lambda k: k[p + 'eng'])
        for cl in ('x', 'other', 'camp', 'none'):
            line(f'  hit {cl}', lambda k, cl=cl: pct(k[p + 'cl_' + cl], k[p + 'eng']))
        for cl in ('none_acted', 'none_idle', 'none_channel', 'none_stunned', 'none_misc'):
            line(f'    {cl}', lambda k, cl=cl: pct(k[p + 'cl_' + cl], k[p + 'eng']))
        for sub in ('closer', 'level', 'still', 'away', 'other', 'endrange', 'seen', 'recall'):
            line(f'    none_acted: {sub}', lambda k, sub=sub: pct(k[p + 'na_' + sub], k[p + 'eng']))
        line('    none_acted: melee (of engaged)', lambda k: pct(k[p + 'na_melee'], k[p + 'eng']))
        line('    none_acted: melee ending adjacent', lambda k: pct(k[p + 'na_melee_endrange'], k[p + 'eng']))
        line('  none, X visible in attack range', lambda k: pct(k[p + 'none_could'], k[p + 'eng']))
        line('    ... and its Strength >= X eff. health', lambda k: pct(k[p + 'none_could_kill'], k[p + 'eng']))
        line('dmg per interval: engaged on X', lambda k: f"{k[p + 'dmg_eng_x'] / max(1, k[p + 'n']):.0f}")
        line('  engaged on other champs', lambda k: f"{k[p + 'dmg_eng_other'] / max(1, k[p + 'n']):.0f}")
        line('  engaged on camps', lambda k: f"{k[p + 'dmg_eng_camp'] / max(1, k[p + 'n']):.0f}")
        line('  all hunters on X', lambda k: f"{k[p + 'dmg_all_x'] / max(1, k[p + 'n']):.0f}")
        line('split (>=2 hitters, X hit): n', lambda k: k[p + 'n2hit'])
        line('  primaries differ', lambda k: pct(k[p + 'split'], k[p + 'n2hit']))
        line('m5: engaged double turn: n', lambda k: k[p + 'dbl'])
        line('  X dies | double', lambda k: pct(k[p + 'dbl_died'], k[p + 'dbl']))
        line('  X dies | single (n)', lambda k: f"{pct(k[p + 'sgl_died'], k[p + 'sgl'])} ({k[p + 'sgl']})")
        line('  doubled engaged hunters (n)', lambda k: k[p + 'dh'])
        line('    hit X on 0/1/2 of its turns', lambda k: '/'.join(pct(k[p + f'dh_hit{i}'], k[p + 'dh']) for i in range(3)))
        line('    second turn cut by X death', lambda k: pct(k[p + 'dh_cut'], k[p + 'dh']))
        for b in range(5):
            line(f'  sched engaged turns {b}{"+" if b == 4 else ""}: died (n)',
                 lambda k, b=b: f"{pct(k[p + f'sched{b}_died'], k[p + f'sched{b}'])} ({k[p + f'sched{b}']})")
        p = f'm1w.{thr}.'
        print(f'  - same intervals, engagement = can hit X this turn (casts 4, Ryth 5, dash-melee 3)')
        line('  intervals with an engaged hunter', lambda k: pct(k[p + 'with_eng'], k[p + 'n']))
        line('    X dies (with engaged)', lambda k: pct(k[p + 'with_eng_died'], k[p + 'with_eng']))
        line('  engaged hunter-intervals', lambda k: k[p + 'eng'])
        for cl in ('x', 'other', 'camp', 'none', 'none_acted', 'none_idle', 'none_channel', 'none_stunned'):
            line(f'    {cl}', lambda k, cl=cl: pct(k[p + 'cl_' + cl], k[p + 'eng']))
        line('    none, X visible in attack range', lambda k: pct(k[p + 'none_could'], k[p + 'eng']))
        line('  X dies | double (n)', lambda k: f"{pct(k[p + 'dbl_died'], k[p + 'dbl'])} ({k[p + 'dbl']})")
        line('  X dies | single (n)', lambda k: f"{pct(k[p + 'sgl_died'], k[p + 'sgl'])} ({k[p + 'sgl']})")
        line('  X dies | no engaged turn (n)', lambda k: f"{pct(k[p + 'sched0_died'], k[p + 'sched0'])} ({k[p + 'sched0']})")
    print('--- split over all intervals with X hit and >= 2 hitters')
    line('n', lambda k: k['all.n2hit'])
    line('primaries differ', lambda k: pct(k['all.split'], k['all.n2hit']))
    for p, lab in (('m2.all.', 'all intervals'), ('m2.40.', '<= 40%'), ('m2.25.', '<= 25%')):
        print(f'--- metric 2 (X survives I), {lab}')
        line('intervals', lambda k: k[p + 'n'])
        line('with a hunter hitting Y, X in its reach', lambda k: k[p + 'cand'])
        line('missed focus kills', lambda k: k[p + 'miss'])
        line('  per game', lambda k: f"{k[p + 'miss'] / max(1, k['games']):.3f}")
        line('  of candidates', lambda k: pct(k[p + 'miss'], k[p + 'cand']))
        line('  Y also survived I', lambda k: k[p + 'miss_ysurv'])
        line('  X visible to c (n / Y surv)', lambda k: f"{k[p + 'miss_vis']}/{k[p + 'miss_vis_ysurv']}")
        line('  pooled over hunters', lambda k: k[p + 'miss_pooled'])
        line('camp hitters with X in reach (n)', lambda k: k[p + 'camp_cand'])
        line('  camp-hit damage would kill X', lambda k: k[p + 'camp_miss'])
    print('--- metric 3: X killed directly by a hunter in I')
    line('kills', lambda k: k['m3.kills'])
    line('  per game', lambda k: f"{k['m3.kills'] / max(1, k['games']):.2f}")
    line('hits per kill', lambda k: f"{k['m3.hits'] / max(1, k['m3.kills']):.2f}")
    line('hitters per kill', lambda k: f"{k['m3.hitters'] / max(1, k['m3.kills']):.2f}")
    line('unneeded hits per kill', lambda k: f"{k['m3.unneeded'] / max(1, k['m3.kills']):.3f}")
    line('kills with an unneeded hit', lambda k: pct(k['m3.kills_unneeded'], k['m3.kills']))
    line('  unneeded hitter had another target', lambda k: pct(k['m3.unneeded_alt'], k['m3.unneeded']))
    line('excess hits (vs min. set) per kill', lambda k: f"{k['m3.excess'] / max(1, k['m3.kills']):.3f}")
    line('kills with excess hits', lambda k: pct(k['m3.kills_excess'], k['m3.kills']))
    line('finisher = top damage', lambda k: pct(k['m3.fin_top'], k['m3.kills']))
    line('  among multi-hitter kills (n)', lambda k: f"{pct(k['m3.multi_fin_top'], k['m3.multi'])} ({k['m3.multi']})")
    line('finisher damage share', lambda k: pct(k['m3.fin_share'], k['m3.kills']))
    print('--- metric 4: stuns (actions with an enemy champion target)')
    line('stun actions', lambda k: k['m4.actions'])
    line('  per game', lambda k: f"{k['m4.actions'] / max(1, k['games']):.2f}")
    line('action-targets', lambda k: k['m4.targets'])
    for st in ('new', 'dup', 'immune', 'killed', 'other'):
        line(f'  {st}', lambda k, st=st: pct(k['m4.' + st], k['m4.targets']))
    line('  dup per game', lambda k: f"{k['m4.dup'] / max(1, k['games']):.3f}")
    line('actions stunning nobody', lambda k: pct(k['m4.actions_wasted'], k['m4.actions']))
    for kind in ('unit', 'aoe'):
        line(f'{kind} (Prism0 Tavi1 Ren0 Cassi1 Marcella) actions' if kind == 'unit' else 'aoe (Ryth0, HoR dash) actions',
             lambda k, kind=kind: k[f'm4.{kind}.actions'])
        line('  per game', lambda k, kind=kind: f"{k[f'm4.{kind}.actions'] / max(1, k['games']):.2f}")
        for st in ('new', 'dup', 'immune', 'killed'):
            line(f'  {st} (per target)', lambda k, st=st, kind=kind: pct(k[f'm4.{kind}.{st}'], sum(k[f'm4.{kind}.{q}'] for q in ('new', 'dup', 'immune', 'killed', 'other'))))
        line('  dup per game', lambda k, kind=kind: f"{k[f'm4.{kind}.dup'] / max(1, k['games']):.3f}")
        line('  actions stunning nobody', lambda k, kind=kind: pct(k[f'm4.{kind}.actions_wasted'], k[f'm4.{kind}.actions']))
    line('new stun, victim died before lost turn', lambda k: pct(k['m4.new_then_died'], k['m4.new']))
    line('stun windows; >= 2 hunters stunning', lambda k: f"{k['m4.windows']}; {pct(k['m4.windows_multi'], k['m4.windows'])}")
    line('unit stun cast on a camp', lambda k: k['m4.camp_target'])


def show(ex, d, x, r):
    row = next(rr for rr in index(ex) if rr['dir'] == d)
    GG = Game(ex, row)
    g = GG.g
    sx, sx1, ev, death = GG.interval(x, r)
    print('types', g.type, 'teams', g.members)
    print('order r', g.order(r)[0], 'x slot', sx, '| order r+1', g.order(r + 1)[0], 'x slot', sx1)
    print('x end r: hp', g.hp(x, r), 'shield', g.at(x, 'shield', r), 'max', g.at(x, 'maxHp', r), 'alive', g.alive(x, r))
    print('snap at start', GG.snap(r, sx))
    for e in g.by_round[r] + g.by_round[r + 1]:
        if e['k'] in ('recall_start', 'recall_cancel'):
            continue
        inI = e in ev
        print('I ' if inI else '  ', e)
    print('death', death)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'run':
        sn = a[a.index('--self') + 1] if '--self' in a else None
        pr = int(a[a.index('--procs') + 1]) if '--procs' in a else 40
        run(a[1], a[2], sn, pr)
    elif a[0] == 'report':
        tm = a[a.index('--teams') + 1].split(',') if '--teams' in a else None
        report([p for p in a[1:] if p.endswith('.pkl')], tm)
    elif a[0] == 'show':
        show(a[1], a[2], int(a[3]), int(a[4]))
