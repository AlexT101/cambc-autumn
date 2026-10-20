"""Fish-likeness scorecard: behaviour metrics from research/FISH-BOT.md for one team and its opponents in the same games.

  py tools/koi/scorecard.py replays/koi-ab/lat100-ladder replays/koi-ab/lat100-gen --team koi
  py tools/koi/scorecard.py "replays/koi-ab/lat100-*" --team koi --json out.json
  py tools/koi/scorecard.py --fish [--refresh]

Sources are replay dirs or files (globs allowed) or analysis dir names, extracted first with
`node tools/replay/extract.mjs <dir>`. --team matches a substring of the team or bot name (case-insensitive),
read from index.json rows of the given sources; games where both or neither team match are skipped.
--fish plays Intercontinental Fish's 459 ranked games of replay-bulk/2026-10-18 and caches the result in
replays/.analysis/reports/fish-scorecard.json (--refresh recomputes). Other runs add those cached Fish
columns for comparison.

Definitions follow the analysis behind FISH-BOT.md. Approximations:
- freed tile: groups with 2+ clusters and a Wolf/Elk pooled, plus E+2G+W alone (FISH-BOT's 90%/64%); single-cluster
  groups are left out, as their only freed tile is often the last camp's.
- crews: wolf = monsters all Wolves, elk = any Elk (no Monolith); FISH-BOT gives per-label ranges.
- kills taken: a turn's kill chance is judged at the first event at or after its turn slot; damage ignores
  Durability; the basic-only variant uses the same moment (not the actor's own first event).
- recalls: only those still channelling after their owner's next turn count (hecate-style bots start one at
  every turn end and cancel it next turn); 'Recall starts per game, all' counts every start. FISH-BOT.md counted
  all starts, so its cancel figures include quick cancels.
- combat retreat hp: median hp at recall start with an enemy visible and no gems (the engage-rule fit is not done).
"""
import argparse, collections, glob, json, os, statistics, sys
from collections import deque
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / 'replay'))
sys.path.insert(0, str(HERE))
from analysis.data import Game, load_index, ANALYSIS, ROOT, chebyshev as cheb  # noqa: E402
from state import walk, turn_order, max_damage  # noqa: E402

VERSION = 2
FISH = 'Intercontinental Fish'
FISH_CACHE = ANALYSIS / 'reports' / 'fish-scorecard.json'
RANGED = {'Stellar', 'Cassi', 'Prism', 'Tavi', 'Willow', 'Vesper Vale'}
CLUSTERS = ('Gem cluster', 'Gold cluster')
MONSTERS = ('Wolf', 'Elk', 'Monolith')
STUNS = {('Ren', 'CC'), ('Cassi', 'CC'), ('Tavi', 'CC'), ('Prism', 'CC'), ('Ryth', 'AoE damage')}


def bfs(m, srcs):
    blocked = m.walls | m.holes | set(m.altars)
    dist = {s: 0 for s in srcs}; dq = deque(srcs)
    while dq:
        x, y = dq.popleft(); d = dist[(x, y)] + 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if (dx or dy) and 0 <= n[0] < m.W and 0 <= n[1] < m.H and n not in blocked and n not in dist:
                    dist[n] = d; dq.append(n)
    return dist


def spawn_fields(m):
    return [bfs(m, [(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)])
            for s in m.spawn]


