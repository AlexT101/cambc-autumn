"""Per-game behaviour features for top-team analysis. Writes features.pkl (list of per-game dicts)."""
import pickle
import sys
from collections import defaultdict
from multiprocessing import Pool

from common import games, load, chebyshev
from analysis.fights import engagements

OUT = __file__.replace('features.py', 'features.pkl')


def in_box(p, s):
    return p is not None and s['minX'] <= p[0] <= s['maxX'] and s['minY'] <= p[1] <= s['maxY']


def bush_clusters(bushes):
    cl, cid = {}, 0
    for b in bushes:
        if b in cl:
            continue
        stack = [b]
        cl[b] = cid
        while stack:
            x, y = stack.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in bushes and n not in cl:
                    cl[n] = cid
                    stack.append(n)
        cid += 1
    return cl


def feat(rec):
    try:
        return _feat(rec)
    except Exception as ex:
        return {'rec': rec, 'error': repr(ex)}


def _feat(rec):
    g = load(rec)
    M = g.map
    T = g.team_of
    N = g.n_rounds
    ev = g.events
    camp_group = {c['id']: c['group'] for c in M.camps}
    full_hp = defaultdict(float)
    for c in M.camps:
        full_hp[c['group']] += c['hp']
    gtiles = {grp['id']: [tuple(t) for t in grp['tiles']] for grp in M.groups}
    gside = {grp['id']: grp['side'] for grp in M.groups}
    gtypes = {grp['id']: ''.join(sorted({'Wolf': 'W', 'Elk': 'E', 'Gem cluster': 'G', 'Gold cluster': '$', 'Monolith': 'M'}[t] for t in grp['types'])) for grp in M.groups}
    tile_group = {}
    for gid, ts in gtiles.items():
        for t in ts:
            tile_group[t] = gid
    bcl = bush_clusters(M.bushes)

    def pos(c, i):
        return g.pos(c, i)

    out = {'rec': rec, 'map': g.map_name, 'N': N, 'winner': g.winner, 'names': g.names,
           'types': {c['id']: c['name'] for c in g.champs}, 'team_of': dict(T)}

    # ---------- camp sessions ----------
    sessions = []
    cur = {}
    dmg_since = defaultdict(lambda: [0.0, 0.0])
    dmg_by_champ = defaultdict(lambda: defaultdict(float))
    sess_list = defaultdict(list)
    camp_deaths = []
    for e in ev:
        k = e['k']
        if k == 'group_wake':
            gid = e['g']
            s = {'g': gid, 'r0': e['r'], 'by': e.get('by'), 'dmg': [0.0, 0.0], 'champs': defaultdict(float), 'hp0': full_hp[gid] - sum(dmg_since[gid])}
            cur[gid] = s
            sess_list[gid].append(s)
        elif k in ('attack', 'cast') and e.get('cdmg'):
            t = T.get(e['a'])
            for cp, amt in e['cdmg']:
                gid = camp_group.get(cp)
                if gid is None:
                    continue
                dmg_since[gid][t] += amt
                dmg_by_champ[gid][e['a']] += amt
                if gid in cur:
                    cur[gid]['dmg'][t] += amt
                    cur[gid]['champs'][e['a']] += amt
        elif k == 'camp_attack' and e.get('refl'):
            t = T.get(e.get('tgt'))
            for cp, amt in e['refl']:
                gid = camp_group.get(cp)
                if gid is None or t is None:
                    continue
                dmg_since[gid][t] += amt
                if gid in cur:
                    cur[gid]['dmg'][t] += amt
        elif k == 'group_sleep':
            gid = e['g']
            if gid in cur:
                s = cur.pop(gid)
                s['r1'] = e['r']
                s['end'] = 'sleep'
                s['hp1'] = full_hp[gid] - sum(dmg_since[gid])
                sessions.append(s)
        elif k == 'group_clear':
            gid = e['g']
            s = cur.pop(gid, None)
            ds = dmg_since[gid]
            clear = {'g': gid, 'r': e['r'], 'by': e.get('by'), 'team': T.get(e.get('by')), 'dmg': list(ds),
                     'nsess': len(sess_list[gid]), 'sess': [(x['r0'], x.get('r1', e['r']), list(x['dmg'])) for x in sess_list[gid]],
                     'champs': dict(dmg_by_champ[gid])}
            out.setdefault('clears', []).append(clear)
            if s:
                s['r1'] = e['r']
                s['end'] = 'clear'
                s['hp1'] = 0
                s['clear_team'] = T.get(e.get('by'))
                sessions.append(s)
        elif k == 'group_respawn':
            gid = e['g']
            dmg_since[gid] = [0.0, 0.0]
            dmg_by_champ[gid] = defaultdict(float)
            sess_list[gid] = []
        elif k == 'death' and e.get('by') == 'camp':
            camp_deaths.append({'v': e['v'], 'r': e['r'], 'gems': e['gems'], 'at': e['at']})
    for s in sessions:
        s['champs'] = dict(s['champs'])
        s['full'] = full_hp[s['g']]
        s['type'] = gtypes[s['g']]
        s['side'] = gside[s['g']]
    # Partial sessions: what did the damagers do before the next session?
    partial = []
    by_g = defaultdict(list)
    for s in sessions:
        by_g[s['g']].append(s)
    for gid, ss in by_g.items():
        ss.sort(key=lambda s: s['r0'])
        for j, s in enumerate(ss):
            if s['end'] != 'sleep' or s['hp1'] >= s['hp0'] - 1:
                continue
            tot = sum(s['dmg'])
            if tot <= 0:
                continue
            team = 0 if s['dmg'][0] >= s['dmg'][1] else 1
            nxt = ss[j + 1] if j + 1 < len(ss) and ss[j + 1]['hp0'] < s['full'] - 1 else None
            info = {'g': gid, 'type': s['type'], 'side': s['side'], 'team': team, 'r0': s['r0'], 'r1': s['r1'],
                    'hp_left': s['hp1'] / s['full'], 'hp_start': s['hp0'] / s['full'], 'champs': list(s['champs'])}
            # damagers' state at the sleep round and their actions until next session
            lo = s['r1']
            hi = nxt['r0'] if nxt else min(N, lo + 150)
            acts = defaultdict(set)
            for c in s['champs']:
                ch = g.ch(c)
                i = min(lo - 1, len(ch['hp']) - 1)
                acts['hpfrac'].add(round(ch['hp'][i] / ch['maxHp'][i], 2) if ch['alive'][i] else -1)
                for r in range(lo, min(hi, len(ch['x']))):
                    if not ch['alive'][r]:
                        acts['died'].add(c)
                    elif in_box((ch['x'][r], ch['y'][r]), M.spawn[T[c]]):
                        acts['home'].add(c)
            for e in ev:
                if lo <= e['r'] < hi and e.get('a') in s['champs']:
                    if e['k'] == 'recall_start':
                        acts['recall'].add(e['a'])
                    elif e['k'] == 'tribute_start':
                        acts['tribute'].add(e['a'])
                    elif e['k'] == 'shop':
                        acts['shop'].add(e['a'])
            info['acts'] = {k: (sorted(v) if k != 'hpfrac' else sorted(v)) for k, v in acts.items()}
            if nxt:
                nt = 0 if nxt['dmg'][0] >= nxt['dmg'][1] else 1
                info['next'] = {'r0': nxt['r0'], 'gap': nxt['r0'] - s['r1'], 'team': nt, 'by': nxt['by'],
                                'end': nxt['end'], 'clear_team': nxt.get('clear_team'), 'same_champs': bool(set(nxt['champs']) & set(s['champs']))}
            partial.append(info)
    out['partial'] = partial
    out['camp_deaths'] = camp_deaths
    out['n_sessions'] = len(sessions)

    # ---------- captures, contests, respawn denial ----------
    caps, resets, flips = [], [], []
    for e in ev:
        if e['k'] == 'capture':
            caps.append({'g': e['g'], 'r': e['r'], 'team': e['team'], 'gems': sum(x[1] for x in e['shares']),
                         'gold': sum(x[2] for x in e['shares']), 'n': len(e['shares']), 'side': gside[e['g']], 'type': gtypes[e['g']]})
        elif e['k'] == 'capture_reset':
            resets.append({'g': e['g'], 'r': e['r'], 'team': e['team'], 'left': e.get('left'), 'contested': e.get('contested'), 'side': gside[e['g']]})
        elif e['k'] == 'capture_flip':
            flips.append({'g': e['g'], 'r': e['r'], 'team': e['team'], 'from': e.get('from')})
    respawns = defaultdict(list)
    for e in ev:
        if e['k'] == 'group_respawn':
            respawns[e['g']].append(e['r'])
    gresp = {grp['id']: grp['respawn'] for grp in M.groups}
    denial = []
    for c in caps:
        exp = c['r'] + gresp[c['g']]
        if exp > N:
            continue
        act = next((r for r in respawns[c['g']] if r >= exp), None)
        delay = (act if act else N) - exp
        if delay > 0:
            # who stands on the tiles at the expected round start
            i = exp - 2
            occ = []
            for cid in T:
                p = pos(cid, i)
                if p in tile_group and tile_group[p] == c['g']:
                    occ.append(cid)
            # occupiers over the delay
            occ_all = defaultdict(int)
            for r in range(exp - 1, (act or N) - 1):
                for cid in T:
                    p = pos(cid, r - 1)
                    if p in tile_group and tile_group[p] == c['g']:
                        occ_all[cid] += 1
            denial.append({'g': c['g'], 'cap_team': c['team'], 'exp': exp, 'delay': delay, 'occ': occ, 'occ_all': dict(occ_all),
                           'type': c['type'], 'side': c['side']})
    out['captures'] = caps
    out['resets'] = resets
    out['flips'] = flips
    out['denial'] = denial
    # Reset causes: for contested resets, which enemy stepped on; also non-contested resets from enemy kills/ pushes
    # ---------- bushes ----------
    bush_rounds = defaultdict(int)
    alive_rounds = defaultdict(int)
    bush_still = defaultdict(int)
    for cid in T:
        ch = g.ch(cid)
        for i in range(len(ch['x'])):
            if ch['alive'][i] and ch['x'][i] is not None:
                p = (ch['x'][i], ch['y'][i])
                alive_rounds[cid] += 1
                if p in M.bushes:
                    bush_rounds[cid] += 1
                    if i > 0 and ch['x'][i - 1] == p[0] and ch['y'][i - 1] == p[1]:
                        bush_still[cid] += 1
    out['bush'] = {'bush': dict(bush_rounds), 'alive': dict(alive_rounds), 'still': dict(bush_still), 'nbush': len(M.bushes)}
    atk = []
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            a = e['a']
            vs = [(v, amt) for v, amt in e['dmg'] if v in T and T[v] != T[a] and amt > 0]
            if not vs:
                continue
            f = tuple(e['f'])
            fb = f in M.bushes
            for v, amt in vs:
                i = e['r'] - 1
                sees = g.ch(v)['sees'][i] if i < len(g.ch(v)['sees']) else []
                atk.append((e['r'], a, v, amt, fb, a in (sees or []), e['k'], e.get('ab')))
    out['champ_atk'] = atk
    wards = []
    for e in ev:
        if e['k'] == 'ward':
            p = tuple(e['to'])
            a = e['a']
            ch = g.ch(a)
            i = e['r'] - 1
            me = pos(a, i)
            wards.append({'r': e['r'], 'a': a, 'to': p, 'bush': p in M.bushes, 'altar': M.altar_dist(p),
                          'half': M.half(M.own(T[a], p)), 'camp': min((chebyshev(p, (c['x'], c['y'])) for c in M.camps), default=99),
                          'self_bush': me in M.bushes if me else None, 'alive': bool(ch['alive'][i]) if i < len(ch['alive']) else None})
    out['wards'] = wards

    # ---------- deaths / kills ----------
    deaths = []
    chans = {}
    for e in ev:
        if e['k'] in ('recall_cancel', 'tribute_cancel', 'teleport_cancel') and e.get('cause') == 'death':
            chans[(e['s'], e['a'])] = e['k']
    for e in g.deaths:
        v = e['v']
        if 'linked' in e and e.get('by') != 'camp':
            pass
        i = g.start_idx(e['r'])
        at = tuple(e['at']) if e.get('at') else None
        ch = g.ch(v)
        d = {'r': e['r'], 'v': v, 'vt': T[v], 'gems': e['gems'], 'by': e.get('by'), 'at': at, 'linked': 'linked' in e,
             'chan': chans.get((e['s'], v)), 'altar': M.altar_dist(at) if at else None,
             'half': M.half(M.own(T[v], at)) if at else None, 'assists': e.get('assists', []),
             'hpmax': ch['maxHp'][i], 'cause': e.get('cause')}
        # enemies and allies within 6 at the start of the round
        if at:
            d['near_enemy'] = sum(1 for c in T if T[c] != T[v] and pos(c, i) and chebyshev(pos(c, i), at) <= 6)
            d['near_ally'] = sum(1 for c in T if T[c] == T[v] and c != v and pos(c, i) and chebyshev(pos(c, i), at) <= 6)
            d['on_camp'] = tile_group.get(at)
            # victim chan state at start of round
            d['chan0'] = ch['chan'][i]
            # victim was walking toward an altar over the previous 5 rounds?
            p5 = pos(v, max(0, i - 5))
            d['to_altar'] = (M.altar_dist(p5) - M.altar_dist(at)) if p5 else None
            d['to_home'] = None
            if p5:
                sc = M.spawn_center(T[v])
                d['to_home'] = chebyshev(p5, sc) - chebyshev(at, sc)
        deaths.append(d)
    out['deaths'] = deaths

    # ---------- tributes, recalls, shops, locks ----------
    trib, recalls, shops, locks, tcancel = [], [], [], [], []
    for e in ev:
        k = e['k']
        if k == 'tribute_start':
            trib.append({'r': e['r'], 'a': e['a'], 'gems': e['gems'], 'altar': tuple(e['altar'])})
        elif k == 'tribute_end':
            trib.append({'r': e['r'], 'a': e['a'], 'gems': e['gems'], 'end': 1})
        elif k == 'tribute_cancel':
            tcancel.append({'r': e['r'], 'a': e['a'], 'gems': e['gems'], 'cause': e.get('cause')})
        elif k == 'recall_start':
            ch = g.ch(e['a'])
            i = g.start_idx(e['r'])
            recalls.append({'r': e['r'], 'a': e['a'], 'gems': e['gems'], 'hpfrac': ch['hp'][i] / ch['maxHp'][i],
                            'gold': ch['gold'][i], 'dist': chebyshev(tuple(e['at']), M.spawn_center(T[e['a']]))})
        elif k == 'recall_end':
            recalls.append({'r': e['r'], 'a': e['a'], 'gems': e['gems'], 'end': 1})
        elif k == 'shop':
            ch = g.ch(e['a'])
            i = e['r'] - 1
            shops.append({'r': e['r'], 'a': e['a'], 'gold': e['gold'], 'items': e.get('items', {}),
                          'alive': bool(ch['alive'][i]) if i < len(ch['alive']) else None})
        elif k == 'consumable':
            shops.append({'r': e['r'], 'a': e['a'], 'gold': e['gold'], 'cons': e.get('cons', {}), 'to': e.get('to')})
        elif k in ('lock_place', 'lock_destroyed', 'tribute_blocked'):
            locks.append({'k': k, 'r': e['r'], 'a': e.get('a'), 'team': e.get('team'), 'to': e.get('to') or e.get('at') or e.get('altar'), 'gems': e.get('gems')})
    out['trib'], out['recalls'], out['shops'], out['locks'], out['tcancel'] = trib, recalls, shops, locks, tcancel

    # ---------- team structure ----------
    struct = []
    for i in range(0, min(N, len(g.ch(g.team_ids[0][0])['x'])), 5):
        row = []
        for t in (0, 1):
            ps = [pos(c, i) for c in g.team_ids[t]]
            ps = [p for p in ps if p]
            # merge Cassi/Issac as separate bodies; components with link distance 4
            n = len(ps)
            par = list(range(n))

            def f(x):
                while par[x] != x:
                    par[x] = par[par[x]]
                    x = par[x]
                return x
            for a in range(n):
                for b in range(a + 1, n):
                    if chebyshev(ps[a], ps[b]) <= 4:
                        par[f(a)] = f(b)
            sizes = defaultdict(int)
            for a in range(n):
                sizes[f(a)] += 1
            row.append(sorted(sizes.values(), reverse=True))
        struct.append((i + 1, row))
    out['struct'] = struct

    # ---------- engagements ----------
    fights, _ = engagements(g)
    for fgt in fights:
        fgt.pop('dir', None)
    out['fights'] = fights

    # ---------- stuns ----------
    stuns = []
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('stun'):
            for v in e['stun']:
                if v in T and T[v] != T[e['a']]:
                    stuns.append((e['r'], e['t'], e['a'], v))
    out['stuns'] = stuns

    # ---------- openings (first 60 rounds) ----------
    first_camp = {}
    for e in ev:
        if e['r'] > 80:
            break
        if e['k'] in ('attack', 'cast') and e.get('cdmg') and e['a'] not in first_camp:
            gid = camp_group.get(e['cdmg'][0][0])
            first_camp[e['a']] = (e['r'], gid, gtypes.get(gid), gside.get(gid))
    out['first_camp'] = first_camp
    traj = {}
    for cid in T:
        ch = g.ch(cid)
        traj[cid] = [(M.own(T[cid], (ch['x'][i], ch['y'][i])) if ch['alive'][i] and ch['x'][i] is not None else None) for i in range(min(60, len(ch['x'])))]
    out['traj60'] = traj
    out['tributed'] = [g.final_gems[0], g.final_gems[1]]
    out['gems100'] = [[g.gems_at(t, r) for r in (100, 200, 300, 400, 500, 700, 1000)] for t in (0, 1)]
    return out


if __name__ == '__main__':
    since = sys.argv[1] if len(sys.argv) > 1 else '2026-10-16T08:00'
    recs = games(since=since)
    print(len(recs), 'games')
    with Pool(14) as p:
        res = p.map(feat, recs, chunksize=4)
    errs = [r for r in res if 'error' in r]
    print('errors', len(errs), errs[:3])
    with open(OUT, 'wb') as f:
        pickle.dump([r for r in res if 'error' not in r], f)
