"""Lethal engagements: participants' strength (hp, earned gold, Focus, Strength) vs outcome, by initiator.

py research/hecate/losses/fights2.py
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games  # noqa
from fights import engagements, cheb, R  # noqa


def power(g, cid, i):
    c = g.ch(cid)
    return c['hp'][i] or 0, c['earned'][i] or 0, c['str'][i] or 0, c['foc'][i] or 0


def main():
    rows = []
    for g in our_games():
        for c in engagements(g):
            if len(c['hits']) < 2:
                continue
            r0 = c['first']
            i0 = max(0, r0 - 2)
            centre = c['start_pos']
            side = {0: [], 1: []}
            for t in (0, 1):
                for cid in g.team_ids[t]:
                    p = g.pos(cid, i0)
                    if p and cheb(p, centre) <= R:
                        side[t].append(power(g, cid, i0))
            dead = collections.Counter()
            for d in g.deaths:
                if c['first'] <= d['r'] <= c['last'] + 1 and not d.get('linked') and d.get('by') is not None:
                    p = tuple(d['at']) if d.get('at') else None
                    if p and any(cheb(p, w) <= 10 for w in c['where']):
                        dead[g.team_of[d['v']]] += 1
            if not dead:
                continue
            init = 'us' if g.team_of[c['start_att']] == g.us else 'them'
            S = lambda t, k: sum(x[k] for x in side[t])
            rows.append(dict(res='W' if g.winner == g.us else 'L', init=init, n=(len(side[g.us]), len(side[g.them])),
                             hp=(S(g.us, 0), S(g.them, 0)), gold=(S(g.us, 1), S(g.them, 1)),
                             dead=(dead[g.us], dead[g.them]), game=g.dir, r=r0))
    tab = collections.defaultdict(lambda: [0, 0, 0])
    for x in rows:
        gu, gt = x['gold']
        gb = 'gold<' if gu < 0.8 * gt else 'gold>' if gu > 1.25 * gt else 'gold='
        hu, ht = x['hp']
        hb = 'hp<' if hu < 0.8 * ht else 'hp>' if hu > 1.25 * ht else 'hp='
        k = (x['res'], x['init'], gb, hb)
        tab[k][0] += 1
        tab[k][1] += x['dead'][0]
        tab[k][2] += x['dead'][1]
    print('(result, initiator, our gold vs theirs, our hp vs theirs): engagements, our deaths, their deaths')
    for k in sorted(tab):
        print(' ', k, tab[k])


if __name__ == '__main__':
    main()