def process(d):
    g = Game(d)
    m = g.map
    C = [collections.Counter(), collections.Counter()]
    L = [collections.defaultdict(list), collections.defaultdict(list)]
    tm = g.team_of; nm = g.name_of
    chs = {c['id']: g.ch(c['id']) for c in g.champs}
    nR = len(g.rounds['round'])
    groups = {gr['id']: gr for gr in m.groups}
    camp_pos = {c['id']: (c['x'], c['y']) for c in m.camps}
    camp_type = {c['id']: c['type'] for c in m.camps}
    camp_group = {c['id']: c['group'] for c in m.camps}
    gtiles = {gid: {tuple(t) for t in gr['tiles']} for gid, gr in groups.items()}

    def val(cid, key, r):
        a = chs[cid][key]; return a[max(0, min(len(a) - 1, r - 2))]

    def sees(cid, r):
        a = chs[cid]['sees']; i = r - 1
        return set(a[i]) if 0 <= i < len(a) and a[i] else set()

    def pos(cid, i):
        X = chs[cid]
        if i < 0 or i >= len(X['x']) or not X['alive'][i] or X['x'][i] is None: return None
        return (X['x'][i], X['y'][i])

    # totals
    for t in (0, 1):
        C[t]['games'] += 1; C[t]['wins'] += g.winner == t
        C[t]['tributed'] += g.final_gems[t]; C[t]['rounds'] += g.n_rounds
    for c in g.champs:
        t = c['team']
        C[t]['earned'] += c.get('earnedGold') or 0
        C[t]['alive'] += sum(chs[c['id']]['alive'])
        if c['name'] == 'Cassi': C[t]['cassi_alive'] += sum(chs[c['id']]['alive'])
        C[t][('champgames', c['name'])] += 1
        gm = chs[c['id']]['gems']; C[t]['carry_sum'] += sum(gm); C[t]['carry_n'] += len(gm)

    kills = {}
    deaths_of = collections.defaultdict(list)
    kept, opened, spans = set(), {}, collections.defaultdict(list)
    for e in g.events:
        k = e['k']
        if k == 'recall_start':
            opened[e['a']] = (e['s'], e['r']); C[tm[e['a']]]['rc_raw'] += 1
        elif k in ('recall_end', 'recall_cancel', 'death') and e.get('a', e.get('v')) in opened:
            a = e.get('a', e.get('v')); s0, r0 = opened.pop(a)
            if k == 'recall_end' or e['r'] > r0 + 1: kept.add(s0); spans[a].append((r0, e['r']))
    for a, (s0, r0) in opened.items(): kept.add(s0); spans[a].append((r0, 10 ** 6))
    recall_starts = {(e['a'], e['r']) for e in g.events if e['k'] == 'recall_start' and e['s'] in kept}
    for e in g.events:
        if e['k'] == 'death':
            v = e['v']; by = e.get('by')
            C[tm[v]]['deaths'] += 1
            C[tm[v]]['lost_gems'] += e.get('gems') or 0
            deaths_of[v].append((e['r'], by))
            if not e.get('linked'):
                kills[(e['r'], v)] = by
                if by in tm: C[tm[by]]['kills'] += 1

    # captures, gold recall, bag age, shops, dead shopping, killer order
    first_cap = {}; dead = {}; od_cache = {}; emblems = collections.defaultdict(list)
    for e in g.events:
        k = e['k']; r = e['r']
        if k == 'capture':
            t = e['team']
            C[t]['cap_n'] += 1; C[t]['cap1'] += len(e['shares']) == 1
            for cid, gm, gd in e['shares']:
                C[t]['gems_captured'] += gm
                if gm > 0: first_cap.setdefault(cid, r)
                if nm[cid] == 'Tavi': continue
                gold = chs[cid]['gold'][min(r - 1, len(chs[cid]['gold']) - 1)]
                b = 'lo' if gold < 120 else 'mid' if gold < 150 else 'hi'
                C[t]['gr_n_' + b] += 1
                started = any((cid, rr) in recall_starts for rr in (r, r + 1))
                C[t]['gr_' + b] += started
                C[t]['grc_' + b] += started or any(r0 < r <= r1 for r0, r1 in spans[cid])
        elif k == 'tribute_end':
            t = tm[e['a']]
            C[t]['trib_n'] += 1; C[t]['trib_gems'] += e['gems']
            if e['a'] in first_cap: L[t]['bag_age'].append(r - first_cap.pop(e['a']))
        elif k == 'death':
            v = e['v']; first_cap.pop(v, None)
            gold = chs[v]['gold'][min(r - 1, len(chs[v]['gold']) - 1)]
            dead[v] = [r, gold, None]
            by = e.get('by')
            if not e.get('linked') and by in tm:
                if r not in od_cache: od_cache[r] = turn_order(g, r, chs)
                od = od_cache[r]
                C[tm[by]]['ko_n'] += 1; C[tm[by]]['ko_first'] += od.index(by) < od.index(v)
        elif k == 'shop':
            a = e['a']; t = tm[a]
            if a in dead and dead[a][2] is None: dead[a][2] = r - dead[a][0]
            for it, n in (e.get('items') or {}).items():
                fam, rest = it.split(' ', 1)
                key = (fam, rest.split(' of ')[1])
                C[t][('shard', nm[a]) + key] += n * (5 if 'Emblem' in rest else 1)
                if 'Emblem' in rest and n > 0: emblems[a] += [' '.join(key)] * n
        elif k == 'respawn' and e['a'] in dead:
            r0, gold, sh = dead.pop(e['a'])
            if gold >= 30:
                t = tm[e['a']]; C[t]['ds_n'] += 1; C[t]['ds_shop'] += sh is not None and sh < 60

    for c in g.champs:
        C[c['team']][('order', c['name'], ', '.join(emblems[c['id']][:3]) or '-')] += 1

    # spawn exits
    for c in g.champs:
        cid = c['id']; t = c['team']; ch = chs[cid]
        for i in range(1, len(ch['x'])):
            if ch['alive'][i] and ch['alive'][i - 1] and ch['x'][i] is not None and ch['x'][i - 1] is not None:
                if m.in_spawn(t, (ch['x'][i - 1], ch['y'][i - 1])) and not m.in_spawn(t, (ch['x'][i], ch['y'][i])):
                    C[t]['exit_n'] += 1; C[t]['exit_lt30'] += ch['gold'][i - 1] < 30

    # respawn arrival
    for e in g.events:
        if e['k'] != 'group_respawn': continue
        r = e['r']; tiles = gtiles[e['g']]
        for t in (0, 1):
            for cid in g.team_ids[t]:
                def dist(i):
                    p = pos(cid, i)
                    return None if p is None else min(cheb(p, x) for x in tiles)
                now, far = dist(r - 2), dist(r - 22)
                if now is not None and now <= 3 and far is not None and far >= 12:
                    j = r - 2
                    while j > r - 22 and dist(j - 1) is not None and dist(j - 1) <= 3: j -= 1
                    C[t]['arr_n'] += 1; C[t]['arr_early'] += 1 <= (r - 1) - j <= 4

    # low-hp survival
    cd_by = collections.defaultdict(float)
    hits = collections.defaultdict(float)
    for s, r, a, v, amt, *_ in g.champ_damage:
        cd_by[(v, r)] += amt; hits[(a, v, r)] += amt
    for c in g.champs:
        cid = c['id']; t = c['team']; ch = chs[cid]; last = -999
        for i in range(1, nR):
            if i >= len(ch['alive']) or not ch['alive'][i] or not ch['alive'][i - 1]: continue
            f0 = ch['hp'][i - 1] / ch['maxHp'][i - 1]; f1 = ch['hp'][i] / ch['maxHp'][i]
            if not f1 < 0.25 <= f0: continue
            r = i + 1
            if r - last < 10: continue
            last = r
            combat = cd_by[(cid, r)] + cd_by[(cid, r - 1)] > 0
            died = any(r + 1 <= rr <= r + 30 for rr, _ in deaths_of[cid])
            C[t]['low_n'] += 1; C[t]['low_surv'] += not died
            if combat: C[t]['lowc_n'] += 1; C[t]['lowc_surv'] += not died

    # chases
    F = spawn_fields(m)
    rows = []
    for c in g.champs:
        cid = c['id']; t = c['team']; ch = chs[cid]; tf = F[1 - t]
        for r in range(3, nR + 1):
            i = r - 1
            if i >= len(ch['turn']) or ch['turn'][i] not in (1, 2) or ch['chan'][i - 1] in (2, 3, 4): continue
            p0 = pos(cid, i - 1); p1 = pos(cid, i)
            if not p0 or not p1: continue
            best = None
            for T in ch['sees'][i] or []:
                q0 = pos(T, i - 1); qm = pos(T, i - 2)
                if not q0 or not qm: continue
                dd = cheb(q0, p0)
                if dd <= 6 and dd > cheb(qm, p0) and tf.get(q0, 999) < tf.get(qm, 999):
                    if best is None or dd < best[1]: best = (T, dd, q0)
            if not best: continue
            T, dd, q0 = best
            follow = hits.get((cid, T, r), 0) > 0 or cheb(q0, p1) < dd
            killed = next((rr for rr, by in deaths_of[T] if r <= rr <= r + 10 and tm.get(by) == t), None)
            C[t]['ch_n'] += 1; C[t]['ch_follow'] += follow
            rows.append((cid, T, r, follow, killed))
    rows.sort()
    eps = []
    for row in rows:
        if eps and eps[-1][-1][:2] == row[:2] and row[2] - eps[-1][-1][2] <= 2: eps[-1].append(row)
        else: eps.append([row])
    for ep in eps:
        if sum(x[3] for x in ep) < 2: continue
        t = tm[ep[0][0]]; end = ep[-1][2]
        C[t]['chep_n'] += 1; C[t]['chep_kill'] += any(x[4] is not None and x[4] <= end + 3 for x in ep)

    # walk: camps, stuns, wakes, recalls, targets, kills, AoE
    life = {}
    def LF(gid):
        if gid not in life: life[gid] = dict(dmg=[0.0, 0.0], att=[set(), set()], nw=0, on=None)
        return life[gid]
    gr_types = {gid: set(gr['types']) for gid, gr in groups.items()}
    pending = []; attacked = set(); lastcap = {}; open_rc = {}
    cur = None; od = None; done = set()
    for e, S in walk(g):
        k = e['k']; r = e['r']; t_ = e['t']
        if r != cur:
            cur = r; od = turn_order(g, r, chs); done = set()
        if t_ >= 0:
            for slot in range(min(t_ + 1, len(od))):
                cid = od[slot]
                if cid in done: continue
                done.add(cid)
                i = r - 1; j = max(0, r - 2); ch = chs[cid]
                if i >= len(ch['turn']) or ch['turn'][i] != 1 or S.pos.get(cid) is None: continue
                vis = sees(cid, r); kl = []; kb = []
                rng = 3 if nm[cid] in RANGED else 1
                for v in g.team_ids[1 - tm[cid]]:
                    if v not in vis or not S.pos.get(v): continue
                    dist = cheb(S.pos[cid], S.pos[v]); ehp = S.hp[v] + chs[v]['shield'][j]
                    md = max_damage(nm[cid], dist, ch['str'][j], ch['foc'][j], ch['cd0'][j], ch['cd1'][j])
                    if md > 0 and ehp <= md * 0.9: kl.append(v)
                    if dist <= rng and S.hp[v] <= ch['str'][j] * 0.95: kb.append(v)
                T = tm[cid]
                if kl:
                    C[T]['kill_n'] += 1; C[T]['kill_taken'] += any(kills.get((r, v)) == cid for v in kl)
                if kb:
                    C[T]['killb_n'] += 1; C[T]['killb_taken'] += any(kills.get((r, v)) == cid for v in kb)
        if pending and t_ >= 0:
            keep = []
            for p in pending:
                if r == p[0] + 1:
                    c = p[1]
                    if S.camp_alive.get(c) and (r, c) not in attacked and any(
                            S.pos.get(x) is not None and cheb(S.pos[x], camp_pos[c]) <= 3 for x in tm):
                        C[p[2]]['stun_skip'] += 1
                elif r <= p[0]:
                    keep.append(p)
            pending = keep
        if k == 'camp_attack':
            attacked.add((r, e['camp']))
        elif k in ('attack', 'cast'):
            a = e['a']; t = tm[a]; f = tuple(e['f']); ab = e.get('ab') if k == 'cast' else 'Attack'
            for c, amt in e.get('cdmg', []):
                lf = LF(camp_group[c]); lf['dmg'][t] += amt; lf['att'][t].add(a)
            if k == 'attack' and e.get('camp') is not None and e.get('cdmg'):
                gid = camp_group[e['camp']]
                if len(groups[gid]['camps']) >= 2:
                    rng = 3 if nm[a] in RANGED else 1
                    alts = [cc for cc in groups[gid]['camps'] if S.camp_alive.get(cc) and cheb(f, camp_pos[cc]) <= rng]
                    types = {camp_type[cc] for cc in alts}
                    if len(alts) >= 2 and types & set(CLUSTERS) and types & set(MONSTERS):
                        C[t]['clu_n'] += 1; C[t]['clu_hit'] += camp_type[e['camp']] in CLUSTERS
            if k == 'cast' and (nm[a], ab) in STUNS:
                camps = {c for c, _ in e.get('cdmg', [])}
                if e.get('camp') is not None: camps.add(e['camp'])
                for c in camps:
                    if S.camp_alive.get(c) and camp_type[c] not in CLUSTERS:
                        C[t]['stun_mon'] += 1; pending.append((r, c, t))
            if k == 'cast' and nm[a] == 'Cassi' and ab == 'CC' and e.get('camp') is not None:
                C[t]['cassi_cc_camp'] += 1
            tgt = e.get('tgt')
            dmg = {v: x for v, x in e.get('dmg', []) if v in tm}
            if k == 'attack' and tgt in tm and tm[tgt] != t and (dmg or e.get('stun')):
                rng = 3 if nm[a] in RANGED else 1
                vis = sees(a, r) | {tgt}; p = S.pos[a]
                cands = [(v, S.hp[v] + val(v, 'shield', r)) for v in g.team_ids[1 - t]
                         if S.alive.get(v) and S.pos.get(v) and v in vis and cheb(p, S.pos[v]) <= rng]
                sc = [x[1] for x in cands]
                if len(cands) >= 2 and tgt in {x[0] for x in cands} and len(set(sc)) > 1:
                    B = [v for v, s in cands if s == min(sc)]
                    C[t]['bt_n'] += 1; C[t]['bt_hit'] += tgt in B; C[t]['bt_rand'] += len(B) / len(sc)
            if k == 'cast' and ab == 'AoE damage' and dmg:
                vs = sees(a, r)
                vpos = [S.pos[v] for v in g.team_ids[1 - t] if S.pos.get(v) and v in vs]
                best = max((sum(1 for q in vpos if cheb(q, (f[0] + dx, f[1] + dy)) <= 1)
                            for dx in range(-4, 5) for dy in range(-4, 5)), default=0)
                if best >= 2:
                    C[t]['aoe_n'] += 1; C[t]['aoe_hit'] += sum(1 for v in dmg if v in vs and tm[v] != t) >= 2
        elif k == 'group_wake':
            gid = e['g']; by = e.get('by'); lf = LF(gid); n = lf['nw']; lf['nw'] += 1
            if n == 0 and by in tm and 'Monolith' not in gr_types[gid] and S.pos.get(by):
                cps = [camp_pos[c] for c in groups[gid]['camps']]
                dw = min(cheb(S.pos[by], q) for q in cps)
                ep = pos(by, r - 1)
                t = tm[by]; C[t]['wake_n'] += 1; C[t]['wake_far'] += dw >= 4
                C[t]['wake_out'] += ep is not None and min(cheb(ep, q) for q in cps) >= 4
        elif k == 'group_clear':
            lf = LF(e['g'])
            lf['on'] = {tm[c] for c in tm if S.pos.get(c) in gtiles[e['g']]}
        elif k == 'capture':
            gid = e['g']; t = e['team']
            for cid, gm, gd in e['shares']: lastcap[cid] = r
            lf = life.pop(gid, None)
            tot = sum(lf['dmg']) if lf else 0
            if lf and lf['nw'] and tot > 0 and lf['dmg'][t] / tot >= 0.9:
                ty = gr_types[gid]
                if 'Monolith' not in ty:
                    ncl = sum(camp_type[c] in CLUSTERS for c in groups[gid]['camps'])
                    if ncl >= 2 and ty & {'Wolf', 'Elk'} and lf['on'] is not None:
                        lab = sorted(camp_type[c] for c in groups[gid]['camps'])
                        keys = {'free_'} | ({'free_egw_'} if lab == ['Elk', 'Gem cluster', 'Gem cluster', 'Wolf'] else set())
                        for kk in keys:
                            C[t][kk + 'n'] += 1; C[t][kk + 'hit'] += t in lf['on']
                    crew = len(lf['att'][t])
                    if 'Elk' in ty: C[t]['crew_e_n'] += 1; C[t]['crew_e'] += crew
                    elif 'Wolf' in ty: C[t]['crew_w_n'] += 1; C[t]['crew_w'] += crew
        elif k == 'group_respawn':
            life.pop(e['g'], None)
        elif k == 'recall_start':
            a = e['a']; t = tm[a]; ch = chs[a]; ps = ('raw_', 'rc_') if e['s'] in kept else ('raw_',)
            hpf = S.hp[a] / ch['maxHp'][min(r - 1, len(ch['maxHp']) - 1)]
            aftercap = r - lastcap.get(a, -99) <= 1
            gold = ch['gold'][max(0, r - 2)]
            seen4 = any(ch['sees'][jj] for jj in range(max(0, r - 4), min(r, len(ch['sees']))))
            vis = sees(a, r)
            visd = [cheb(S.pos[x], S.pos[a]) for x in vis if S.pos.get(x) and S.pos.get(a)]
            for p in ps:
                C[t][p + 'n'] += 1
                C[t][p + 'novis'] += not vis
                C[t][p + 'vis5'] += bool(visd) and min(visd) <= 5
                if not aftercap:
                    b = int(hpf * 40)
                    C[t][p + 'hp275'] += b == 11; C[t][p + 'hp300'] += b == 12
                    C[t][p + 'aimless'] += hpf >= 0.30 and not seen4 and e['gems'] == 0 and gold < 120
            if vis and e['gems'] == 0 and len(ps) == 2: L[t]['rc_hp_vis'].append(hpf)
            open_rc[a] = (not vis, ps)
        elif k in ('recall_end', 'recall_cancel') and e['a'] in open_rc:
            t = tm[e['a']]; nv, ps = open_rc.pop(e['a'])
            for p in ps:
                if k == 'recall_end':
                    C[t][p + 'done'] += 1; C[t][p + 'novis_done'] += nv
                else:
                    C[t][p + 'cancel'] += 1; C[t][p + 'manual'] += e.get('cause') == 'manual'
        elif k == 'death':
            open_rc.pop(e['v'], None)
    return d, [dict(c) for c in C], [dict(x) for x in L]


