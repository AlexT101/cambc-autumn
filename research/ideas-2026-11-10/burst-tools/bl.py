"""Burst exposure in decoded replays (tools/replay/extract.mjs output).

At every turn end of one of our champions V, the burst each enemy E could land on V before V's next
turn, from E's real Strength, Focus, cooldowns and emblems, the distance (walls ignored: an upper
bound), and the real turn order (E's turns between V's turn and V's next). Records V's health then,
the burst B (all enemies) and Bv (enemies V sees), the spell part, and whether V died before its
next turn to an enemy champion.

Usage: bl.py SRC [--lo 2026-11-09T12] [--out FILE] [--n N]
  SRC: mite (miteRE/ana, games vs us), fish (fishre/ana2 vs us), or a local ana dir (LOCAL:<dir>,
  our bot = team A in -12 batches).
Output: pickle of per-turn rows (compact tuples) and per-death rows.
"""
import gzip, json, os, sys, glob, csv, pickle, collections
from multiprocessing import Pool

US = 'stellar best girl'
H = os.path.expanduser('~')

# name: (ranged, abilities [(kind, mult, stuns, excl)])
K = {
    'Ryth': (False, [('ground', 1.0, True, True), ('reset', 0, False, False)]),
    'Vesper Vale': (True, [('reset', 0, False, False), ('dash', 0, False, False)]),
    'Prism': (True, [('unit', 1.5, True, True), ('ground', 1.0, False, True)]),
    'Stellar': (True, [('unit', 2.0, False, True), ('ground', 1.4, False, True)]),
    'Vendetta': (False, [('reset', 0, False, False), ('dash', 0, False, False)]),
    'Marcella': (False, [('reset', 0, True, False), ('unit', 2.0, False, True)]),
    'Tavi': (True, [('reset', 0, False, False), ('unit', 1.6, True, True)]),
    'Willow': (True, [('heal', 0, False, False), ('reset', 0, False, False)]),
    'Ren': (False, [('unit', 1.1, True, True), ('dash', 0, False, False)]),
    'Varg': (False, [('reset', 0, False, False), ('shield', 0, False, False)]),
    'Heart of Ruin': (False, [('shield', 0, False, False), ('land', 1.5, True, False)]),
    'Cassi': (True, [('unit', 2.0, False, True), ('stun', 0, True, False)]),
    'Issac': (False, [('reset', 0, False, False), ('dash', 0, False, False)]),
}


def one_turn(name, S, F, d, ready, scale=1.0):
    """Most damage E deals at Chebyshev distance d in one turn, (total, spell part)."""
    ranged, ab = K[name]
    basic = 3 if ranged else 1
    w = 0 if ranged else 1
    best = (S if d <= basic + w else 0.0, 0.0)
    def up(v, sp):
        nonlocal best
        if v > best[0]: best = (v, sp)
    for s in (0, 1):
        if not ready[s]: continue
        kind, m, _, _ = ab[s]
        if kind == 'reset':
            if d <= basic + w: up(2 * S, 0)
            if ranged and d <= basic + 1: up(S, 0)
        elif kind == 'dash':
            if d <= basic + w + 2: up(S, 0)
        elif kind == 'unit':
            if d <= 4: up(m * F, m * F)
            if d <= basic: up(m * F + S, m * F)
        elif kind == 'ground':
            if d <= 5: up(m * F, m * F)
            if d <= basic: up(m * F + S, m * F)
        elif kind == 'land':
            if d <= w + 3: up(m * F + S, m * F)
    return best[0] * scale, best[1] * scale


def window_burst(name, S, F, d, ready, turns, scale=1.0):
    if turns <= 0: return 0.0, 0.0
    t, sp = one_turn(name, S, F, d, ready, scale)
    if turns >= 2 and d >= 1:
        # Two turns: a walk on the first, then anything from a tile nearer (a spell's reach one longer).
        t2, sp2 = one_turn(name, S, F, d - 1, ready, scale)
        if t2 > t: t, sp = t2, sp2
    if turns >= 2:
        ranged, _ = K[name]
        basic = 3 if ranged else 1
        # A second turn: a step closer and a basic attack (spells stay on cooldown).
        if d <= basic + (0 if ranged else 2): t += S * scale
    return t, sp


