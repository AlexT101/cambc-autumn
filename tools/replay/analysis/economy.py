import json
import math
import os
import re
from collections import Counter, defaultdict

from . import params as params_mod
from .camps import group_key, members, model_damage, walk_dist
from .data import ANALYSIS, chebyshev
from .util import mean, median, pct

VERSION = 1
CACHE = ANALYSIS / 'cache' / 'economy'
MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Issac', 'Heart of Ruin'}
DAMAGING = set('WEM')
LOOP_HP, LOOP_GAP = 0.35, 8

METRICS = {
    'camp_dps': ('camp HP dealt per champion attack-round, rounds 1-300', True, False),
    'camp_cast_share': ('share of camp damage dealt by casts', None, False),
    'camp_vs_min_ratio': ('camp damage taken / basic-attack minimum on clean solo-team clears (median)', False, False),
    'attack_share': ('champion-rounds 1-300 spent attacking camps', None, False),
    'walk_share': ('champion-rounds 1-300 spent walking', False, False),
    'gems_per_khp': ('captured gems per 1000 camp HP dealt, rounds 1-300', True, False),
    'sharers': ('champions sharing each capture, rounds 1-300 (mean)', None, False),
    'trip_overhead': ('altar trip overhead over the direct walk, rounds 1-300 (median rounds)', False, False),
    'recall_loops': ('recall loops (recall again within 8 rounds after arriving under 35% hp), rounds 1-300', False, False),
}
MEAN_KEYS = {'recall_loops', 'sharers'}


def _add(d, k, v):
    d[k] = d.get(k, 0) + v


def extract(g, P=None):
    W = (P or params_mod.DEFAULTS)['econ_window']
    path = CACHE / f'{g.dir}.json'
    key = [VERSION, W, os.stat(g.path / 'events.jsonl.gz').st_mtime_ns, os.stat(ANALYSIS / 'maps' / f'{g.map.hash}.json').st_mtime_ns]
    try:
        cached = json.loads(path.read_text(encoding='utf-8'))
        if cached['key'] == key:
            return cached['data']
    except (OSError, ValueError, KeyError):
        pass
    data = json.loads(json.dumps(_extract(g, W)))
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'{path.name}.{os.getpid()}.tmp')
    tmp.write_text(json.dumps({'key': key, 'data': data}), encoding='utf-8')
    os.replace(tmp, path)
    return data