def keystr(k):
    return '|'.join(map(str, k)) if isinstance(k, tuple) else k


def merge(acc, c, l):
    for k, v in c.items(): acc['c'][keystr(k)] = acc['c'].get(keystr(k), 0) + v
    for k, v in l.items(): acc['l'].setdefault(k, []).extend(v)


def run(jobs, threads):
    acc = {'sel': {'c': {}, 'l': {}}, 'opp': {'c': {}, 'l': {}}}
    side = dict(jobs)
    with Pool(threads) as p:
        for n, (d, C, L) in enumerate(p.imap_unordered(process, list(side), chunksize=2), 1):
            t = side[d]
            merge(acc['sel'], C[t], L[t]); merge(acc['opp'], C[1 - t], L[1 - t])
            if n % 50 == 0: print(f'  {n}/{len(side)} games', file=sys.stderr)
    return acc


M = [  # (section, label, kind, keys, FISH-BOT.md (Fish / opponents))
    ('Totals', 'Games / win rate', 'rate', ('wins', 'games'), '459 / Fish 64%'),
    ('Totals', 'Gems captured per game', 'pergame', 'gems_captured', ''),
    ('Totals', 'Gems tributed per game', 'pergame', 'tributed', ''),
    ('Totals', 'Body deaths per game', 'pergame', 'deaths', ''),
    ('Totals', 'Kills per game (C&I pair = 1)', 'pergame', 'kills', ''),
    ('Totals', 'Gold earned per game', 'pergame', 'earned', ''),
    ('Totals', 'Rounds per game', 'pergame', 'rounds', ''),
    ('Camps', 'Basic attack on the cluster, cluster + monster in range', 'rate', ('clu_hit', 'clu_n'), '95% / 16%'),
    ('Camps', 'Body on a freed tile when a group with 2+ clusters and a monster clears', 'rate', ('free_hit', 'free_n'), ''),
    ('Camps', '... E+2G+W groups only', 'rate', ('free_egw_hit', 'free_egw_n'), '90% / 64%'),
    ('Camps', 'First wakes from distance >= 4', 'rate', ('wake_far', 'wake_n'), '37% / 18%'),
    ('Camps', 'First waker ends its turn out of reach', 'rate', ('wake_out', 'wake_n'), '37% / 17%'),
    ('Camps', 'Camp attacks cancelled by stuns, per 100 alive body-rounds', 'per100', ('stun_skip', 'alive'), '19.4k / 11.0k total'),
    ('Camps', 'Camp attacks cancelled by stuns, per game', 'pergame', 'stun_skip', '42 / 24'),
    ('Camps', 'Stuns on monsters per 100 alive body-rounds', 'per100', ('stun_mon', 'alive'), ''),
    ('Camps', 'Cassi stuns on camps per 100 Cassi alive rounds', 'per100', ('cassi_cc_camp', 'cassi_alive'), '4.3 / 1.4'),
    ('Camps', 'Crew on wolf groups (attackers per held life)', 'mean', ('crew_w', 'crew_w_n'), '1.8-2.8 / 1.6-1.9'),
    ('Camps', 'Crew on elk groups', 'mean', ('crew_e', 'crew_e_n'), '3.0-4.1 / 2.0-3.0'),
    ('Camps', 'Far bodies arriving 1-4 rounds before a respawn', 'rate', ('arr_early', 'arr_n'), '86% / 55%'),
    ('Camps', 'Captures paying a single share', 'rate', ('cap1', 'cap_n'), '98% / -'),
    ('Recalls', 'Recall starts per game, all', 'pergame', 'rc_raw', ''),
    ('Recalls', 'Recall starts kept past the next turn (the rest are turn-end pre-starts)', 'rate', ('rc_n', 'rc_raw'), ''),
    ('Recalls', 'Recall within a round of a payout to >= 150 gold', 'rate', ('gr_hi', 'gr_n_hi'), '83% / 19%'),
    ('Recalls', '... or already recalling at the payout (>= 150 gold)', 'rate', ('grc_hi', 'gr_n_hi'), ''),
    ('Recalls', '... payout to 120-149 gold', 'rate', ('gr_mid', 'gr_n_mid'), '42-45% / 3%'),
    ('Recalls', '... payout to < 120 gold', 'rate', ('gr_lo', 'gr_n_lo'), '1% / 1%'),
    ('Recalls', '... or already recalling at the payout (< 120 gold)', 'rate', ('grc_lo', 'gr_n_lo'), ''),
    ('Recalls', 'Non-payout recalls at 27.5-30% vs 30-32.5% hp', 'pair', ('rc_hp275', 'rc_hp300'), '1036 vs 243 / -'),
    ('Recalls', 'Aimless recalls (hp >= 30%, no gems, gold < 120, no enemy seen 4 rounds)', 'count', ('rc_aimless', 'rc_n'), ''),
    ('Recalls', 'Recalls started with no enemy visible', 'rate', ('rc_novis', 'rc_n'), '77% / -'),
    ('Recalls', 'Recalls started with a visible enemy within 5', 'rate', ('rc_vis5', 'rc_n'), '2% / -'),
    ('Recalls', 'Completion, no enemy visible', 'rate', ('rc_novis_done', 'rc_novis'), ''),
    ('Recalls', 'Completion, all recalls', 'rate', ('rc_done', 'rc_n'), ''),
    ('Recalls', 'Cancelled (any cause)', 'rate', ('rc_cancel', 'rc_n'), ''),
    ('Recalls', 'Self-cancelled', 'rate', ('rc_manual', 'rc_n'), '444 (3%) / -'),
    ('Recalls', 'All starts: aimless', 'count', ('raw_aimless', 'raw_n'), '185 (1%) / 8243 (41%)'),
    ('Recalls', 'All starts: completion, no enemy visible', 'rate', ('raw_novis_done', 'raw_novis'), '93% / 60%'),
    ('Recalls', 'All starts: cancelled (any cause)', 'rate', ('raw_cancel', 'raw_n'), '7% / 41%'),
    ('Recalls', 'Median hp at recall start, enemy visible, no gems', 'median', 'rc_hp_vis', '23% / 49% (any bag)'),
    ('Banking', 'Median bag age at tribute (rounds)', 'median', 'bag_age', '40 / 22'),
    ('Banking', 'Gems per tribute', 'mean', ('trib_gems', 'trib_n'), ''),
    ('Banking', 'Carried gems per body-round', 'mean', ('carry_sum', 'carry_n'), '16.9 / 9.7'),
    ('Banking', 'Gems lost on death per game', 'pergame', 'lost_gems', '47 / 95'),
    ('Builds', 'Spawn exits with < 30 gold', 'rate', ('exit_lt30', 'exit_n'), '100% / -'),
    ('Builds', 'Deaths with >= 30 gold that shop while dead', 'rate', ('ds_shop', 'ds_n'), '100% / 55%'),
    ('Fights', 'Basic attack on lowest hp+shield (2+ in range)', 'rate', ('bt_hit', 'bt_n'), '92% / 79% (random 49%)'),
    ('Fights', '... random-pick baseline', 'rate', ('bt_rand', 'bt_n'), '49%'),
    ('Fights', 'Available kill taken (spells counted)', 'rate', ('kill_taken', 'kill_n'), '97% / 79%'),
    ('Fights', 'Available kill taken (basic attack only)', 'rate', ('killb_taken', 'killb_n'), '93% / 90%'),
    ('Fights', 'Killer acts before its victim', 'rate', ('ko_first', 'ko_n'), '74% / 45%'),
    ('Fights', 'AoE hits 2+ champions when 2+ visible fit', 'rate', ('aoe_hit', 'aoe_n'), '95% / 92%'),
    ('Disengage', 'Drops below 25% hp in combat surviving 30 rounds', 'rate', ('lowc_surv', 'lowc_n'), '62% / 36%'),
    ('Disengage', 'All drops below 25% hp surviving 30 rounds', 'rate', ('low_surv', 'low_n'), '73% / 52%'),
    ('Chasing', 'Follow a fleeing visible enemy within 6', 'rate', ('ch_follow', 'ch_n'), '59% / 49%'),
    ('Chasing', 'Chase episodes (2+ follows) where the team kills the target', 'rate', ('chep_kill', 'chep_n'), '31% / 12%'),
]