def emblems(items):
    fams = set(); emb = set()
    for j in range(0, len(items), 2):
        i, n = items[j], items[j + 1]
        if n <= 0: continue
        if i % 2 == 1: fams.add(i // 6)
    return fams


def dealt(fams):
    m = 1.1 if 11 in fams else 1.0
    if 13 in fams: m *= 1 + 0.01 * len(fams)
    return m


def taken(fams):
    return 0.9 if 2 in fams else 1.0


def hor_scale(name, hp, mx):
    return 1 + 0.5 * (1 - hp / mx) if name == 'Heart of Ruin' and mx > 0 else 1.0


def analyse(g):
    d = g['dir']
    meta = json.load(open(f'{d}/meta.json'))
    rd = json.load(gzip.open(f'{d}/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(f'{d}/events.jsonl.gz', 'rt')]
    us = g['us']
    R = rd['round']; idx = {r: i for i, r in enumerate(R)}
    C = {c['id']: c for c in rd['champions']}
    nm = {c['id']: c['name'] for c in meta['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    ids = sorted(C)
    ours = [c for c in ids if team[c] == us]; theirs = [c for c in ids if team[c] != us]
    byr = collections.defaultdict(list)
    for e in ev: byr[e['r']].append(e)
    # Slot of each champion per round: from its events; others filled by team parity.
    rows = []; deaths = []
    fam_cache = {}
    def fams(c, i):
        key = (c, json.dumps(C[c]['items'][i]))
        if key not in fam_cache: fam_cache[key] = emblems(C[c]['items'][i])
        return fam_cache[key]
    nteam = {0: sum(team[c] == 0 for c in ids), 1: sum(team[c] == 1 for c in ids)}
    def slots_of(r):
        sl = {}
        for e in byr.get(r, []):
            if 'a' in e and e.get('t', -1) >= 0 and e['a'] in C: sl.setdefault(e['a'], e['t'])
        # Team slot sets: alternate, A first in odd rounds; the bigger team's extras at the end.
        first = 0 if r % 2 == 1 else 1
        n = len(ids); seq = []; a = b = 0
        order = [first, 1 - first]
        cnt = {0: 0, 1: 0}
        k = 0
        while len(seq) < n:
            tm = order[k % 2]
            if cnt[tm] < nteam[tm]: seq.append(tm); cnt[tm] += 1
            elif cnt[1 - tm] < nteam[1 - tm]: seq.append(1 - tm); cnt[1 - tm] += 1
            k += 1
        for tm in (0, 1):
            free = [s for s, x in enumerate(seq) if x == tm and s not in sl.values()]
            rest = [c for c in ids if team[c] == tm and c not in sl]
            i = idx.get(r - 1)
            rest.sort(key=lambda c: (-(C[c]['prio'][i] if i is not None else 0), c))
            for c, s in zip(rest, free): sl[c] = s
        return sl
    slot_cache = {}
    def slots(r):
        if r not in slot_cache: slot_cache[r] = slots_of(r)
        return slot_cache[r]
    death_at = collections.defaultdict(list)  # victim -> [(round, slot of killing turn, event)]
    for e in ev:
        if e['k'] == 'death': death_at[e['v']].append(e)
    for r in R[1:]:
        i0 = idx[r - 1]; i1 = idx[r]
        if r + 1 not in idx: break
        sl = slots(r); sl2 = slots(r + 1)
        pos = {c: (C[c]['x'][i0], C[c]['y'][i0]) for c in ids}
        hp = {c: C[c]['hp'][i0] for c in ids}
        alive = {c: C[c]['alive'][i0] for c in ids}
        cast_r = set()  # (c, slot) cast this round
        evs = sorted(byr.get(r, []), key=lambda e: e['s'])
        k = 0
        # Walk slots in order; at the end of each of our champions' slots, record.
        for t in range(len(ids)):
            while k < len(evs) and (evs[k].get('t', -1) <= t):
                e = evs[k]; k += 1
                kk = e['k']
                if kk == 'move' or kk == 'recall_end' or kk == 'teleport_end': pos[e['a']] = tuple(e['to'])
                elif kk == 'cast':
                    cast_r.add((e['a'], e['slot']))
                    if e.get('moved'): pos[e['a']] = tuple(e['moved'])
                elif kk == 'respawn': pos[e['a']] = tuple(e['at']); alive[e['a']] = 1; hp[e['a']] = C[e['a']]['maxHp'][i1]
                elif kk == 'death': alive[e['v']] = 0
                if kk == 'camp_attack':
                    if e.get('tgt') in hp: hp[e['tgt']] -= e.get('dmg', 0)
                else:
                    for x, amt in e.get('dmg', []) or []:
                        if x in hp: hp[x] -= amt
                    for x, amt in e.get('heal', []) or []:
                        if x in hp: hp[x] += amt
            for v in ours:
                if sl.get(v) != t or not alive[v] or C[v]['x'][i0] is None or not C[v]['alive'][i0]: continue
                if pos[v][0] is None: continue
                # Window: enemy turns after (r, t) and before V's next turn (r+1, sl2[v]).
                tv2 = sl2.get(v, 99)
                vh = hp[v] + C[v]['shield'][i0]
                if vh <= 0: continue
                tk = taken(fams(v, i0))
                B = Bv = Sp = 0.0; near = []
                sees = set(C[v]['sees'][i1] or []) | set(C[v]['sees'][i0] or [])
                for e_ in theirs:
                    if not alive[e_] or pos[e_][0] is None: continue
                    dd = max(abs(pos[e_][0] - pos[v][0]), abs(pos[e_][1] - pos[v][1]))
                    if dd > 8: continue
                    n1 = 1 if sl.get(e_, -1) > t else 0
                    n2 = 1 if sl2.get(e_, 99) < tv2 else 0
                    turns = n1 + n2
                    cd = (C[e_]['cd0'][i0], C[e_]['cd1'][i0])
                    # Ready at its first window turn: in round r if cd 0 at r-1's end and not cast
                    # earlier this round; in round r+1 if cd <= 1.
                    ready = tuple(((cd[s] <= 0) if n1 else (cd[s] <= 1)) and (e_, s) not in cast_r for s in (0, 1))
                    sc = dealt(fams(e_, i0)) * hor_scale(nm[e_], hp[e_], C[e_]['maxHp'][i0]) * tk
                    b, sp = window_burst(nm[e_], C[e_]['str'][i0], C[e_]['foc'][i0], dd, ready, turns, sc)
                    B += b; Sp += sp
                    vis = e_ in sees
                    if vis: Bv += b
                    ball, _ = window_burst(nm[e_], C[e_]['str'][i0], C[e_]['foc'][i0], dd, (True, True), turns, sc)
                    near.append((nm[e_], dd, round(b), round(sp), int(vis), turns, ready[0], ready[1], round(C[e_]['foc'][i0]), e_, pos[e_], round(ball), cd, C[e_]['str'][i0], C[e_]['foc'][i0], sc))
                if not near: continue
                # Died before its next turn, to an enemy champion?
                died = None
                for de in death_at.get(v, []):
                    if (de['r'] == r and de['t'] > t) or (de['r'] == r + 1 and de['t'] < tv2):
                        died = de
                kill = died is not None and died.get('by') is not None and team.get(died['by']) != us
                rows.append((r, nm[v], round(vh), round(C[v]['maxHp'][i0]), round(B), round(Bv), round(Sp), int(kill),
                             nm[died['by']] if kill else '', died.get('cause', '') if died else '', C[v]['gems'][i0], tuple(near), v, pos[v]))
    # All deaths of ours to enemy champions (some never show a window row: e.g. unseen positions).
    for v in ours:
        for de in death_at.get(v, []):
            if de.get('by') is not None and team.get(de['by']) != us:
                deaths.append((de['r'], nm[v], nm[de['by']], de.get('cause', ''), de.get('hp'), de.get('gems', 0), 'linked' in de))
    return {'g': g['mid'], 'win': g['win'], 'rows': rows, 'deaths': deaths, 'n': len(R)}


def games(src, lo):
    out = []
    if src == 'mite':
        A = f'{H}/tmp-offload/miteRE/ana'
        G = [json.loads(l) for l in open(f'{H}/tmp-offload/miteRE/feats.jsonl')]
        G = list({x['mid']: x for x in G if 'err' not in x}.values())
        for x in G:
            if x['cr'] >= lo and x['opp'] == US:
                out.append({'dir': f"{A}/{x['dir']}", 'us': 1 - x['ms'], 'mid': x['mid'], 'win': not x['mwin'], 'opp': 'mite'})
    elif src == 'fish':
        rows = {}
        for r in csv.DictReader(open(f'{H}/tmp-offload/oppre/replays/fish/list.tsv'), delimiter='\t'): rows[r['match_id']] = r
        for m in sorted(glob.glob(f'{H}/tmp-offload/fishre/ana2/*/meta.json')):
            mm = json.load(open(m)); mid = os.path.basename(mm['source']).split('.')[0]
            r = rows.get(mid)
            if not r or r['opponent'] != US or r['created_at'] < lo: continue
            fs = 0 if r['fish_side'] == 'a' else 1
            out.append({'dir': os.path.dirname(m), 'us': 1 - fs, 'mid': mid, 'win': r['fish_result'] != 'win', 'opp': 'fish'})
    elif src.startswith('LOCAL:'):
        for m in sorted(glob.glob(f'{src[6:]}/*/meta.json')):
            mm = json.load(open(m)); base = os.path.basename(mm['source']).split('.')[0]
            us = 0 if base.endswith('-12') else 1
            out.append({'dir': os.path.dirname(m), 'us': us, 'mid': base, 'win': mm['result']['winner'] == us, 'opp': 'local'})
    return out


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('--lo', default='2026-11-09T12'); ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=0); ap.add_argument('-j', type=int, default=8)
    a = ap.parse_args()
    G = games(a.src, a.lo)
    if a.n: G = G[:a.n]
    res = []
    with Pool(a.j) as p:
        for o in p.imap_unordered(analyse, G, chunksize=2): res.append(o)
    pickle.dump(res, open(a.out, 'wb'))
    print(len(res), 'games ->', a.out)
