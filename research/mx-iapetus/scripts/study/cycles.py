"""Group cycles (respawn -> capture) overlapping each farm-break window: per team, D-line targeting (F branch with
farm_group = g) champion-rounds, first target/hit round, damage, holds; captor; how the loser's targeters stopped.
Also both Prisms' bags at the window start. Writes /tmp/mxi-study/cycles.jsonl."""
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
    Lt = 1 - Wt

    def rel(gid, t):
        a, b = gd[gid][t], gd[gid][1 - t]
        if abs(a - b) <= max(2, 0.1 * (a + b)):
            return 'mid'
        return 'own' if a < b else 'enemy'
    # target rounds per (team, gid): list of (r, cid)
    tgt = defaultdict(list)
    for (cid, r), b in tr.items():
        if b[0] == 'F' and b[1] >= 0 and cid in team_of and cls[cid][r] != 'dead':
            tgt[(team_of[cid], b[1])].append((r, cid))
    for k in tgt: tgt[k].sort()
    cycles = []
    start = defaultdict(lambda: 1)
    info = defaultdict(lambda: {'hit': [defaultdict(float), defaultdict(float)], 'firsthit': [None, None],
                                'hold': [0, 0], 'firsthold': [None, None], 'clear': None, 'cleared_at': None})
    pos = lambda c, i: (c['x'][i], c['y'][i]) if c['alive'][i] and c['x'][i] is not None else None
    cidx = {c['id']: c for c in champs}

    def close(gid, r_end, cap_team, gems):
        a = start[gid]
        if r_end < w0 or a > w1:
            return
        I = info[gid]
        rec = {'g': gid, 'a': a, 'z': r_end, 'cap': role.get(cap_team, 'N'), 'gems': gems,
               'side_L': rel(gid, Lt), 'cluster': all(x in CLUSTER for x in gmeta[gid]['types']),
               'types': ''.join(sorted(macro.ABBR[x] for x in gmeta[gid]['types'])), 'ggems': gmeta[gid]['gems'],
               'clear': role.get(I['clear'], 'N'), 'cleared_at': I['cleared_at']}
        for t in (0, 1):
            ro = role[t]
            rs = [(r, c) for r, c in tgt[(t, gid)] if a <= r <= r_end and w0 - 30 <= r <= w1]
            rec[ro + '_tgt'] = len(rs)
            rec[ro + '_tgt_first'] = rs[0][0] if rs else None
            rec[ro + '_tgt_champs'] = len({c for _, c in rs})
            rec[ro + '_hitdmg'] = sum(I['hit'][t].values())
            rec[ro + '_firsthit'] = I['firsthit'][t]
            rec[ro + '_hold'] = I['hold'][t]
            rec[ro + '_firsthold'] = I['firsthold'][t]
            # how each targeting champion's last target turn ended
            ends = []
            last = {}
            for r, c in rs: last[c] = r
            for c, r in last.items():
                nxt = None
                for rr in range(r + 1, min(n, r + 4) + 1):
                    if cls[c][rr] == 'dead':
                        nxt = 'dead'; break
                    b = tr.get((c, rr))
                    if b:
                        nxt = b[0] if b[0] != 'F' else ('F-other' if b[1] != gid else 'F-same')
                        break
                # nearest enemy at last target turn
                i = max(0, r - 1)
                p = pos(cidx[c], i)
                nd = 99
                if p:
                    for ec in champs:
                        if ec['team'] != t:
                            q = pos(ec, i)
                            if q: nd = min(nd, chebyshev(p, q))
                dgrp = fields[gid][p[0] * H + p[1]] if p else None
                ends.append([name_of[c], r, nxt, nd, dgrp, len([1 for rr, cc in rs if cc == c])])
            rec[ro + '_ends'] = ends
        cycles.append(rec)

    for e in g.events:
        k, r = e['k'], e['r']
        if k == 'group_respawn':
            gid = e['g']
            # a cycle that never captured
            if gid in info and start[gid] <= w1:
                close(gid, r - 1, None, 0)
            start[gid] = r
            info.pop(gid, None)
        elif k in ('attack', 'cast') and e.get('cdmg') and e.get('camp') is not None:
            gid = camp_group.get(e['camp'])
            if gid is None: continue
            t = team_of[e['a']]
            I = info[gid]
            I['hit'][t][e['a']] += e['cdmg'] if isinstance(e['cdmg'], (int, float)) else sum(x[1] for x in e['cdmg'])
            if I['firsthit'][t] is None: I['firsthit'][t] = r
        elif k == 'capture_hold':
            I = info[e['g']]
            I['hold'][e['team']] += 1
            if I['firsthold'][e['team']] is None: I['firsthold'][e['team']] = r
        elif k == 'group_clear':
            I = info[e['g']]
            I['clear'] = team_of.get(e.get('by'), 2)
            I['cleared_at'] = r
        elif k == 'capture':
            gid = e['g']
            info[gid]  # ensure
            close(gid, r, e['team'], sum(s[1] for s in e['shares']))
            info.pop(gid, None)
            start[gid] = 10 ** 9  # respawning until group_respawn
    for gid in list(info):
        if start[gid] <= w1:
            close(gid, w1, None, 0)
    # Prism bags at window start
    pb = {}
    i = max(0, w0 - 2)
    for c in champs:
        if name_of[c['id']] == 'Prism':
            pb[role[c['team']]] = [c['gems'][i] or 0, c['foc'][i], c['alive'][i]]
    return {'dir': d, 'w0': w0, 'w1': w1, 'cycles': cycles, 'prism': pb}


def main():
    rows = [json.loads(l) for l in open('/tmp/mxi-study/farmwin.jsonl')]
    with ProcessPoolExecutor(24) as ex, open('/tmp/mxi-study/cycles.jsonl', 'w') as out:
        for res in ex.map(work, rows, chunksize=2):
            out.write(json.dumps(res) + '\n')


if __name__ == '__main__':
    main()