def value(acc, kind, keys):
    c, l = acc['c'], acc['l']
    g = c.get('games', 0) or 1
    if kind == 'rate':
        n, d = c.get(keys[0], 0), c.get(keys[1], 0)
        return (n / d if d else None), (f'{100 * n / d:.0f}% ({n:.0f}/{d})' if d else '-')
    if kind == 'per100':
        n, d = c.get(keys[0], 0), c.get(keys[1], 0)
        return (100 * n / d if d else None), (f'{100 * n / d:.2f} ({n})' if d else '-')
    if kind == 'pergame':
        v = c.get(keys, 0) / g
        return v, f'{v:.1f}'
    if kind == 'mean':
        s, n = c.get(keys[0], 0), c.get(keys[1], 0)
        return (s / n if n else None), (f'{s / n:.2f} (n={n})' if n else '-')
    if kind == 'median':
        v = l.get(keys, [])
        if not v: return None, '-'
        x = statistics.median(v)
        return x, (f'{100 * x:.0f}%' if keys == 'rc_hp_vis' else f'{x:g}') + f' (n={len(v)})'
    if kind == 'pair':
        a, b = c.get(keys[0], 0), c.get(keys[1], 0)
        return [a, b], f'{a} vs {b}'
    if kind == 'count':
        n, d = c.get(keys[0], 0), c.get(keys[1], 0)
        return (n / d if d else None), (f'{n} ({100 * n / d:.1f}% of {d})' if d else '-')


