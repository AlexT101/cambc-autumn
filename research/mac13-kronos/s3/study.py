#!/usr/bin/env python3
"""s3 Prism war: one pass over the cached games, writing row tables to replays/.s3cache/rows.pkl.

Rows:
  enc   Prism-vs-Prism encounters (both alive within 6; a new one after 20 rounds apart), with the 10 rounds before.
  death Prism deaths (all causes), with the sight window before them.
  dom   per game and dominant Prism (Focus >= 2x the enemy Prism's, both alive): round-by-round branch counts,
        sight, belief, chase episodes and their ends.
  chase chase/engage episodes of a dominant Prism against the weak one.
  game  per game: dominance onset, outcome and the loss classification inputs.
Usage: study.py [--procs 16]
"""
import collections, os, pickle, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import Game, cheb, files, load, rect_dist, UNREACH, CACHE

HURT = 0.4532513  # params::hurt_health_fraction
PRISM_RANGE = 4   # unit and ground abilities
BASIC = 3         # ranged basic attack


def dmg_events(G):
    """(round, actor, target, amount, kind, slot) for champion damage, and stuns (round, actor, target)."""
    out, stuns = [], []
    for e in G.g['ev']:
        if e['k'] not in ('attack', 'cast'):
            continue
        for tgt, amt in e.get('dmg', ()):
            out.append((e['r'], e['a'], tgt, amt, e['k'], e.get('slot', -1)))
        for tgt in e.get('stun', ()):
            stuns.append((e['r'], e['a'], tgt))
    return out, stuns


def ready(G, cid, i, slot):
    """Slot ready at round i+1's turn: cooldown 0 at the end of the round before."""
    if i <= 0:
        return True
    return G.ch[cid]['cd%d' % slot][i - 1] == 0


def burst2(G, cid, i):
    """Two turns of a Prism's damage from round i+1: both ready spells (1.5F stun, 1.0F ground) and two basics."""
    c = G.ch[cid]
    j = max(0, i - 1)
    f, s = c['foc'][j], c['str'][j]
    return (1.5 * f if ready(G, cid, i, 0) else 0) + (1.0 * f if ready(G, cid, i, 1) else 0) + 2 * s


def bstr(G, cid, i0, i1):
    return ''.join((G.branch(cid, i) or ('.',))[0] for i in range(i0, i1))


def doing(b):
    """The branch letter's activity."""
    return {'F': 'farm', 'P': 'hold', 'B': 'bank', 'W': 'bank', 'T': 'tribute', 't': 'tribute', 'C': 'chase', 'A': 'attack',
            'R': 'retreat', 'K': 'recall', 'k': 'recall', 'Q': 'recall', 'H': 'mend', 'S': 'shop', 'G': 'siege',
            'X': 'contest', 'E': 'stop_ender', 'U': 'guard', 'r': 'recovery', '-': 'none', '.': 'none'}.get(b, b)