def _extract(g, W):
    mp, ev, n = g.map, g.events, g.n_rounds
    team_of, name = g.team_of, g.name_of
    camp_group = {c['id']: c['group'] for c in mp.camps}
    gk = {grp['id']: group_key(mp, grp['id']) for grp in mp.groups}
    gold_group = {h for h, k in gk.items() if set(k) == {'$'}}
    tiles_of = {grp['id']: [tuple(t) for t in grp['tiles']] for grp in mp.groups}
    groups_at = defaultdict(list)
    for h, ts in tiles_of.items():
        for t in ts:
            groups_at[t].append(h)

    ng = len(mp.groups)
    states = [None] * (n + 2)
    cur = [1] * ng
    rows = sorted(g.rounds['groups'], key=lambda r: r[0])
    ri = 0
    for r in range(1, n + 2):
        while ri < len(rows) and rows[ri][0] <= r:
            cur[rows[ri][1]] = rows[ri][2]
            ri += 1
        states[r] = tuple(cur)

    def state(h, r):
        return states[max(1, min(r, n + 1))][h]

    def on_claimable(p, *rs):
        return p is not None and any(state(h, r) == 2 for h in groups_at.get(p, ()) for r in rs)

    ch = {c['id']: g.ch(c['id']) for c in g.champs}

    def pos(cid, r):
        c = ch[cid]
        i = max(0, r - 1)
        if i >= len(c['x']) or not c['alive'][i] or c['x'][i] is None:
            return None
        return (c['x'][i], c['y'][i])

    acts = defaultdict(lambda: defaultdict(set))
    camp_hits = defaultdict(lambda: defaultdict(set))
    recall_starts = defaultdict(list)
    recall_rounds = defaultdict(set)
    dealt = []
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast'):
            a = e['a']
            if e.get('cdmg'):
                tot = defaultdict(float)
                for c, amt in e['cdmg']:
                    if c in camp_group:
                        tot[camp_group[c]] += amt
                for h, amt in tot.items():
                    if amt > 0:
                        dealt.append((e['r'], a, h, amt, chebyshev(e['f'], e['to']), k))
                        camp_hits[a][e['r']].add(h)
                        acts[a][e['r']].add('camp')
            if e.get('dmg') and any(v in team_of and team_of[v] != team_of[a] and amt > 0 for v, amt in e['dmg']):
                acts[a][e['r']].add('champ')
            if k == 'cast' and e.get('moved'):
                acts[a][e['r']].add('move')
        elif k == 'move':
            acts[e['a']][e['r']].add('move')
        elif k == 'tribute_start':
            acts[e['a']][e['r']].add('trib')
        elif k == 'recall_start':
            recall_starts[e['a']].append(e['r'])
        elif k == 'recall_end':
            rs = [r for r in recall_starts[e['a']] if r < e['r']]
            if rs:
                recall_rounds[e['a']].update(range(rs[-1] + 1, e['r']))

    taken = []
    for e in ev:
        if e['k'] != 'camp_attack':
            continue
        r, h = e['r'], e['g']
        victims = [(e['tgt'], e['dmg'])] if e.get('tgt') in team_of and e.get('dmg') else []
        victims += [(v, amt) for v, amt in e.get('xdmg', []) if v in team_of]
        for v, amt in victims:
            hits = camp_hits[v].get(r - 1, set()) | camp_hits[v].get(r, set())
            tags = acts[v].get(r - 1, set()) | acts[v].get(r, set())
            p = pos(v, r - 1)
            if h in hits:
                cls = 'attacking it'
            elif hits:
                cls = 'attacking another group'
            elif on_claimable(p, r - 1):
                cls = 'capturing nearby'
            elif ch[v]['chan'][max(0, r - 2)] == 2:
                cls = 'tributing'
            elif 'champ' in tags:
                cls = 'fighting a champion'
            elif 'move' in tags:
                if any(h in camp_hits[v].get(rr, ()) for rr in range(r + 1, r + 6)):
                    cls = 'walking in'
                elif any(h in camp_hits[v].get(rr, ()) for rr in range(r - 6, r - 1)):
                    cls = 'walking out'
                else:
                    cls = 'passing by'
            else:
                cls = 'waiting (no move)' if any(h in camp_hits[v].get(rr, ()) for rr in range(r + 1, r + 6)) else 'idle in range'
            taken.append((team_of[v], gk[h], name[v] in MELEE, cls, amt))

    episodes, open_ep = [], {}
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            t = team_of[e['a']]
            for c, amt in e['cdmg']:
                if c not in camp_group or amt <= 0:
                    continue
                ep = open_ep.setdefault(camp_group[c], {'dealt': [0.0, 0.0], 'taken': [0.0, 0.0], 'att': [set(), set()], 'str': [{}, {}]})
                ep['dealt'][t] += amt
                ep['att'][t].add(e['a'])
                s = ch[e['a']]['str'][max(0, e['r'] - 1)]
                ep['str'][t][e['a']] = max(ep['str'][t].get(e['a'], 0), s)
        elif k == 'camp_attack' and e['g'] in open_ep:
            ep = open_ep[e['g']]
            if e.get('tgt') in team_of and e.get('dmg'):
                ep['taken'][team_of[e['tgt']]] += e['dmg']
            for v, amt in e.get('xdmg', []):
                if v in team_of:
                    ep['taken'][team_of[v]] += amt
        elif k in ('group_clear', 'group_sleep') and e['g'] in open_ep:
            ep = open_ep.pop(e['g'])
            ms = members(mp, e['g'])
            S = [sum(x.values()) for x in ep['str']]
            episodes.append({'gk': gk[e['g']], 'clear': k == 'group_clear', 'hp': sum(m[0] for m in ms), 'dealt': ep['dealt'], 'taken': ep['taken'],
                             'n_att': [len(a) for a in ep['att']], 'model': [model_damage(ms, x) if x else None for x in S]})

    captures = [e for e in ev if e['k'] == 'capture']
    sides, aggs = [], []
    for t in (0, 1):
        tids = g.team_ids[t]
        tset = set(tids)
        st = [g.champs[g.idx[c]]['stats'] for c in tids]
        A = {'mdt': sum(s['monsterDamageTaken'] for s in st), 'mdd': sum(s['monsterDamageDone'] for s in st), 'bodies': len(tids),
             'gems300': g.gems_at(t, W) if n >= W else None}

        dealt_gk, kind, d300 = {}, {}, 0.0
        for r, a, h, amt, dd, k in dealt:
            if team_of[a] != t:
                continue
            _add(dealt_gk, gk[h], amt)
            _add(kind, f'{"melee" if name[a] in MELEE else "ranged"}|{k}|{dd}', amt)
            if r <= W:
                d300 += amt
        A.update(dealt_gk=dealt_gk, dealt_kind=kind, dealt300=d300)
        tk_gk, tk_cls, tk_melee = {}, {}, {}
        for tt, k, melee, cls, amt in taken:
            if tt == t:
                _add(tk_gk, k, amt)
                _add(tk_cls, cls, amt)
                _add(tk_melee, 'melee' if melee else 'ranged', amt)
        A.update(taken_gk=tk_gk, taken_cls=tk_cls, taken_melee=tk_melee)

        ep_by, att, att_n, eff = {}, {}, [], []
        for ep in episodes:
            if ep['dealt'][t] <= 0 or not set(ep['gk']) & DAMAGING:
                continue
            na = ep['n_att'][t]
            att_n.append(na)
            _add(att, str(min(na, 3)), 1)
            x = ep_by.setdefault(f'{ep["gk"]}|{min(na, 3)}', [0, 0.0, 0.0])
            x[0] += 1
            x[1] += ep['dealt'][t]
            x[2] += ep['taken'][t]
            if ep['clear'] and ep['dealt'][1 - t] <= 0 and ep['dealt'][t] >= 0.98 * ep['hp'] and ep['model'][t]:
                eff.append(ep['taken'][t] / ep['model'][t])
        A.update(ep_by=ep_by, att=att, att_sum=sum(att_n), att_n=len(att_n), eff=eff)

        budget = Counter()
        for cid in tids:
            c = ch[cid]
            cats = []
            for r in range(1, min(W, len(c['turn'])) + 1):
                i = r - 1
                tv = c['turn'][i]
                tags = acts[cid].get(r, set())
                p = pos(cid, r)
                if tv == 4 or (not c['alive'][i] and not tags):
                    cat = 'dead'
                elif 'champ' in tags:
                    cat = 'fight'
                elif 'camp' in tags:
                    cat = 'attack camp'
                elif 'trib' in tags or c['chan'][i] == 2:
                    cat = 'tribute'
                elif r in recall_rounds[cid] or (tv == 3 and c['chan'][i] == 1):
                    cat = 'recall'
                elif tv == 3 and c['chan'][i] == 3:
                    cat = 'teleport'
                elif 'move' in tags:
                    cat = 'walk'
                elif on_claimable(p, r, r - 1):
                    cat = 'capture'
                elif mp.in_spawn(t, p):
                    cat = 'spawn idle'
                elif p is not None and any(state(h, r) == 3 and min(chebyshev(p, x) for x in tiles_of[h]) <= 4 for h in range(ng)):
                    cat = 'wait respawn'
                elif tv == 5:
                    cat = 'stunned'
                else:
                    cat = 'idle'
                cats.append(cat)
            j = 0
            while j < len(cats):
                if cats[j] != 'walk':
                    budget[cats[j]] += 1
                    j += 1
                    continue
                k2 = j
                while k2 < len(cats) and cats[k2] == 'walk':
                    k2 += 1
                nxt = cats[k2] if k2 < len(cats) else 'end'
                if nxt in ('attack camp', 'capture', 'wait respawn'):
                    lab = 'walk to camp'
                elif nxt == 'tribute':
                    lab = 'walk to altar'
                elif nxt == 'fight':
                    lab = 'walk to fight'
                elif nxt in ('spawn idle', 'recall'):
                    lab = 'walk to spawn'
                elif c['gems'][min(len(c['gems']) - 1, (j + k2) // 2)] > 0:
                    lab = 'walk to altar'
                else:
                    lab = 'walk other'
                budget[lab] += k2 - j
                j = k2
        A['budget'] = dict(budget)

        shares = defaultdict(list)
        for e in captures:
            if e['team'] == t:
                for c, gm, gd in e['shares']:
                    shares[c].append((e['r'], e['g']))
        tribs, last_trib = [], {}
        for e in ev:
            if e['k'] != 'tribute_start' or e['a'] not in tset:
                continue
            a, r = e['a'], e['r']
            caps = [x[0] for x in shares[a] if x[0] <= r]
            lo = last_trib.get(a, 0)
            last_trib[a] = r
            tribs.append({'r': r, 'a': a, 'gems': e['gems'], 'ncap': sum(1 for x in caps if x > lo), 'last_cap': caps[-1] if caps else None,
                          'dur': max(1, math.ceil(e['gems'] / 10))})
        trips, overs = [], []
        for x in tribs:
            a = x['a']
            if x['last_cap'] is None or x['r'] > W:
                continue
            end = x['r'] + x['dur']
            nxt = next((rr for rr in range(end, min(end + 120, n)) if camp_hits[a].get(rr)), None)
            if nxt is None:
                continue
            p0, p1 = pos(a, x['last_cap']), pos(a, nxt)
            if p0 is None or p1 is None or any(not ch[a]['alive'][rr - 1] for rr in range(x['last_cap'], nxt)):
                continue
            direct = walk_dist(mp, [p0]).get(p1)
            if direct is not None:
                trips.append(nxt - x['last_cap'])
                overs.append(nxt - x['last_cap'] - direct)
        t300 = [x for x in tribs if x['r'] <= W]
        A.update(trib300=len(t300), bags=[x['gems'] for x in t300], ncap=[x['ncap'] for x in t300], trips=trips, overs=overs)
        trib_by = defaultdict(lambda: [0, 0])
        for x in t300:
            trib_by[x['a']][0] += 1
            trib_by[x['a']][1] += x['gems']

        cap_label, cap_gk, cap_side, share_g = {}, {}, {}, []
        cap_n = cap_gems = 0
        for e in captures:
            if e['team'] != t or e['r'] > W:
                continue
            gm = sum(s[1] for s in e['shares'])
            k = len(e['shares'])
            own = mp.own_group(t, e['g'])
            x = cap_label.setdefault(mp.group_label(own), [0, 0])
            x[0] += 1
            x[1] += gm
            x = cap_gk.setdefault(gk[e['g']], [0, 0, 0])
            x[0] += 1
            x[1] += gm
            x[2] += k
            _add(cap_side, mp.group_side(own), gm)
            cap_n += 1
            cap_gems += gm
            if k and gm > 0:
                share_g.append(gm / k)
        A.update(cap_n=cap_n, cap_gems=cap_gems, cap_label=cap_label, cap_gk=cap_gk, cap_side=cap_side, share_g=share_g)

        shards = defaultdict(dict)
        for e in ev:
            if e['k'] == 'shop' and e['a'] in tset:
                for it, dlt in (e.get('items') or {}).items():
                    if 'Shard' in it or 'Emblem' in it:
                        _add(shards[name[e['a']]], it.replace('Emblem', 'Shard'), (25 if it.startswith('Greed') else 5) * dlt if 'Emblem' in it else dlt)
        A['shards'] = dict(shards)

        camp_dmg_r, champ_dmg_r = defaultdict(float), defaultdict(float)
        for s, r, v, amt in g.camp_damage:
            if v in tset:
                camp_dmg_r[(v, r)] += amt
        for s, r, a, v, amt, *_ in g.champ_damage:
            if v in tset:
                champ_dmg_r[(v, r)] += amt
        camp_att = defaultdict(set)
        for e in ev:
            if e['k'] in ('attack', 'cast') and e.get('a') in tset and e.get('cdmg'):
                camp_att[e['a']].add(e['r'])
        recalls, loops, starts, ends = [], [], defaultdict(list), defaultdict(list)
        for e in ev:
            if e['k'] == 'recall_start' and e['a'] in tset:
                starts[e['a']].append(e['r'])
            elif e['k'] == 'recall_end' and e['a'] in tset:
                a = e['a']
                ends[a].append(e['r'])
                prior = [x for x in starts[a] if x < e['r']]
                if e['r'] > W or not prior:
                    continue
                rs = prior[-1]
                c = ch[a]
                cd = sum(camp_dmg_r[(a, r)] for r in range(rs - 10, rs + 1))
                hd = sum(champ_dmg_r[(a, r)] for r in range(rs - 10, rs + 1))
                before = [r for r in camp_att[a] if r <= rs]
                after = [r for r in camp_att[a] if r > e['r']]
                recalls.append([name[a], c['hp'][rs - 1] / c['maxHp'][rs - 1], 'camp' if cd > hd else 'champion' if hd > 0 else 'none',
                                min(after) - max(before) if before and after else None, int(e['gems'] > 0)])
        for a, rs in ends.items():
            c = ch[a]
            for r0, r1 in zip(rs, rs[1:]):
                if c['hp'][r0 - 1] < LOOP_HP * c['maxHp'][r0 - 1] and r1 - r0 <= LOOP_GAP:
                    loops.append([r0, r1, name[a]])
        A.update(recalls=recalls, loops=loops)

        bodies = []
        for cid in tids:
            basic = cast = 0.0
            att_r, gold_r = set(), set()
            for e in ev:
                if e['r'] > W:
                    break
                if e.get('a') == cid and e['k'] in ('attack', 'cast') and e.get('cdmg'):
                    tot = sum(x for _, x in e['cdmg'])
                    if e['k'] == 'attack':
                        basic += tot
                    else:
                        cast += tot
                    att_r.add(e['r'])
                    if all(camp_group[c] in gold_group for c, _ in e['cdmg']):
                        gold_r.add(e['r'])
            c = ch[cid]
            i = min(149, len(c['str']) - 1)
            bodies.append({'name': name[cid], 'basic': basic, 'cast': cast, 'att_rounds': len(att_r), 'str150': c['str'][i], 'foc150': c['foc'][i],
                           'maxhp150': c['maxHp'][i], 'recalls': sum(1 for r in ends.get(cid, []) if r <= W), 'gold_att_rounds': len(gold_r),
                           'gold_caps': sum(1 for r, h in shares[cid] if r <= W and h in gold_group),
                           'trib': trib_by[cid][0], 'trib_gems': trib_by[cid][1]})
        A['bodies_rows'] = bodies
        aggs.append(A)

        tot = sum(budget.values())
        all_dealt = sum(kind.values())
        sides.append({
            'camp_dps': d300 / budget['attack camp'] if budget['attack camp'] else None,
            'camp_cast_share': sum(v for k, v in kind.items() if '|cast|' in k) / all_dealt if all_dealt else None,
            'camp_vs_min_ratio': median(eff),
            'attack_share': budget['attack camp'] / tot if tot else None,
            'walk_share': sum(v for k, v in budget.items() if k.startswith('walk')) / tot if tot else None,
            'gems_per_khp': 1000 * cap_gems / d300 if d300 else None,
            'sharers': sum(x[2] for x in cap_gk.values()) / cap_n if cap_n else None,
            'trip_overhead': median(overs),
            'recall_loops': sum(1 for x in loops if x[1] <= W),
        })
    return {'sides': sides, 'agg': aggs}


def preset(map_name):
    """Generated maps (gen-<preset>-<seed>, mut-<map>-<seed>) grouped by preset; other maps stand alone."""
    m = re.match(r'^((?:gen|mut)-.+)-\d+$', map_name)
    return m.group(1) if m else map_name


def _p1(x):
    return '-' if x is None else f'{100 * x:.1f}%'


def _f(nd):
    return lambda x: '-' if x is None else str(x) if isinstance(x, int) else f'{x:.{nd}f}'


def _sum(dicts):
    out = defaultdict(float)
    for d in dicts:
        for k, v in d.items():
            out[k] += v
    return out


def _shares(d):
    tot = sum(d.values())
    return {k: v / tot for k, v in d.items()} if tot else {}


def camp_block(As):
    res = {}
    res['taken/dealt (mean per side)'] = mean([A['mdt'] / A['mdd'] for A in As if A['mdd']])
    res['taken/dealt (pooled)'] = sum(A['mdt'] for A in As) / max(1, sum(A['mdd'] for A in As))
    dealt = _sum(A['dealt_gk'] for A in As)
    taken = _sum(A['taken_gk'] for A in As)
    tot_d = sum(dealt.values())
    res['dealt_share'] = _shares(dealt)
    res['ratio_gk'] = {k: taken.get(k, 0) / v for k, v in dealt.items() if v > 0}
    res['taken_share_gk'] = _shares(taken)
    res['dealt on harmless groups'] = sum(v for k, v in dealt.items() if not set(k) & DAMAGING) / tot_d if tot_d else None
    res['cls'] = _shares(_sum(A['taken_cls'] for A in As))
    res['victim'] = _shares(_sum(A['taken_melee'] for A in As))
    dd = _sum(A['dealt_kind'] for A in As)
    allc = sum(dd.values())
    res['dealt by casts'] = sum(v for k, v in dd.items() if '|cast|' in k) / allc if allc else None
    res['dealt by melee'] = sum(v for k, v in dd.items() if k.startswith('melee')) / allc if allc else None
    res['ranged_dist'] = _shares(_sum({k.split('|')[2]: v} for k, v in dd.items() if k.startswith('ranged|attack|')))
    res['att_dist'] = {k: int(v) for k, v in _sum(A['att'] for A in As).items()}
    na = sum(A['att_n'] for A in As)
    res['own attackers per damaging episode'] = sum(A['att_sum'] for A in As) / na if na else None
    res['taken / basic-attack minimum (median)'] = median([x for A in As for x in A['eff']])
    ep = defaultdict(lambda: [0, 0.0, 0.0])
    for A in As:
        for k, v in A['ep_by'].items():
            for i in range(3):
                ep[k][i] += v[i]
    res['ep_by'] = dict(ep)
    return res


def bag_block(As):
    bags = [b for A in As for b in A['bags']]
    trips = [x for A in As for x in A['trips']]
    overs = [x for A in As for x in A['overs']]
    caps = sum(A['cap_n'] for A in As)
    return {'tributed gems at the window end': mean([A['gems300'] for A in As]), 'captured gems in the window': mean([A['cap_gems'] for A in As]),
            'captures per side': caps / len(As) if As else None,
            'sharers per capture': sum(x[2] for A in As for x in A['cap_gk'].values()) / caps if caps else None,
            'gems per capture share': mean([x for A in As for x in A['share_g']]),
            'tributes per body': mean([A['trib300'] / max(1, A['bodies']) for A in As]),
            'gems per tribute (mean)': mean(bags), 'gems per tribute (median)': median(bags), 'captures per tribute': mean([x for A in As for x in A['ncap']]),
            'altar trip, last capture to next camp attack (median)': median(trips), 'altar trip (mean)': mean(trips),
            'trip overhead over direct walk (median)': median(overs), 'trip overhead (mean)': mean(overs), 'tributes': len(bags),
            'hist': dict(Counter(str(min(b // 10 * 10, 100)) for b in bags)),
            'gk_share': _shares(_sum({k: v[1] for k, v in A['cap_gk'].items()} for A in As)),
            'side_share': _shares(_sum(A['cap_side'] for A in As)),
            'sharers_gk': _sum({k: v[2] for k, v in A['cap_gk'].items()} for A in As),
            'caps_gk': _sum({k: v[0] for k, v in A['cap_gk'].items()} for A in As)}


def recall_block(As, W):
    rows = [x for A in As for x in A['recalls']]
    cyc = [x[3] for x in rows if x[3] is not None]
    src = Counter(x[2] for x in rows)
    out = {'completed recalls per side': len(rows) / len(As) if As else None, 'hp share at start (median)': median([x[1] for x in rows]),
           'cycle: last camp attack to next (median)': median(cyc), 'cycle (mean)': mean(cyc), 'share carrying gems': mean([x[4] for x in rows])}
    for k in ('camp', 'champion', 'none'):
        out[f'share damaged by {k} in the 10 rounds before' if k != 'none' else 'share undamaged in the 10 rounds before'] = src[k] / len(rows) if rows else None
    out['loops per side'] = sum(1 for A in As for x in A['loops'] if x[1] <= W) / len(As) if As else None
    return out


def _table(rep, blocks, keys, fmt, csv=None):
    rep.table([''] + list(blocks), [[k] + [fmt(b.get(k)) for b in blocks.values()] for k in keys], csv)


def _dict_table(rep, blocks, field, fmt=_p1, order=None, limit=20, csv=None, label=''):
    tot = Counter()
    for b in blocks.values():
        for k, v in b.get(field, {}).items():
            tot[k] += v
    keys = order or [k for k, _ in tot.most_common(limit)]
    rep.table([label] + list(blocks), [[k] + [fmt(b.get(field, {}).get(k)) for b in blocks.values()] for k in keys], csv)


def _sets(ctx):
    P = ctx.params
    fname = ctx.focus or 'sources'
    focus = [(gi, t) for gi in ctx.games for t in ctx.focus_teams(gi)]
    sets, notes = {fname: focus}, []
    if ctx.focus:
        sets['opponents'] = [(gi, 1 - t) for gi, t in focus]
    if not ctx.vs_games:
        if not ctx.focus:
            sets['source winners'] = [(gi, gi['winner']) for gi in ctx.games]
        return sets, notes, fname
    vs = ctx.vs_games
    vs_maps = {gi['map'] for gi in vs}
    off = sorted({gi['map'] for gi, _ in focus} - vs_maps)
    ref = fname
    if off:
        on = [(gi, t) for gi, t in focus if gi['map'] in vs_maps]
        where = f'{len(off)} of the {len({gi["map"] for gi, _ in focus})} source maps are not in the --vs set ({", ".join(sorted({preset(m) for m in off}))})'
        if on:
            ref = f'{fname}, vs maps'
            sets[ref] = on
            notes.append(f'{where}, so the comparison with --vs is only like-for-like in the `{ref}` column ({len(on)} sides); `{fname}` and `opponents` pool every map.')
        else:
            ref = None
            notes.append(f'{where}: none of them, so the --vs columns are context only and the highlights compare with `opponents`.')
    n, w = Counter(), Counter()
    for gi in vs:
        for t in (0, 1):
            n[gi['names'][t]] += 1
            w[gi['names'][t]] += gi['winner'] == t
    top = sorted([k for k in n if n[k] >= P['econ_top_games']], key=lambda k: -w[k] / n[k])[:P['econ_top']]
    win = [(gi, t) for gi in vs for t in (0, 1) if gi['winner'] == t]
    agg = lambda gi, t: ctx.data[gi['dir']]['economy']['agg'][t]
    ratio = {(gi['dir'], t): agg(gi, t)['mdt'] / agg(gi, t)['mdd'] for gi, t in win if agg(gi, t)['mdd']}
    q = sorted(ratio.values())
    lo = q[len(q) // 4] if q else 0
    sets['vs all'] = [(gi, t) for gi in vs for t in (0, 1)]
    sets['vs winners'] = win
    if top:
        sets[f'top{len(top)}'] = [(gi, t) for gi in vs for t in (0, 1) if gi['names'][t] in top]
        sets[f'top{len(top)} wins'] = [(gi, t) for gi, t in win if gi['names'][t] in top]
        notes.append(f'top{len(top)} = the best win rates in the --vs set among teams with {P["econ_top_games"]}+ games: '
                     + ', '.join(f'{k} {w[k] / n[k]:.0%} ({n[k]})' for k in top) + '.')
    sets['low-ratio winners'] = [(gi, t) for gi, t in win if ratio.get((gi['dir'], t), 9) <= lo]
    notes.append(f'low-ratio winners = winning sides whose camp damage taken/dealt (engine statistics) is in the lowest quartile of winners (<= {lo:.3f}).')
    return sets, notes, ref


def _map_rows(sets, A, names, key, W):
    rows = []
    for m in sorted({key(gi['map']) for gi, _ in sets[names[0]]}):
        for k in names:
            ms = [(gi, a) for (gi, _), a in zip(sets[k], A[k]) if key(gi['map']) == m]
            if not ms:
                continue
            nm = len(ms)
            labels = Counter()
            for _, a in ms:
                for lab, (c, _) in a['cap_label'].items():
                    labels[lab] += c
            d300 = sum(a['dealt300'] for _, a in ms)
            att = sum(a['budget'].get('attack camp', 0) for _, a in ms)
            gems = sum(a['cap_gems'] for _, a in ms)
            nmaps = len({gi['map'] for gi, _ in ms})
            top = ', '.join(f'{lab} {v / nm:.1f}' for lab, v in labels.most_common(7)) if nmaps == 1 else f'({nmaps} maps)'
            rows.append([m, f'{k} (n={nm})', f'{sum(a["gems300"] or 0 for _, a in ms) / nm:.0f}', f'{gems / nm:.0f}', f'{1000 * gems / max(1, d300):.1f}',
                         f'{d300 / max(1, att):.0f}', f'{sum(a["trib300"] for _, a in ms) / nm:.1f}', top])
    return rows


def render(ctx, rep):
    W = ctx.params['econ_window']
    sets, notes, ref_f = _sets(ctx)
    A = {k: [ctx.data[gi['dir']]['economy']['agg'][t] for gi, t in v] for k, v in sets.items()}
    fname = next(iter(sets))
    ref = 'vs winners' if 'vs winners' in sets else None
    tops = [k for k in sets if k.startswith('top') and k.endswith(' wins')]
    shown = [k for k in dict.fromkeys([fname, ref_f, 'opponents', ref] + tops) if k in sets]
    pair = (ref_f, ref) if ref and ref_f else (fname, 'opponents') if 'opponents' in sets else None
    rep.p(f'Set: {ctx.describe()}' + (f'; comparison: {ctx.describe(vs=True)}' if ctx.vs_games else '') + '. '
          'Sides: ' + ', '.join(f'{k} {len(v)}' for k, v in sets.items()) + '. ' + ' '.join(notes),
          f'Every column pools the sides of its set (one team in one game); "per side" averages over them. Window: rounds 1-{W} unless stated. '
          'Camp handling, time use and trips are mostly about our own play; the opponent still shapes deaths, fights and contested captures '
          '(against a weak opponent we die less and fight less). The ladder is played only on its own maps, so a --vs comparison means little on generated maps '
          '(`gen-*`, `mut-*`); compare those with `opponents` or another local batch.')

    rep.h('Camp damage dealt')
    rep.p(f'Camp DPS = camp HP dealt in rounds 1-{W} per champion-round spent attacking camps (the time budget\'s `attack camp`). '
          'Gems per 1k HP = captured gems per 1000 camp HP dealt. Top captures are per game, own frame.')
    names = [k for k in (fname, 'opponents', ref) if k in sets]
    headers = ['map', 'set', f'tributed @{W}', f'captured gems @{W}', 'gems per 1k HP dealt', 'HP dealt per attack-round', f'tributes @{W}', 'top captures per game']
    per_map = _map_rows(sets, A, names, lambda m: m, W)
    n_maps = len({gi['map'] for gi, _ in sets[fname]})
    if n_maps > 12:
        rep.p(f'{n_maps} maps, so the table groups generated maps by preset (`gen-<preset>`, `mut-<map>`); per-map rows are in `economy-per_map.csv`.')
        rep.table(['preset'] + headers[1:], _map_rows(sets, A, names, preset, W))
        rep.write_csv('per_map', headers, per_map)
    else:
        rep.table(headers, per_map, 'per_map')
    rep.p(f'Per champion body, rounds 1-{W}: camp damage per round with a camp hit, cast share of it, rounds with a camp hit, '
          'Strength/Focus/max HP at round 150, completed recalls, rounds hitting only gold clusters, gold-cluster captures shared, tributes and gems tributed. '
          'Comparison sets list champions with 5+ bodies; every set is in `economy-champions.csv`.')
    csv = []
    for k in sets:
        by = defaultdict(list)
        for a in A[k]:
            for b in a['bodies_rows']:
                by[b['name']].append(b)
        rows = []
        for nm, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
            s = lambda f: sum(x[f] for x in xs)
            ar, n = s('att_rounds'), len(xs)
            row = [nm, n, f'{(s("basic") + s("cast")) / ar if ar else 0:.1f}', pct(s('cast') / max(1, s('basic') + s('cast'))), f'{ar / n:.0f}',
                   f'{s("str150") / n:.0f}', f'{s("foc150") / n:.0f}', f'{s("maxhp150") / n:.0f}', f'{s("recalls") / n:.2f}',
                   f'{s("gold_att_rounds") / n:.1f}', f'{s("gold_caps") / n:.2f}', f'{s("trib") / n:.1f}', f'{s("trib_gems") / n:.0f}']
            csv.append([k] + row)
            if k in (fname, 'opponents') or n >= 5:
                rows.append(row)
        if k in shown and k != ref_f or k == fname:
            rep.h(f'{k}: per champion', 3)
            rep.table(['champion', 'bodies', 'camp dmg per attack-round', 'cast share', 'attack rounds', 'Str@150', 'Foc@150', 'maxHP@150',
                       'completed recalls', 'gold-cluster attack rounds', 'gold-cluster captures', 'tributes', 'gems tributed'], rows)
    rep.write_csv('champions', ['set', 'champion', 'bodies', 'camp_dmg_per_attack_round', 'cast_share', 'attack_rounds', 'str150', 'foc150',
                                'maxhp150', 'recalls', 'gold_attack_rounds', 'gold_caps', 'tributes', 'gems_tributed'], csv)

    rep.h('Camp damage taken')
    cb = {k: camp_block(v) for k, v in A.items()}
    rep.p('Taken/dealt uses the engine statistics (monsterDamageTaken / monsterDamageDone), whole game; the rest is derived from events, whole game. '
          'The basic-attack minimum (camps report) is the least damage a group deals while the side clears it at its summed Strength with every member attacking '
          'until it dies. The ratio to it is taken on episodes (wake to clear or sleep) of damaging groups the side cleared alone: 1.0 is no better than standing and '
          'trading; below 1.0 needs kiting, spreading hits over several champions, or stuns.')
    _table(rep, cb, ['taken/dealt (mean per side)', 'taken/dealt (pooled)', 'taken / basic-attack minimum (median)', 'dealt on harmless groups',
                     'dealt by casts', 'dealt by melee', 'own attackers per damaging episode'], _f(3), 'camp_summary')
    rep.p('Share of camp damage dealt, by group type (W wolf, E elk, G gem, $ gold, M monolith):')
    _dict_table(rep, cb, 'dealt_share', csv='dealt_by_type', label='group')
    rep.p('Camp damage taken / dealt, by group type:')
    _dict_table(rep, cb, 'ratio_gk', fmt=_f(2), csv='ratio_by_type', label='group')
    rep.p('Share of camp damage taken, by group type:')
    _dict_table(rep, cb, 'taken_share_gk', csv='taken_by_type', label='group')
    rep.p('Share of camp damage taken, by what the victim was doing this or the previous round: attacking that group, attacking another group, '
          'standing on a claimable group, tributing, fighting a champion, walking in (attacks the group within 5 rounds), walking out (attacked it in the 5 rounds before), '
          'passing by, waiting (no move, attacks it soon) or idle in range.')
    _dict_table(rep, cb, 'cls', csv='taken_by_activity', label='victim activity')
    rep.p('Share of camp damage taken, by victim attack type:')
    _dict_table(rep, cb, 'victim', csv='taken_by_class', label='victim')
    rep.p('Ranged basic attacks on camps, share of their damage by attack distance (camps hit within 3, so every ranged basic attack is in camp range):')
    _dict_table(rep, cb, 'ranged_dist', order=['1', '2', '3'], csv='ranged_distance', label='distance')
    rep.p('Damaging-group episodes by number of own attackers (3 = 3+), then taken/dealt by group type and attackers:')
    _dict_table(rep, cb, 'att_dist', fmt=lambda x: '-' if x is None else str(x), order=['1', '2', '3'], label='attackers')
    keys = Counter()
    for b in cb.values():
        for k, x in b['ep_by'].items():
            keys[k] += x[1]
    rows = []
    for k, _ in keys.most_common(18):
        cells = []
        for b in cb.values():
            x = b['ep_by'].get(k)
            cells.append(f'{x[2] / x[1]:.2f} (n={x[0]})' if x and x[1] else '-')
        rows.append([k.replace('|', ', ')] + cells)
    rep.table(['group, attackers'] + list(cb), rows, 'ratio_by_attackers')

    rep.h(f'Time budget, rounds 1-{W}')
    rep.p('Share of champion-rounds. Each round gets the first that applies: dead, fight (damaged an enemy champion), attack camp, tribute, recall, teleport, '
          'walk, capture (standing on a claimable group), spawn idle, wait respawn (within 4 of a respawning group), stunned, idle. '
          'A run of walking rounds is labelled by what ends it (camp, altar, fight, spawn), or "to altar" if carrying gems, else "other".')
    tb = {k: _shares(_sum(a['budget'] for a in v)) for k, v in A.items()}
    cats = Counter()
    for v in tb.values():
        cats.update(v)
    rep.table([''] + list(tb), [[c] + [_p1(tb[k].get(c, 0)) for k in tb] for c, _ in cats.most_common()], 'time_budget')

    rep.h(f'Gems, captures, bags and altar trips (rounds 1-{W})')
    bb = {k: bag_block(v) for k, v in A.items()}
    rep.p('Altar trip = rounds from the last capture before a tribute to the next camp attack after it (no death in between); overhead = trip minus the direct walk '
          'from the capture position to that attack position: the detour to the altar, the tribute channel and any waiting.')
    _table(rep, bb, [k for k, v in next(iter(bb.values())).items() if not isinstance(v, dict)], _f(1), 'bags')
    rep.p('Tributes by bag size (gems, in tens; 100 = 100+):')
    _dict_table(rep, bb, 'hist', fmt=lambda x: '-' if x is None else str(x), order=[str(i) for i in range(0, 110, 10)], label='gems', csv='bag_hist')
    rep.p('Champions sharing each capture, by group type: mean (captures).')
    keys = Counter()
    for b in bb.values():
        keys.update(b['caps_gk'])
    rep.table(['group'] + list(bb), [[k] + [f'{b["sharers_gk"][k] / b["caps_gk"][k]:.2f} ({b["caps_gk"][k]:.0f})' if b['caps_gk'].get(k) else '-'
                                            for b in bb.values()] for k, _ in keys.most_common(15)], 'sharers')
    rep.p('Share of captured gems, by group type and by side (own frame):')
    _dict_table(rep, bb, 'gk_share', csv='captured_by_type', label='group')
    _dict_table(rep, bb, 'side_share', order=['own', 'mid', 'enemy'], label='side')

    rep.h('Shards bought')
    rep.p('Shards bought per champion over the whole game (an emblem counts as its 5 shards, 25 for Greed) and the share of each kind; every set is in `economy-shards.csv`.')
    csv = []
    for k in sets:
        sh = defaultdict(Counter)
        for a in A[k]:
            for c, d in a['shards'].items():
                sh[c].update(d)
        lines = []
        for c, d in sorted(sh.items(), key=lambda x: -sum(x[1].values())):
            tot = sum(d.values())
            if tot:
                lines.append(f'{c} ({tot}): ' + ', '.join(f'{it.replace(" Shard of ", " ")} {v / tot:.0%}' for it, v in d.most_common(5)))
                csv += [[k, c, it, v] for it, v in d.most_common()]
        if k in shown and k != ref_f or k == fname:
            rep.p(f'**{k}**:')
            rep.bullets(lines or ['(none)'])
    rep.write_csv('shards', ['set', 'champion', 'shard', 'count'], csv)

    rep.h(f'Recalls (completed in rounds 1-{W})')
    rb = {k: recall_block(v, W) for k, v in A.items()}
    rep.p('Cycle = rounds from the last camp attack before the recall started to the first camp attack after arrival. '
          f'Loop = a recall that arrives under {LOOP_HP:.0%} hp and is followed by another recall arrival within {LOOP_GAP} rounds '
          '(the arrival turn left spawn before the turn-end heal). It is a regression check for our bot and must stay 0.')
    _table(rep, rb, list(next(iter(rb.values()))), _f(2), 'recalls')
    by_team = defaultdict(list)
    for gi in ctx.games:
        for t in (0, 1):
            by_team[gi['names'][t]].append([(gi, x) for x in ctx.data[gi['dir']]['economy']['agg'][t]['loops']])
    rows = []
    for team, ls in sorted(by_team.items(), key=lambda kv: (kv[0] != ctx.focus, kv[0])):
        flat = [y for x in ls for y in x]
        rows.append([team, len(ls), sum(1 for _, x in flat if x[1] <= W), len(flat)])
    rep.p('Loops per team in the sources:')
    rep.table(['team', 'sides', f'loops in rounds 1-{W}', 'loops in whole games'], rows, 'recall_loops')
    for team, sides_, n300, nall in rows:
        if ctx.focus and team != ctx.focus:
            continue
        flat = [y for x in by_team[team] for y in x]
        if flat:
            rep.p(f'{team}:')
            rep.bullets([f'{gi["dir"]} r{x[0]}-r{x[1]} {gi["map"]} {x[2]}' for gi, x in flat[:30]])
        rep.highlight(f'Recall-loop check ({team}): {n300} in rounds 1-{W}, {nall} in whole games'
                      + ((' (REGRESSION: must be 0).' if n300 else ' (ok).') if ctx.focus else '.'))

    if pair:
        ref_f, ref = pair
        f, r = cb[ref_f], cb[ref]
        rep.highlight(f'Camp taken/dealt: {ref_f} {f["taken/dealt (pooled)"]:.3f} vs {ref} {r["taken/dealt (pooled)"]:.3f} (pooled); actual / basic-attack minimum '
                      f'{_f(2)(f["taken / basic-attack minimum (median)"])} vs {_f(2)(r["taken / basic-attack minimum (median)"])}; casts deal '
                      f'{_p1(f["dealt by casts"])} vs {_p1(r["dealt by casts"])} of camp damage.')
        dps = lambda As: sum(a['dealt300'] for a in As) / max(1, sum(a['budget'].get('attack camp', 0) for a in As))
        walk = lambda k: sum(v for c, v in tb[k].items() if c.startswith('walk'))
        rep.highlight(f'Camp DPS (HP per attack-round, r1-{W}): {ref_f} {dps(A[ref_f]):.0f} vs {ref} {dps(A[ref]):.0f}; time attacking camps '
                      f'{_p1(tb[ref_f].get("attack camp"))} vs {_p1(tb[ref].get("attack camp"))}, walking {_p1(walk(ref_f))} vs {_p1(walk(ref))}.')
        fb, rb_ = bb[ref_f], bb[ref]
        rep.highlight(f'Bags and trips (r1-{W}): {ref_f} {_f(1)(fb["gems per tribute (mean)"])} gems per tribute, {_f(1)(fb["tributes per body"])} tributes per body, '
                      f'trip overhead median {_f(0)(fb["trip overhead over direct walk (median)"])} rounds; {ref} {_f(1)(rb_["gems per tribute (mean)"])}, '
                      f'{_f(1)(rb_["tributes per body"])}, {_f(0)(rb_["trip overhead over direct walk (median)"])}.')