def builds(acc, top=3):
    c = acc['c']; per = collections.defaultdict(collections.Counter); orders = collections.defaultdict(collections.Counter)
    games = {}
    for k, v in c.items():
        p = k.split('|')
        if p[0] == 'shard': per[p[1]][f'{p[2]} {p[3]}'] += v
        elif p[0] == 'order': orders[p[1]][p[2]] += v
        elif p[0] == 'champgames': games[p[1]] = v
    out = {}
    for ch, cnt in per.items():
        tot = sum(cnt.values()); n = max(1, games.get(ch, 1))
        o, on = orders[ch].most_common(1)[0] if orders[ch] else ('-', 0)
        out[ch] = (tot / n, ', '.join(f'{k} {100 * v / tot:.0f}%' for k, v in cnt.most_common(top)), f'{o} ({100 * on / n:.0f}%)')
    return out


def report(acc, title, fish=None):
    cols = ['Metric', title, 'opponents']
    if fish: cols += ['Fish (computed)', 'Fish opp (computed)']
    cols.append('FISH-BOT.md (Fish / opp)')
    lines = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    sec = None
    for s, label, kind, keys, ref in M:
        if s != sec:
            lines.append(f'| **{s}** |' + ' |' * (len(cols) - 1)); sec = s
        row = [label, value(acc['sel'], kind, keys)[1], value(acc['opp'], kind, keys)[1]]
        if fish: row += [value(fish['sel'], kind, keys)[1], value(fish['opp'], kind, keys)[1]]
        lines.append('| ' + ' | '.join(row + [ref]) + ' |')
    out = '\n'.join(lines)
    sets = [(title, acc['sel']), ('opponents', acc['opp'])] + ([('Fish', fish['sel'])] if fish else [])
    out += '\n\nShards bought per champion: shards per champion-game, top 3 family/stat by share; ' \
        'most common first three emblems (share of champion-games).\n\n| Champion | ' + \
        ' | '.join(n for n, _ in sets) + ' |\n|' + '---|' * (len(sets) + 1)
    bs = [builds(a) for _, a in sets]
    for ch in sorted(set().union(*bs)):
        out += f'\n| {ch} | ' + ' | '.join(f'{b[ch][0]:.1f}: {b[ch][1]}; {b[ch][2]}' if ch in b else '-' for b in bs) + ' |'
    return out


