"""Second-pass behaviour features: camp poke range, victim activity at death, ward details, tribute cancels, ambushes."""
import pickle
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

from common import games, load, chebyshev

OUT = __file__.replace('deep.py', 'deep.pkl')


def feat(rec):
    try:
        return _feat(rec)
    except Exception as ex:
        import traceback
        return {'rec': rec, 'error': traceback.format_exc()}


def _feat(rec):
    g = load(rec)
    M = g.map
    T = g.team_of
    ev = g.events
    camp_pos = {c['id']: (c['x'], c['y']) for c in M.camps}
    camp_group = {c['id']: c['group'] for c in M.camps}
    camp_type = {c['id']: c['type'] for c in M.camps}
    tile_group = {}
    for grp in M.groups:
        for t in grp['tiles']:
            tile_group[tuple(t)] = grp['id']
    out = {'rec': rec, 'names': g.names, 'team_of': dict(T), 'types': {c['id']: c['name'] for c in g.champs}, 'nbush': len(M.bushes), 'map': g.map_name}
    # 1. camp damage by distance, per champion
    cd = defaultdict(lambda: defaultdict(float))  # (champ) -> dist -> dmg
    cd_kind = defaultdict(lambda: defaultdict(float))
    awake_g = {}
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            f = tuple(e['f'])
            for cp, amt in e['cdmg']:
                d = chebyshev(f, camp_pos[cp]) if cp in camp_pos else -1
                cd[e['a']][min(d, 5)] += amt
                cd_kind[e['a']][(e['k'] if e['k'] == 'attack' else e.get('ab'), min(d, 5))] += amt
    taken = defaultdict(float)
    for s, r, v, amt in g.camp_damage:
        taken[v] += amt
    out['camp_dmg_dist'] = {c: dict(v) for c, v in cd.items()}
    out['camp_dmg_kind'] = {c: dict(v) for c, v in cd_kind.items()}
    out['camp_taken'] = dict(taken)

    # 2. victim activity at death
    camp_hit_r = defaultdict(set)  # champ -> rounds it hit a camp
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            camp_hit_r[e['a']].add(e['r'])
    camp_taken_r = defaultdict(set)
    for s, r, v, amt in g.camp_damage:
        camp_taken_r[v].add(r)
    first_dmg = {}
    cdmg_list = g.champ_damage
    vic_hits = defaultdict(list)
    for s, r, a, v, amt, ap, vp in cdmg_list:
        vic_hits[v].append((r, a))
    deaths = []
    for e in g.deaths:
        if 'linked' in e or e.get('by') is None:
            continue
        v, r = e['v'], e['r']
        k = e['by']
        ch = g.ch(v)
        i0 = g.start_idx(r)
        act = []
        if any(rr in camp_hit_r[v] for rr in range(r - 4, r + 1)):
            act.append('farming')
        if any(rr in camp_taken_r[v] for rr in range(r - 6, r + 1)):
            act.append('camp_hurt')
        at = tuple(e['at'])
        if at in tile_group:
            act.append('on_capture_tile')
        chan = ch['chan'][i0]
        if chan == 1:
            act.append('recalling')
        if chan == 2:
            act.append('tributing')
        if e['gems'] >= 30:
            act.append('bag30')
        if M.altar_dist(at) <= 3:
            act.append('near_altar')
        # fight start: first hit on the victim within the last 12 rounds chain
        hits = [x for x in vic_hits[v] if r - 12 <= x[0] <= r]
        r0 = hits[0][0] if hits else r
        # did the victim see the killer in the 3 rounds before r0?
        sees = ch['sees']
        seen_before = any(k in (sees[j] or []) for j in range(max(0, r0 - 4), max(0, r0 - 1)))
        if not seen_before:
            act.append('ambushed')
        hp0 = ch['hp'][g.start_idx(r0)] / ch['maxHp'][g.start_idx(r0)]
        # killer: where from
        kp0 = g.pos(k, g.start_idx(r0))
        vp0 = g.pos(v, g.start_idx(r0))
        chase = None
        if vp0:
            chase = chebyshev(vp0, at)
        attackers = {a for rr, a in hits}
        deaths.append({'r': r, 'r0': r0, 'v': v, 'k': k, 'act': act, 'hp0': hp0, 'chase': chase, 'n_att': len(attackers),
                       'kdist0': chebyshev(kp0, vp0) if kp0 and vp0 else None, 'kbush0': kp0 in M.bushes if kp0 else None,
                       'gems': e['gems'], 'half': M.half(M.own(T[v], at))})
    out['kills'] = deaths

    # 3. wards
    wards = []
    for e in ev:
        if e['k'] == 'ward':
            a = e['a']
            p = tuple(e['to'])
            me = g.pos(a, e['r'] - 1)
            wards.append({'r': e['r'], 'a': a, 'to': p, 'bush': p in M.bushes, 'd': chebyshev(me, p) if me else None,
                          'me_bush': me in M.bushes if me else None})
    out['wards'] = wards
    # ward vision use: did wards reveal enemies? count rounds where a champion sees an enemy only via ward is not separable; skip

    # 4. tribute cancels manual: context
    tc = []
    starts = {}
    for e in ev:
        if e['k'] == 'tribute_start':
            starts[e['a']] = e
        elif e['k'] == 'tribute_cancel':
            s = starts.get(e['a'])
            i = g.start_idx(e['r'])
            near_en = sum(1 for c in T if T[c] != T[e['a']] and g.pos(c, i) and g.pos(e['a'], i) and chebyshev(g.pos(c, i), g.pos(e['a'], i)) <= 6)
            tc.append({'r': e['r'], 'a': e['a'], 'cause': e.get('cause'), 'gems': e['gems'], 'left': e.get('left'),
                       'started': s['r'] if s else None, 'near_enemy': near_en})
    out['tcancel'] = tc
    # 5. recall: where and after what
    rc = []
    for e in ev:
        if e['k'] == 'recall_end':
            a = e['a']
            i = g.start_idx(e['r'] - 5)
            rc.append({'r': e['r'], 'a': a, 'gems': e['gems'], 'hp': g.ch(a)['hp'][i] / g.ch(a)['maxHp'][i],
                       'gold': g.ch(a)['gold'][i], 'dist': chebyshev(tuple(e['f']), M.spawn_center(T[a]))})
    out['recall_end'] = rc
    return out


if __name__ == '__main__':
    since = sys.argv[1] if len(sys.argv) > 1 else '2026-10-16T08:00'
    recs = games(since=since)
    with Pool(14) as p:
        res = p.map(feat, recs, chunksize=4)
    errs = [r for r in res if 'error' in r]
    print(len(res), 'errors', len(errs), errs[:1])
    pickle.dump([r for r in res if 'error' not in r], open(OUT, 'wb'))
