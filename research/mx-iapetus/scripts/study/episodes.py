"""Farm-target episodes in the farm-break windows: runs of F-branch turns on one farm group per champion (gaps <= 3
rounds merged), each with its rounds by class, the group's side, and how it ended. Plus retreat-branch turns.
Writes /tmp/mxi-study/episodes.jsonl."""
import json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '/home/ubuntu/wt/mx-iapetus/tools/replay')
sys.path.insert(0, '/tmp/mxi-study')
from analysis.data import Game, chebyshev  # noqa
from analysis import macro  # noqa
from farmwin import read_trace, CLUSTER  # noqa


def work(row):
    d, w0, w1 = row['dir'], row['w0'], row['w1']
    g = Game(d)
    mp, n, R = g.map, g.n_rounds, g.rounds
    Wt = g.winner
    role = {Wt: 'W', 1 - Wt: 'L'}
    cls = macro.classify(g)
    fields = macro.group_fields(mp)
    H = mp.H
    tr = read_trace(g.meta['source'])
    champs = R['champions']
    team_of, name_of = g.team_of, g.name_of
    gmeta = {grp['id']: grp for grp in mp.groups}
    camp_group = {c['id']: c['group'] for c in mp.camps}
    sp = []
    for t in (0, 1):
        s = mp.spawn[t]
        sp.append([(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)])
    gd = {gid: [min(fields[gid][x * H + y] for x, y in sp[t]) for t in (0, 1)] for gid in gmeta}

    def rel(gid, t):
        a, b = gd[gid][t], gd[gid][1 - t]
        if abs(a - b) <= max(2, 0.1 * (a + b)):
            return 'mid'
        return 'own' if a < b else 'enemy'
    caps = defaultdict(list)  # gid -> [(r, team, {cid: gems})]
    hits = defaultdict(set)   # (cid, gid) -> rounds hit
    for e in g.events:
        if e['k'] == 'capture':
            caps[e['g']].append((e['r'], e['team'], {s[0]: s[1] for s in e['shares']}, sum(s[1] for s in e['shares'])))
        elif e['k'] in ('attack', 'cast') and e.get('cdmg') and e.get('camp') is not None:
            hits[(e['a'], camp_group.get(e['camp']))].add(e['r'])
    dmg = g.damaged_rounds
    pos = lambda c, i: (c['x'][i], c['y'][i]) if c['alive'][i] and c['x'][i] is not None else None
    eps = []
    for c in champs:
        cid = c['id']
        t = team_of[cid]
        enemies = [cc for cc in champs if cc['team'] != t]
        runs = []
        cur = None
        for r in range(w0, w1 + 1):
            b = tr.get((cid, r))
            if b and b[0] == 'F' and b[1] >= 0 and cls[cid][r] != 'dead':
                if cur and cur['g'] == b[1] and r - cur['end'] <= 4:
                    cur['end'] = r
                else:
                    if cur: runs.append(cur)
                    cur = {'g': b[1], 'start': r, 'end': r}
        if cur: runs.append(cur)
        for ru in runs:
            gid, a, z = ru['g'], ru['start'], ru['end']
            cc = Counter(cls[cid][r] for r in range(a, z + 1))
            # outcome
            own_cap = [x for x in caps[gid] if a <= x[0] <= z + 3 and x[1] == t]
            mine = sum(x[2].get(cid, 0) for x in own_cap)
            en_cap = [x for x in caps[gid] if a <= x[0] <= z + 15 and x[1] != t]
            nxt = None
            for r in range(z + 1, min(n, z + 4) + 1):
                if cls[cid][r] == 'dead':
                    nxt = 'dead'; break
                b = tr.get((cid, r))
                if b:
                    nxt = b[0] if b[0] != 'F' else ('F-other' if b[1] != gid else 'F-same')
                    break
            hit = len([r for r in hits[(cid, gid)] if a <= r <= z])
            i = max(0, z - 1)
            p = pos(c, i)
            nd = 99
            if p:
                for ec in enemies:
                    q = pos(ec, i)
                    if q: nd = min(nd, chebyshev(p, q))
            # distance walked to the group at start
            i0 = max(0, a - 2)
            p0 = pos(c, i0)
            dist0 = fields[gid][p0[0] * H + p0[1]] if p0 else None
            p1 = pos(c, i)
            dist1 = fields[gid][p1[0] * H + p1[1]] if p1 else None
            if own_cap: out = 'own_cap'
            elif en_cap: out = 'enemy_cap'
            else: out = 'none'
            eps.append({'team': role[t], 'type': name_of[cid], 'g': gid, 'side': rel(gid, t),
                        'cluster': all(x in CLUSTER for x in gmeta[gid]['types']),
                        'gtypes': ''.join(sorted(macro.ABBR[x] for x in gmeta[gid]['types'])), 'gems': gmeta[gid]['gems'],
                        'a': a, 'z': z, 'len': z - a + 1, 'cls': dict(cc), 'hit': hit, 'out': out, 'mine': mine,
                        'cap_total': sum(x[3] for x in own_cap), 'next': nxt, 'nd_end': nd, 'd0': dist0, 'd1': dist1,
                        'dmg_end': any(r in dmg[cid] for r in range(z - 2, z + 1))})
    return {'dir': d, 'w0': w0, 'w1': w1, 'eps': eps}


def main():
    rows = [json.loads(l) for l in open('/tmp/mxi-study/farmwin.jsonl')]
    with ProcessPoolExecutor(24) as ex, open('/tmp/mxi-study/episodes.jsonl', 'w') as out:
        for res in ex.map(work, rows, chunksize=2):
            out.write(json.dumps(res) + '\n')


if __name__ == '__main__':
    main()