def expand(sources):
    out = []
    for s in sources:
        hits = sorted(glob.glob(s)) if any(ch in s for ch in '*?[') else [s]
        if not hits: raise SystemExit(f'no match for {s}')
        out += hits
    return out


def norm(p):
    path = Path(p)
    path = path if path.is_absolute() else Path.cwd() / path
    try: return path.resolve().relative_to(ROOT).as_posix().rstrip('/')
    except ValueError: return path.resolve().as_posix()


def select(sources, team, index):
    """[(analysis dir, selected team index)] for games where exactly one team's name contains `team`."""
    by_dir = collections.defaultdict(list)
    for r in index: by_dir[r['dir']].append(r)
    jobs, skipped, seen = [], 0, set()
    want = team.lower()
    for src in sources:
        name = Path(src).name
        if len(name) == 16 and (ANALYSIS / name / 'meta.json').exists():
            rows = by_dir.get(name) or [{'dir': name, 'ok': True, 'teams': [t['name'] for t in Game(name).meta['teams']]}]
        else:
            p = norm(src)
            rows = [r for r in index if r['source'] == p or r['source'].startswith(p + '/')]
            if not rows: raise SystemExit(f'no extracted replays under {src} (run node tools/replay/extract.mjs {src})')
        for r in rows:
            if not r['ok'] or r['dir'] in seen: continue
            seen.add(r['dir'])
            m = [i for i, n in enumerate(r['teams']) if want in (n or '').lower()]
            if len(m) == 1: jobs.append((r['dir'], m[0]))
            else: skipped += 1
    return jobs, skipped