def analyse(f):
    G = Game(load(f))
    rows = dict(enc=[], death=[], dom=[], chase=[], game=[])
    T = G.T
    dmg, stuns = dmg_events(G)
    dmg_by = collections.defaultdict(list)  # (actor, target) -> [(round, amount, kind, slot)]
    for r, a, t, amt, k, s in dmg:
        dmg_by[(a, t)].append((r, amt, k, s))
    hit_rounds = collections.defaultdict(set)
    for r, a, t, amt, k, sl in dmg:
        hit_rounds[(a, t)].add(r)
    stun_by = collections.defaultdict(list)
    for r, a, t in stuns:
        stun_by[(a, t)].append(r)
    deaths = [e for e in G.g['ev'] if e['k'] == 'death']
    tcancel = [e for e in G.g['ev'] if e['k'] == 'tribute_cancel']
    rcancel = [e for e in G.g['ev'] if e['k'] == 'recall_cancel']
    tribs = [e for e in G.g['ev'] if e['k'] in ('tribute_start', 'tribute_end')]
    res = G.g['result']
    _tl = sorted((e['r'], G.team[e['a']], e['gems']) for e in tribs if e['k'] == 'tribute_end')

    def score_at(team, r):
        return sum(gm for rr, t, gm in _tl if t == team and rr < r)
    both = len(G.prisms) == 2 and G.team[G.prisms[0]] != G.team[G.prisms[1]]
    base = dict(sha=G.g['sha'], T=T, winner=G.winner, gems=res['gems'], both=both)

    # ---------------- deaths of every Prism ----------------
    for e in deaths:
        v = e['v']
        if G.names.get(v) != 'Prism':
            continue
        id_ = e['r'] - 1  # index of the death round
        killer = e.get('by')
        kname = G.names.get(killer) if killer is not None else ('camp' if 'camp' in e else None)
        enemy_prism = [p for p in G.prisms if G.team[p] != G.team[v]]
        ep = enemy_prism[0] if enemy_prism else None
        e_r = e['r']
        row = dict(base, r=e['r'], v=v, vteam=G.team[v], killer=killer, kname=kname, cause=e.get('cause'),
                   gems=e.get('gems', 0), ep_alive=bool(ep is not None and G.alive(ep, id_ - 1)))
        pre = max(0, id_ - 1)
        row['v_hpfrac_pre'] = G.ch[v]['hp'][pre] / max(1, G.ch[v]['maxHp'][pre])
        row['v_foc'] = G.ch[v]['foc'][pre]
        if ep is not None and G.alive(ep, pre):
            row['ep_foc'] = G.ch[ep]['foc'][pre]
            row['pow_ratio_pre'] = G.power(ep, pre) / max(1, G.power(v, pre))
        k = killer if killer is not None and killer in G.ch else None
        if k is not None and G.alive(k, pre):
            # sight window: back from the death while the victim saw the killer, gaps up to 3 rounds
            s, gap = None, 0
            for j in range(id_, max(-1, id_ - 300), -1):
                if j < id_ and not (G.alive(v, j) and G.alive(k, j)):
                    break
                if G.sees(v, k, j):
                    s, gap = j, 0
                else:
                    gap += 1
                    if (s is not None and gap > 3) or (s is None and gap > 10):
                        break
            ks, gap = None, 0
            for j in range(id_, max(-1, id_ - 300), -1):
                if j < id_ and not (G.alive(v, j) and G.alive(k, j)):
                    break
                if G.sees(k, v, j):
                    ks, gap = j, 0
                else:
                    gap += 1
                    if (ks is not None and gap > 3) or (ks is None and gap > 10):
                        break
            row['saw'] = s is not None
            w0 = s if s is not None else max(0, id_ - 5)
            while w0 < id_ and not (G.alive(v, w0) and G.alive(k, w0)):
                w0 += 1
            row['window'] = id_ - w0
            row['killer_saw_first'] = ks is not None and (s is None or ks < s)
            row['k_window'] = id_ - ks if ks is not None else None
            i0 = max(0, w0 - 1)
            row['d_first'] = G.dist(v, k, w0) if G.alive(v, w0) and G.alive(k, w0) else None
            row['d_last'] = G.dist(v, k, pre)
            row['k_pow_ratio_first'] = G.power(k, i0) / max(1, G.power(v, i0))
            row['k_foc_ratio_first'] = G.ch[k]['foc'][i0] / max(1, G.ch[v]['foc'][i0])
            row['v_hpfrac_first'] = G.ch[v]['hp'][i0] / max(1, G.ch[v]['maxHp'][i0])
            row['k_hp_first'] = G.ch[k]['hp'][i0]
            row['k_hpfrac_first'] = G.ch[k]['hp'][i0] / max(1, G.ch[k]['maxHp'][i0])
            row['k_hp_end'] = G.ch[k]['hp'][id_] if G.alive(k, id_) else 0
            row['k_hpfrac_end'] = row['k_hp_end'] / max(1, G.ch[k]['maxHp'][id_])
            row['v_hp_first'] = G.ch[v]['hp'][i0]
            row['v_burst_first'] = burst2(G, v, w0) if G.names[v] == 'Prism' else None
            row['k_burst_first'] = burst2(G, k, w0) if G.names.get(k) == 'Prism' else None
            row['v_ready_first'] = (ready(G, v, w0, 0), ready(G, v, w0, 1))
            row['v_ready_death'] = (ready(G, v, id_, 0), ready(G, v, id_, 1))
            row['k_ready_first'] = (ready(G, k, w0, 0), ready(G, k, w0, 1)) if G.names.get(k) == 'Prism' else None
            # victim's moves relative to the killer, and its branches
            away = toward = still = 0
            for j in range(w0 + 1, id_ + 1):
                if not (G.alive(v, j) and G.alive(v, j - 1) and G.alive(k, j - 1)):
                    continue
                vx, vy = G.pos(v, j)
                px, py = G.pos(v, j - 1)
                kx, ky = G.pos(k, j - 1)
                dd = cheb(vx, vy, kx, ky) - cheb(px, py, kx, ky)
                if (vx, vy) == (px, py):
                    still += 1
                elif dd > 0:
                    away += 1
                elif dd < 0:
                    toward += 1
                else:
                    still += 1
            row['moves'] = (away, toward, still)
            row['v_br'] = bstr(G, v, max(0, w0 - 5), id_ + 1)
            row['v_br_window'] = bstr(G, v, w0, id_ + 1)
            row['k_br_window'] = bstr(G, k, w0, id_ + 1)
            row['v_br_pre5'] = bstr(G, v, max(0, w0 - 5), w0)
            vx, vy = G.pos(v, pre)
            row['v_spawn_steps'] = G.steps(G.team[v], vx, vy)
            row['v_spawn_cheb'] = rect_dist(vx, vy, G.mp['spawn'][G.team[v]])
            row['v_spawn_steps_first'] = G.steps(G.team[v], *G.pos(v, w0)) if G.alive(v, w0) else None
            row['v_ally'] = G.nearest(v, G.allies(v), pre)
            row['v_ally_first'] = G.nearest(v, G.allies(v), w0) if G.alive(v, w0) else None
            row['k_ally'] = G.nearest(k, [a for a in G.allies(k)], pre)
            row['v_altar'] = G.nearest_altar(vx, vy)
            row['v_own_ground'] = G.own_ground(G.team[v], vx, vy)
            row['v_own_ground_first'] = G.own_ground(G.team[v], *G.pos(v, w0)) if G.alive(v, w0) else None
            row['v_gems_first'] = G.ch[v]['gems'][i0]
            row['v_chan'] = G.ch[v]['chan'][pre]
            # damage both ways in the window (rounds w0+1 .. death round)
            lo, hi = w0 + 1, id_ + 1
            row['v_dmg_to_k'] = sum(a for r, a, _, _ in dmg_by[(v, k)] if lo <= r <= hi)
            row['v_hits_to_k'] = [(r, kk, s) for r, a, kk, s in dmg_by[(v, k)] if lo <= r <= hi]
            row['k_dmg_to_v'] = sum(a for r, a, _, _ in dmg_by[(k, v)] if lo <= r <= hi)
            row['v_dmg_any'] = sum(a for (aa, t), L in dmg_by.items() if aa == v for r, a, _, _ in L if lo <= r <= hi)
            row['others_dmg_to_v'] = sum(a for (aa, t), L in dmg_by.items() if t == v and aa != k for r, a, _, _ in L if lo <= r <= hi)
            row['k_stuns_v'] = len([r for r in stun_by[(k, v)] if lo <= r <= hi])
            row['v_stuns_k'] = len([r for r in stun_by[(v, k)] if lo <= r <= hi])
            row['v_recall_K'] = row['v_br_window'].count('K') + row['v_br_window'].count('k')
            row['v_recall_hit'] = len([c for c in rcancel if c['a'] == v and lo - 5 <= c['r'] <= hi and c['cause'] in ('damage', 'stun')
                                       and c.get('left', 5) < 4])
            row['v_recall_hit_any'] = len([c for c in rcancel if c['a'] == v and lo <= c['r'] <= hi and c['cause'] in ('damage', 'stun')])
            row['v_tribute_cancel'] = [c.get('cause') for c in tcancel if c['a'] == v and lo - 5 <= c['r'] <= hi]
            # the kill in hand: the victim's ready spells and basic at its last turns against the killer's health then
            def unspent(j):
                c = G.ch[v]
                f, st_ = c['foc'][max(0, j - 1)], c['str'][max(0, j - 1)]
                return (1.5 * f if ready(G, v, j, 0) else 0) + (1.0 * f if ready(G, v, j, 1) else 0) + st_
            row['v_unspent_death'] = unspent(id_)
            row['k_hp_pre'] = G.ch[k]['hp'][pre]
            row['v_unspent_pre'] = unspent(pre)
            row['k_hp_pre2'] = G.ch[k]['hp'][max(0, pre - 1)]
            # retreat turns that walked in the killer's cast reach with a spell ready (a Prism's spells exclude walking)
            # a virtual cast on each such turn, one a turn, each slot again 8 rounds after (its own or a real cast)
            forgone, fdmg, r_in_reach = 0, 0.0, 0
            nxt = [0, 0]
            for j in range(w0 + 1, id_ + 1):
                bj = (G.branch(v, j) or ('.',))[0]
                if not (G.alive(v, j) and G.alive(v, j - 1) and G.alive(k, j - 1)):
                    continue
                for sl in (0, 1):
                    if not ready(G, v, j, sl):
                        nxt[sl] = max(nxt[sl], j + G.ch[v]['cd%d' % sl][j - 1])
                dprev = G.dist(v, k, j - 1)
                if bj == 'R' and dprev <= PRISM_RANGE + 1:
                    r_in_reach += 1
                    if G.pos(v, j) != G.pos(v, j - 1):
                        for sl, mult in ((0, 1.5), (1, 1.0)):
                            if nxt[sl] <= j:
                                forgone += 1
                                fdmg += mult * G.ch[v]['foc'][j - 1]
                                nxt[sl] = j + 8
                                break
            row['r_in_reach'] = r_in_reach
            row['r_forgone'] = forgone
            row['r_forgone_dmg'] = fdmg
            row['k_score_pre'] = sum(e2['gems'] for e2 in tribs if e2['k'] == 'tribute_end' and G.team[e2['a']] == G.team[k] and e2['r'] < e_r)
            row['v_score_pre'] = sum(e2['gems'] for e2 in tribs if e2['k'] == 'tribute_end' and G.team[e2['a']] == G.team[v] and e2['r'] < e_r)
            row['k_chan_pre'] = G.ch[k]['chan'][pre]
            row['k_gems_pre'] = G.ch[k]['gems'][pre]
            row['k_tcancel_window'] = [(c['r'], c.get('cause'), c.get('gems')) for c in tcancel if c['a'] == k and lo - 1 <= c['r'] <= hi]
            row['v_team_won'] = G.team[v] == G.winner
            row['rounds_to_end'] = T - id_
            row['k_trib_after'] = [(e['r'], e['gems']) for e in tribs if e['a'] == k and e['k'] == 'tribute_end' and e['r'] > e_r][:1]
        rows['death'].append(row)

    if not both:
        rows['game'].append(dict(base, dom=None))
        return rows
    pa, pb = G.prisms

    # ---------------- encounters ----------------
    last = -100
    for i in range(T):
        if not (G.alive(pa, i) and G.alive(pb, i)):
            continue
        d = G.dist(pa, pb, i)
        if d > 6:
            continue
        if i - last > 20:
            j = max(0, i - 1)
            pr = G.power(pa, j) / max(1, G.power(pb, j))
            s, w = (pa, pb) if pr >= 1 else (pb, pa)
            ratio = max(pr, 1 / max(pr, 1e-9))
            fr = G.ch[s]['foc'][j] / max(1, G.ch[w]['foc'][j])
            # who closed: each Prism's own step against the other's last tile, over the 10 rounds before
            cs = cw = 0
            for q in range(max(1, i - 9), i + 1):
                if not all(G.alive(c, q) and G.alive(c, q - 1) for c in (s, w)):
                    continue
                sx, sy = G.pos(s, q); sx0, sy0 = G.pos(s, q - 1)
                wx, wy = G.pos(w, q); wx0, wy0 = G.pos(w, q - 1)
                cs += cheb(sx, sy, wx0, wy0) - cheb(sx0, sy0, wx0, wy0)
                cw += cheb(wx, wy, sx0, sy0) - cheb(wx0, wy0, sx0, sy0)
            d10 = G.dist(s, w, max(0, i - 10)) if G.alive(s, max(0, i - 10)) and G.alive(w, max(0, i - 10)) else None
            out, by = 'none', None
            for q in range(i + 1, min(T, i + 21)):
                if not G.alive(w, q):
                    out = 'weak_died'; break
                if not G.alive(s, q):
                    out = 'strong_died'; break
            if out != 'none':
                vic = w if out == 'weak_died' else s
                for e in deaths:
                    if e['v'] == vic and i + 1 <= e['r'] <= i + 22:
                        by = e.get('by'); break
            bw = G.branch(w, i) or ('.', -1, -1)
            bs = G.branch(s, i) or ('.', -1, -1)
            wfg = bw[1]
            tiles = G.group_tiles(wfg)
            sx, sy = G.pos(s, i)
            wx, wy = G.pos(w, i)
            fg_d = min((cheb(sx, sy, x, y) for x, y in tiles), default=None)
            wfg_side = G.mp['groups'][wfg]['side'] if 0 <= wfg < len(G.mp['groups']) else None
            seen_w = any(G.sees(w, s, q) for q in range(max(0, i - 10), i))
            seen_s = any(G.sees(s, w, q) for q in range(max(0, i - 10), i))
            rows['enc'].append(dict(base, r=i + 1, ratio=ratio, fr=fr, s=s, w=w, steam=G.team[s], d=d, d10=d10, cs=cs, cw=cw,
                                    out=out, by=by, bw=bstr(G, w, max(0, i - 10), i + 1), bs=bstr(G, s, max(0, i - 10), i + 1),
                                    wfg=wfg, wclaim=bw[2], sfg=bs[1], fg_d=fg_d,
                                    wfg_side=None if wfg_side is None else ('own' if wfg_side == G.team[w] else 'mid' if wfg_side == -1 else 'enemy'),
                                    w_sees=G.sees(w, s, i), s_sees=G.sees(s, w, i), w_seen10=seen_w, s_seen10=seen_s,
                                    w_hpf=G.ch[w]['hp'][j] / max(1, G.ch[w]['maxHp'][j]), s_hpf=G.ch[s]['hp'][j] / max(1, G.ch[s]['maxHp'][j]),
                                    w_gems=G.ch[w]['gems'][j], s_gems=G.ch[s]['gems'][j],
                                    w_own=G.own_ground(G.team[w], wx, wy), s_own=G.own_ground(G.team[s], sx, sy),
                                    w_spawn=G.steps(G.team[w], wx, wy), s_spawn=G.steps(G.team[s], sx, sy),
                                    w_ally=G.nearest(w, G.allies(w), i), s_ally=G.nearest(s, G.allies(s), i),
                                    w_burst=burst2(G, w, i), s_burst=burst2(G, s, i), w_hp=G.ch[w]['hp'][j], s_hp=G.ch[s]['hp'][j]))
        last = i

    # ---------------- dominance ----------------
    onset = None
    for i in range(T):
        if G.alive(pa, i) and G.alive(pb, i):
            fa, fb = G.ch[pa]['foc'][i], G.ch[pb]['foc'][i]
            if max(fa / fb, fb / fa) >= 2:
                onset = i
                break
    bd = collections.defaultdict(dict)  # (round, observer) -> record of the enemy Prism
    for rec in G.g['BD']:
        t, rnd, obs, eid, alive, vis, tracked, x, y, prnd, src, cnt = rec
        bd[(rnd, obs)] = dict(alive=alive, vis=vis, tracked=tracked, x=x, y=y, prnd=prnd, src=src, cnt=cnt, eid=eid)
    for s, w in ((pa, pb), (pb, pa)):
        br = collections.Counter()
        br_seen = collections.Counter()
        br_seen_near = collections.Counter()
        seen = seen10 = rounds = 0
        dists = []
        know = collections.Counter()
        gate = collections.Counter()
        seen_d, seen_hit, seen_got, nohit_br = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
        phase = collections.Counter()
        chases = []
        cur = None
        for i in range(T):
            if not (G.alive(s, i) and G.alive(w, i)):
                if cur:
                    cur['end'] = 'weak_died' if not G.alive(w, i) and G.alive(s, i) else 'strong_died' if not G.alive(s, i) else 'both'
                    cur['end_r'] = i + 1
                    chases.append(cur); cur = None
                continue
            fs, fw = G.ch[s]['foc'][i], G.ch[w]['foc'][i]
            if fs < 2 * fw:
                if cur:
                    cur['end'] = 'not_dominant'; cur['end_r'] = i + 1; chases.append(cur); cur = None
                continue
            rounds += 1
            b = (G.branch(s, i) or ('.',))[0]
            # the endgame: the dominant Prism's bag wins with its team's score (keeps_gems lets go)
            ph = 'win' if G.ch[s]['gems'][i] + score_at(G.team[s], i + 1) >= 1000 else 'mid'
            br[b] += 1
            phase[(ph, b)] += 1
            d = G.dist(s, w, i)
            dists.append(d)
            sees = G.sees(s, w, i)
            if sees:
                seen += 1
                br_seen[b] += 1
                hit = (i + 1) in hit_rounds[(s, w)]
                got = (i + 1) in hit_rounds[(w, s)]
                db = 'd<=4' if d <= 4 else 'd5-6' if d <= 6 else 'd7-8' if d <= 8 else 'd>8'
                seen_d[(ph, db)] += 1
                seen_hit[(ph, db)] += hit
                seen_got[(ph, db)] += got
                if not hit:
                    nohit_br[(ph, db, b)] += 1
                if d <= 6:
                    br_seen_near[b] += 1
                # why not chasing: preyable's tests
                if b != 'C' and (i + 1) not in hit_rounds[(s, w)]:
                    wx, wy = G.pos(w, i)
                    sx, sy = G.pos(s, i)
                    st = G.team[s]
                    hp_ok = G.ch[w]['hp'][i] >= HURT * G.ch[w]['maxHp'][i]
                    on_ours = G.own_ground(st, wx, wy)
                    near_spawn = rect_dist(wx, wy, G.mp['spawn'][G.team[w]]) <= 1
                    if d > 8:
                        gate[(ph, 'd>8')] += 1
                    elif near_spawn:
                        gate[(ph, 'near_enemy_spawn')] += 1
                    elif d > 3 and not on_ours and hp_ok and G.ch[w]['gems'][i] == 0:
                        gate[(ph, 'their_ground_healthy_nobag')] += 1
                    elif d > 3 and not on_ours and hp_ok:
                        gate[(ph, 'their_ground_healthy_bag')] += 1
                    else:
                        gate[(ph, 'preyable_by_ground')] += 1
                    gate[(ph, 'branch_' + b)] += 1
            if any(G.sees(s, w, q) for q in range(max(0, i - 10), i + 1)):
                seen10 += 1
            rec = bd.get((i + 1, s))
            if rec is not None:
                if not rec['alive']:
                    know['bd_thinks_dead'] += 1
                elif rec['vis']:
                    know['bd_visible'] += 1
                elif not rec['tracked'] or rec['cnt'] < 0:
                    know['bd_untracked'] += 1
                else:
                    c = rec['cnt']
                    know['bd_cnt<=9' if c <= 9 else 'bd_cnt<=49' if c <= 49 else 'bd_cnt<=200' if c <= 200 else 'bd_cnt>200'] += 1
                    wx, wy = G.pos(w, i)
                    err = cheb(rec['x'], rec['y'], wx, wy)
                    know['bd_err<=2' if err <= 2 else 'bd_err<=6' if err <= 6 else 'bd_err>6'] += 1
                know['bd_n'] += 1
            # engagement episodes: the dominant Prism sees the weak one and chases (C) or strikes (A)
            engaged = sees and (b == 'C' or (i + 1) in hit_rounds[(s, w)])
            if engaged:
                if cur is None:
                    cur = dict(base, s=s, w=w, r0=i + 1, n=0, br='', d0=d, w_hpf0=G.ch[w]['hp'][i] / G.ch[w]['maxHp'][i],
                               s_hpf0=G.ch[s]['hp'][i] / G.ch[s]['maxHp'][i], dmg=0, fr=fs / fw)
                cur['n'] += 1
                cur['br'] += b
                cur['hits'] = cur.get('hits', 0) + ((i + 1) in hit_rounds[(s, w)])
            elif cur is not None:
                cur['end_r'] = i + 1
                cur['end_br'] = b
                cur['end_d'] = d
                cur['end_s_hpf'] = G.ch[s]['hp'][i] / G.ch[s]['maxHp'][i]
                cur['end_w_hpf'] = G.ch[w]['hp'][i] / G.ch[w]['maxHp'][i]
                cur['end_sees'] = sees
                ex = [e for e in G.enemies(s) if e != w and G.alive(e, i)]
                cur['end_enemy_near'] = sum(1 for e in ex if G.dist(s, e, i) <= 6)
                cur['end_ally_near'] = sum(1 for a in G.allies(s) if G.alive(a, i) and G.dist(s, a, i) <= 6)
                wx, wy = G.pos(w, i)
                cur['end_w_own'] = G.own_ground(G.team[w], wx, wy)
                cur['end_w_ours'] = G.own_ground(G.team[s], wx, wy)
                cur['end_w_spawn'] = G.steps(G.team[w], wx, wy)
                cur['end_w_gems'] = G.ch[w]['gems'][i]
                cur['end_w_chan'] = G.ch[w]['chan'][i]
                if not sees:
                    cur['end'] = 'lost_sight'
                elif b == 'R':
                    cur['end'] = 'retreat'
                else:
                    cur['end'] = 'gate'
                chases.append(cur)
                cur = None
            if cur is not None:
                cur['dmg'] += sum(a for r, a, _, _ in dmg_by[(s, w)] if r == i + 1)
        if cur:
            cur['end'] = 'game_end'; cur['end_r'] = T; chases.append(cur)
        for c in chases:
            c['killed'] = any(e['v'] == w and c['r0'] <= e['r'] <= c.get('end_r', T) + 3 and e.get('by') == s for e in deaths)
            c['w_died_30'] = any(e['v'] == w and c['r0'] <= e['r'] <= c.get('end_r', T) + 30 for e in deaths)
            c['dmg_total'] = sum(a for r, a, _, _ in dmg_by[(s, w)] if c['r0'] <= r <= c.get('end_r', T))
        if rounds:
            rows['dom'].append(dict(base, s=s, w=w, steam=G.team[s], rounds=rounds, br=dict(br), br_seen=dict(br_seen),
                                    br_seen_near=dict(br_seen_near), seen=seen, seen10=seen10, seen_d=dict(seen_d),
                                    seen_hit=dict(seen_hit), phase=dict(phase), seen_got=dict(seen_got), nohit_br=dict(nohit_br),
                                    dist_med=sorted(dists)[len(dists) // 2], know=dict(know), gate=dict(gate),
                                    kills=sum(1 for e in deaths if e['v'] == w and e.get('by') == s and
                                              G.alive(s, e['r'] - 2) and G.ch[s]['foc'][e['r'] - 2] >= 2 * G.ch[w]['foc'][e['r'] - 2]),
                                    bd_team=any(True for (rr, o) in bd if o == s)))
            rows['chase'] += chases

    # ---------------- game-level (dominance onset and the loss) ----------------
    gr = dict(base, dom=None)
    if onset is not None:
        i = onset
        s, w = (pa, pb) if G.ch[pa]['foc'][i] > G.ch[pb]['foc'][i] else (pb, pa)
        st = G.team[s]
        gr.update(dom=onset + 1, s=s, w=w, steam=st, won=(st == G.winner))
        sd = [e for e in deaths if e['v'] == s and e['r'] > onset + 1]
        gr['s_deaths'] = [(e['r'], G.names.get(e.get('by')) if e.get('by') is not None else 'camp', e.get('gems', 0),
                           e.get('by') == w) for e in sd]
        wd = [e for e in deaths if e['v'] == w and e['r'] > onset + 1]
        gr['w_deaths'] = [(e['r'], G.names.get(e.get('by')) if e.get('by') is not None else 'camp', e.get('gems', 0),
                           e.get('by') == s) for e in wd]
        # the strong Prism's bag at the end, and its tributes
        last_alive = max((q for q in range(T) if G.alive(s, q)), default=T - 1)
        gr['s_bag_end'] = G.ch[s]['gems'][last_alive]
        gr['s_alive_end'] = G.alive(s, T - 1)
        gr['s_bag_max'] = max(G.ch[s]['gems'][onset:T])
        gr['s_bag_at_onset'] = G.ch[s]['gems'][onset]
        gr['s_tributed'] = sum(e['gems'] for e in G.g['ev'] if e['k'] == 'tribute_end' and e['a'] == s and e['r'] > onset)
        gr['s_tcancel'] = [(c['r'], c.get('cause'), c.get('gems'), c.get('left')) for c in tcancel if c['a'] == s and c['r'] > onset]
        gr['team_tcancel'] = [(c['r'], c['a'], c.get('cause'), c.get('gems'), c.get('left')) for c in tcancel
                              if G.team[c['a']] == st and c['r'] > onset]
        gr['s_tstart'] = [(e['r'], e['gems'], e.get('dur')) for e in G.g['ev'] if e['k'] == 'tribute_start' and e['a'] == s and e['r'] > onset]
        gr['gems_us'] = res['gems'][st]
        gr['gems_them'] = res['gems'][1 - st]
        gr['round_limit'] = T >= 2000
        # team bags at the end (gems carried by each team's champions alive at the end)
        gr['bag_us_end'] = sum(G.ch[c]['gems'][T - 1] for c in G.ch if G.team[c] == st and G.alive(c, T - 1))
        gr['bag_them_end'] = sum(G.ch[c]['gems'][T - 1] for c in G.ch if G.team[c] != st and G.alive(c, T - 1))
        gr['s_foc_onset'] = G.ch[s]['foc'][onset]
        gr['w_foc_onset'] = G.ch[w]['foc'][onset]
        # team scores over time (tribute_end totals), for the cancels and the onset's cause
        tl = [(e['r'], G.team[e['a']], e['gems']) for e in G.g['ev'] if e['k'] == 'tribute_end']

        def score(team, r):
            return sum(gm for rr, t, gm in tl if t == team and rr < r)
        gr['s_tcancel_ctx'] = [(c['r'], c.get('cause'), c.get('gems'), c.get('left'), score(st, c['r']), score(1 - st, c['r']))
                               for c in tcancel if c['a'] == s and c['r'] > onset]
        gr['w_trib_at_onset'] = any(e['k'] == 'tribute_end' and e['a'] == w and onset - 2 <= e['r'] <= onset + 1 for e in G.g['ev'])
        gr['end_gap'] = T - (onset + 1)
        # a sustained onset: the ratio held 10 rounds in a row, both alive
        run, sus = 0, None
        for q in range(T):
            if G.alive(pa, q) and G.alive(pb, q):
                fa, fb = G.ch[pa]['foc'][q], G.ch[pb]['foc'][q]
                ok = G.ch[s]['foc'][q] >= 2 * G.ch[w]['foc'][q]
                run = run + 1 if ok else 0
                if run >= 10:
                    sus = q - 9
                    break
            else:
                run = 0
        gr['sus'] = None if sus is None else sus + 1
        # enemy (weak team) score race: rounds the weak team's last tribute landed before the end
        gr['them_last_trib'] = max((rr for rr, t, gm in tl if t != st), default=None)
        gr['dom_branch'] = collections.Counter((G.branch(s, q) or ('.',))[0] for q in range(onset, T) if G.alive(s, q))
        # gem flows after onset: captures by team, kills' gems
        cap = [0, 0]
        for e in G.g['ev']:
            if e['k'] == 'capture' and e['r'] > onset:
                for sh in e.get('shares', ()):
                    cap[G.team[sh[0]]] += sh[1]
        gr['cap_us'] = cap[st]
        gr['cap_them'] = cap[1 - st]
        trib = [0, 0]
        for e in G.g['ev']:
            if e['k'] == 'tribute_end' and e['r'] > onset:
                trib[G.team[e['a']]] += e['gems']
        gr['trib_us'] = trib[st]
        gr['trib_them'] = trib[1 - st]
        # strong Prism's carried gem fraction of our total (score + bags) at each 100 rounds after onset
        # enemy score at onset vs ours
        tr0 = [0, 0]
        for e in G.g['ev']:
            if e['k'] == 'tribute_end' and e['r'] <= onset + 1:
                tr0[G.team[e['a']]] += e['gems']
        gr['score_us_onset'] = tr0[st]
        gr['score_them_onset'] = tr0[1 - st]
        # the bag the strong Prism held when the enemy's winning tribute landed / at the end
        gr['s_hpfrac_end'] = G.ch[s]['hp'][last_alive] / max(1, G.ch[s]['maxHp'][last_alive])
        # rounds the strong Prism spent dead after onset
        gr['s_dead_rounds'] = sum(1 for q in range(onset, T) if not G.alive(s, q))
        gr['w_dead_rounds'] = sum(1 for q in range(onset, T) if not G.alive(w, q))
        # last time dominance held
        gr['dom_rounds'] = sum(1 for q in range(onset, T) if G.alive(s, q) and G.alive(w, q) and
                               G.ch[s]['foc'][q] >= 2 * G.ch[w]['foc'][q])
        gr['rev_rounds'] = sum(1 for q in range(onset, T) if G.alive(s, q) and G.alive(w, q) and
                               G.ch[w]['foc'][q] >= 2 * G.ch[s]['foc'][q])
    rows['game'].append(gr)
    return rows


if __name__ == '__main__':
    procs = int(sys.argv[sys.argv.index('--procs') + 1]) if '--procs' in sys.argv else 16
    out = collections.defaultdict(list)
    with Pool(procs) as p:
        for rows in p.imap_unordered(analyse, files(), chunksize=4):
            for k, v in rows.items():
                out[k] += v
    pickle.dump(dict(out), open(os.path.join(CACHE, 'rows.pkl'), 'wb'))
    print({k: len(v) for k, v in out.items()})
