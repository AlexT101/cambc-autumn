"""Lethal exposure to an enemy Prism at the end of each body's own turn.

A body is lethal-exposed at the end of its turn when an enemy Prism, from where it stands then, can kill it on
its next turn (which comes before the body's next turn), by its cooldowns at that turn's start:
  ground ready, d <= 5, hp <= F;  stun ready, d <= 4, hp <= 1.5F;  stun and ground ready, d <= 4, hp <= 2.5F
  (the stun removes the body's next turn, so the ground spell lands from the same tile the turn after).
For Cassi & Issac each body counts by its own hp (either death kills both).

Per exposure: the body's branch letter that turn (D lines), whether it walked in (its distance at turn start
was outside the lethal reach), whether the Prism walked in since the body's previous turn end, whether the
body saw the Prism at its turn start, and whether it (or its pair) died before its next turn ended.

usage: lethal.py OUT.json DIR... (extracted dirs or a replays/.xxx root; teams named in meta)
"""
import gzip, json, sys, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dlines(src):
    """{team: {(round, id): letter}} from the replay zip's stdouts."""
    out = {0: {}, 1: {}}
    try:
        z = zipfile.ZipFile(src)
    except Exception:
        return None
    for team, name in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        try:
            data = z.read(name).decode('utf-8', 'replace')
        except KeyError:
            continue
        for line in data.splitlines():
            if line.startswith('D '):
                p = line.split()
                if len(p) >= 4:
                    out[team][(int(p[1]), int(p[2]))] = p[3]
            elif line.startswith('LX '):
                p = line.split()
                if len(p) >= 17 and all(v.lstrip('-').isdigit() for v in p[4:]):
                    out[team].setdefault('LX', {})[(int(p[1]), int(p[2]))] = [p[3]] + [int(v) for v in p[4:]]
    return out


def lethal_kind(d, hp, F, stun, ground):
    if stun and ground and d <= 4 and hp <= 2.5 * F: return 'lock' if hp > 1.5 * F else 'stun'
    if stun and d <= 4 and hp <= 1.5 * F: return 'stun'
    if ground and d <= 5 and hp <= F: return 'ground'
    return None


def reach_of(kind): return 5 if kind == 'ground' else 4


