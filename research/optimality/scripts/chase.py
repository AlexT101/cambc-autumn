# Chase streaks: >= 3 consecutive own turns approaching the same visible enemy that starts each turn outside
# the chaser's one-turn basic reach (melee 2, ranged 3). Outcome: did the chaser damage it during the streak
# or the 3 rounds after; did the target keep its distance (fled) or let it shrink (anchored)?
import json, gzip, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT = r'C:\Users\alext\Github\cambc-autumn\replays\.analysis'
MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Issac'}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def game(d):
    try:
        m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
        ev = [json.loads(l) for l in gzip.open(os.path.join(ROOT, d, 'events.jsonl.gz'), 'rt')]
        R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
    except Exception:
        return []
    idxj_teams = None
    champs = m['champions']; ids = [c['id'] for c in champs]
    name = {c['id']: c['name'] for c in champs}; team = {c['id']: c['team'] for c in champs}
    idx = {c['id']: i for i, c in enumerate(champs)}
    rix = {r: i for i, r in enumerate(R['round'])}
    ev.sort(key=lambda e: e['s'])
    byround = collections.defaultdict(list)
    for e in ev: byround[e['r']].append(e)
    hits = collections.defaultdict(set)  # (a, v) -> rounds with damage
    for e in ev:
        if e['k'] in ('attack', 'cast'):
            for v, a in (e.get('dmg') or []):
                if v in team and team[v] != team[e['a']] and a > 0: hits[(e['a'], v)].add(e['r'])
    def order(r):
        pi = rix.get(r - 1)
        key = lambda c: (-(R['champions'][idx[c]]['prio'][pi] if pi is not None else 0), c)
        A = sorted([c for c in ids if team[c] == 0], key=key); B = sorted([c for c in ids if team[c] == 1], key=key)
        f, s = (A, B) if r % 2 == 1 else (B, A)
        seq = []
        for i in range(max(len(A), len(B))):
            if i < len(f): seq.append(f[i])
            if i < len(s): seq.append(s[i])
        return {c: k for k, c in enumerate(seq)}
    # positions at the start and end of each champion's turn
    start = {}; end = {}
    cur = {}
    nmax = R['round'][-1]
    for r in range(1, nmax + 1):
        i = rix.get(r - 1)
        if i is not None:
            for c in ids:
                ch = R['champions'][idx[c]]
                cur[c] = (ch['x'][i], ch['y'][i]) if ch['alive'][i] else None
        o = order(r); inv = {k: c for c, k in o.items()}
        es = byround.get(r, []); j = 0
        for t in range(len(ids)):
            c = inv.get(t)
            snap0 = dict(cur)
            while j < len(es) and es[j]['t'] <= t:
                e = es[j]; j += 1
                k = e['k']; a = e.get('a')
                if k == 'move': cur[a] = tuple(e['to'])
                elif k == 'cast' and e.get('moved'): cur[a] = tuple(e['moved'])
                elif k in ('recall_end', 'teleport_end'): cur[a] = tuple(e['to'])
                elif k == 'respawn': cur[a] = tuple(e['at'])
                elif k == 'death': cur[e['v']] = None
            if c is not None:
                start[(c, r)] = snap0; end[(c, r)] = dict(cur)
    out = []
    for c in ids:
        R1 = 2 if name[c] in MELEE else 3
        streak = None
        for r in range(1, nmax + 1):
            i = rix.get(r)
            s0 = start.get((c, r)); s1 = end.get((c, r))
            ok = False
            if s0 and s1 and i is not None and s0.get(c) and s1.get(c):
                seen = R['champions'][idx[c]]['sees'][i]
                cand = [(cheb(s0[c], s0[e]), e) for e in seen if s0.get(e)]
                if cand:
                    d0, e = min(cand)
                    if R1 < d0 <= 8 and s1.get(e) and cheb(s1[c], s1[e]) < d0:
                        ok = True
                        if streak and streak['e'] == e and streak['last'] == r - 1:
                            streak['last'] = r; streak['n'] += 1; streak['dlast'] = d0
                        else:
                            if streak and streak['n'] >= 3: out.append(streak)
                            streak = {'c': c, 'e': e, 'first': r, 'last': r, 'n': 1, 'd0': d0, 'dlast': d0}
            if not ok and streak and streak['last'] < r - 0:
                if streak['n'] >= 3: out.append(streak)
                streak = None
        if streak and streak['n'] >= 3: out.append(streak)
    res = []
    tnames = [m['teams'][0]['name'], m['teams'][1]['name']]
    for s in out:
        hit = any(s['first'] <= r <= s['last'] + 3 for r in hits[(s['c'], s['e'])])
        fled = s['dlast'] >= s['d0']
        res.append((tnames[team[s['c']]], name[s['c']] in MELEE, s['n'], fled, hit))
    return res


if __name__ == '__main__':
    idxj = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
    games = [g for g in idxj['games'] if g['kind'] == 'ladder' and g['ok'] and g['source'].split('/')[2][:8] >= '20261016']
    dirs = sorted({g['dir'] for g in games})[:int(sys.argv[1])]
    rows = []
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(game, dirs, chunksize=4): rows += r
    def show(label, rs):
        if not rs: return
        f = [r for r in rs if r[3]]; a = [r for r in rs if not r[3]]
        print(f'{label:22s} streaks {len(rs):6d}  target kept distance: {len(f)/len(rs):.2f} -> hit {sum(r[4] for r in f)/max(1,len(f)):.2f} | target let us close: hit {sum(r[4] for r in a)/max(1,len(a)):.2f}')
    show('ALL', rows)
    for t in ['Intercontinental Fish', 'Mite', 'Sneaky Bush Campers', 'Univardisty of Shingtonwash', 'procless', 'PTN Hyperion']:
        show(t, [r for r in rows if r[0] == t])