def fish_jobs(index):
    jobs, seen = [], set()
    for r in index:
        if r['source'].startswith('replay-bulk/2026-10-18/') and 'Intercontinental-Fish' in r['source'] and r['ok'] \
                and FISH in r['teams'] and r['dir'] not in seen:
            seen.add(r['dir']); jobs.append((r['dir'], r['teams'].index(FISH)))
    return jobs


def load_fish_cache():
    try:
        d = json.loads(FISH_CACHE.read_text(encoding='utf-8'))
        return d['acc'] if d.get('v') == VERSION else None
    except (OSError, ValueError, KeyError):
        return None


def dump(acc, title, path):
    out = {'team': title, 'games': acc['sel']['c'].get('games', 0), 'metrics': [], 'builds': {}}
    for s, label, kind, keys, ref in M:
        out['metrics'].append({'section': s, 'metric': label, 'team': value(acc['sel'], kind, keys)[0],
                               'opponents': value(acc['opp'], kind, keys)[0], 'fish_bot_md': ref})
    out['builds'] = {'team': builds(acc['sel']), 'opponents': builds(acc['opp'])}
    out['raw'] = acc
    Path(path).write_text(json.dumps(out, indent=1), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sources', nargs='*')
    ap.add_argument('--team', help='substring of the selected team or bot name')
    ap.add_argument('--fish', action='store_true', help="Fish's 459 ladder games (cached)")
    ap.add_argument('--refresh', action='store_true', help='recompute the Fish cache')
    ap.add_argument('--json', help='also write the numbers here')
    ap.add_argument('--threads', type=int, default=max(1, min(16, (os.cpu_count() or 2) - 1)))
    a = ap.parse_args()
    if a.fish == bool(a.sources or a.team): ap.error('give either --fish or sources with --team')
    if not a.fish and not a.team: ap.error('--team is required with sources')
    index = load_index()
    if a.fish:
        acc = None if a.refresh else load_fish_cache()
        if acc is None:
            jobs = fish_jobs(index)
            print(f'{len(jobs)} Fish games', file=sys.stderr)
            acc = run(jobs, a.threads)
            FISH_CACHE.parent.mkdir(parents=True, exist_ok=True)
            FISH_CACHE.write_text(json.dumps({'v': VERSION, 'acc': acc}), encoding='utf-8')
        title, fish = 'Fish', None
    else:
        jobs, skipped = select(expand(a.sources), a.team, index)
        if not jobs: raise SystemExit(f'no games with exactly one team matching {a.team!r}')
        print(f'{len(jobs)} games' + (f', {skipped} skipped (no or both teams match)' if skipped else ''), file=sys.stderr)
        acc = run(jobs, a.threads)
        title, fish = a.team, load_fish_cache()
    print(report(acc, title, fish))
    if a.json: dump(acc, title, a.json)


if __name__ == '__main__':
    main()