def one(d):
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    D = dlines(meta['source']) or {0: {}, 1: {}}
    names = [t['name'] for t in meta['teams']]
    C = R['champions']
    col = {c['id']: c for c in C}
    typ = {c['id']: c['name'] for c in meta['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    ids = [c['id'] for c in C]
    N = len(R['round'])
    prisms = {t: [c for c in ids if typ[c] == 'Prism' and team[c] == t] for t in (0, 1)}
    partner = {}
    for c in ids:
        if typ[c] in ('Cassi', 'Issac'):
            for o in ids:
                if o != c and team[o] == team[c] and typ[o] in ('Cassi', 'Issac'): partner[c] = o
    by_round = defaultdict(list)
    for e in ev: by_round[e['r']].append(e)
    first_kill = None
    deaths = defaultdict(list)  # id -> [(r, s, by)]
    for e in ev:
        if e['k'] == 'death':
            deaths[e['v']].append((e['r'], e['s'], e.get('by'), e.get('linked')))
            if first_kill is None and not e.get('linked') and e.get('by') in typ: first_kill = e['r']
    if first_kill is None: first_kill = 10 ** 9

    def slots(r):
        i = max(r - 2, 0)
        order = []
        for t in (0, 1):
            tid = [c for c in ids if team[c] == t]
            order.append(sorted(tid, key=lambda x: (-col[x]['prio'][i] if r > 1 else 0, x)))
        a, b = (order[0], order[1]) if r % 2 == 1 else (order[1], order[0])
        seq = []
        for k in range(max(len(a), len(b))): seq += a[k:k + 1] + b[k:k + 1]
        return seq

    def at(c, key, r):  # end of round r
        return col[c][key][min(max(r, 1), N) - 1]

    def endpos(c, r):
        i = min(r, N) - 1
        cc = col[c]
        return (cc['x'][i], cc['y'][i]) if cc['alive'][i] and cc['x'][i] is not None else None

    out = []
    prev_end = {}  # (body, prism) -> prism pos at body's previous turn end
    for r in range(2, N + 1):
        seq = slots(r)
        slot = {c: k for k, c in enumerate(seq)}
        pos = {c: endpos(c, r - 1) for c in ids}
        hp = {c: at(c, 'hp', r - 1) for c in ids}
        evs = by_round[r]
        j = 0
        # round phases (t = -1) first
        bys = defaultdict(list)
        for e in evs: bys[e['t']].append(e)

        now = [-1]

        def apply(e):
            now[0] = max(now[0], e['s'])
            k = e['k']
            if k == 'move': pos[e['a']] = tuple(e['to'])
            elif k == 'cast' and e.get('moved'): pos[e['a']] = tuple(e['moved'])
            elif k in ('respawn', 'recall_end', 'teleport_end'): pos[e['a']] = tuple(e.get('at') or e.get('to'))
            elif k == 'death': pos[e['v']] = None
            if k == 'camp_attack':
                if e.get('tgt') in hp and isinstance(e.get('dmg'), (int, float)): hp[e['tgt']] -= e['dmg']
                for t in e.get('xdmg') or []:
                    if isinstance(t, list) and t and t[0] in hp: hp[t[0]] -= t[1]
            else:
                for t in e.get('dmg') or []:
                    if isinstance(t, list) and t and t[0] in hp: hp[t[0]] -= t[1]
                if isinstance(e.get('refl'), (int, float)) and e.get('a') in hp: hp[e['a']] -= e['refl']
            for t in e.get('heal') or []:
                if isinstance(t, list) and t and t[0] in hp: hp[t[0]] += t[1]
        for e in bys.get(-1, []): apply(e)
        for k, x in enumerate(seq):
            start = pos.get(x)
            for e in bys.get(k, []): apply(e)
            here = pos.get(x)
            if here is None or start is None or at(x, 'turn', r) not in (1, 2): continue
            if True:
                for p in prisms[1 - team[x]]:
                    pp = pos.get(p)
                    if pp is None: continue
                    dd = cheb(here, pp)
                    if dd > 7: prev_end.pop((x, p), None); continue
                    # Prism's next turn: this round if later in the order, else next round
                    nr = r if slot[p] > k else r + 1
                    if nr > N: continue
                    snap = nr - 1  # end of round before its next turn
                    cd0, cd1, F = at(p, 'cd0', snap), at(p, 'cd1', snap), at(p, 'foc', snap)
                    if at(p, 'turn', nr) in (5, 4): prev_end[(x, p)] = pp; continue
                    stun, ground = cd0 == 0, cd1 == 0
                    h = hp[x]
                    kind = lethal_kind(dd, h, F, stun, ground)
                    pe = prev_end.get((x, p))
                    prev_end[(x, p)] = pp
                    if dd > 5: continue
                    rec = {'r': r, 'team': team[x], 'name': names[team[x]], 'x': typ[x], 'd': dd, 'hp': round(h),
                           'F': round(F), 'stun': stun, 'ground': ground, 'kind': kind, 'pre': r < first_kill}
                    if kind is None:
                        rec['lethal'] = False
                    else:
                        rec['lethal'] = True
                        rec['walked_in'] = cheb(start, pp) > reach_of(kind)
                        rec['moved'] = start != here
                        rec['p_in'] = pe is not None and cheb(here, pe) > reach_of(kind) if pe else None
                        rec['seen'] = p in (at(x, 'sees', r) or [])
                        rec['br'] = D[team[x]].get((r, x), '?')
                        rec['gems'] = at(x, 'gems', r)
                        rec['pchan'] = at(p, 'chan', snap); rec['pgems'] = at(p, 'gems', snap)
                        rec['lx'] = D[team[x]].get('LX', {}).get((r, x))
                    # death before its next turn ends: this round after now, or next round
                    died = None
                    for (dr, ds, by, linked) in deaths[x]:
                        if (dr == r and ds > now[0]) or dr == r + 1:
                            died = (dr, typ.get(by, 'camp') if by is not None else 'camp', bool(linked))
                            break
                    rec['died'] = died is not None
                    rec['killer'] = died[1] if died else None
                    out.append(rec)
    return {'src': meta['source'], 'name': names, 'ok': True, 'winner': meta['result']['winner'], 'recs': out, 'first_kill': first_kill, 'N': N,
            'deaths': [{'v': typ[e['v']], 'team': team[e['v']], 'r': e['r'], 'by': typ.get(e.get('by'), 'camp'), 'linked': bool(e.get('linked'))}
                       for e in ev if e['k'] == 'death'],
            'gems': {t: sum(s[1] for e in ev if e['k'] == 'capture' for s in e['shares'] if team.get(s[0]) == t) for t in (0, 1)}}


def main():
    outp = sys.argv[1]
    dirs = []
    for a in sys.argv[2:]:
        p = Path(a)
        if (p / 'meta.json').exists(): dirs.append(p)
        else: dirs += [q for q in p.iterdir() if (q / 'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex:
        res = [g for g in ex.map(one, dirs, chunksize=4) if g]
    json.dump(res, open(outp, 'w'))
    print(len(res), 'games')


if __name__ == '__main__':
    main()
