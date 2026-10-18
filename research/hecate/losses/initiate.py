"""Lethal engagements we start while outmatched (less hp present): who starts them, how, and examples.

py research/hecate/losses/initiate.py [--examples N]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games  # noqa
from fights import engagements, cheb, R  # noqa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--examples', type=int, default=0)
    ap.add_argument('--losses', action='store_true')
    a = ap.parse_args()
    rows = []
    for g in our_games():
        if a.losses and g.winner == g.us:
            continue
        for c in engagements(g):
            if len(c['hits']) < 2 or g.team_of[c['start_att']] != g.us:
                continue
            r0 = c['first']
            i0 = max(0, r0 - 2)
            centre = c['start_pos']
            hp = {0: 0, 1: 0}
            n = {0: 0, 1: 0}
            for t in (0, 1):
                for cid in g.team_ids[t]:
                    p = g.pos(cid, i0)
                    if p and cheb(p, centre) <= R:
                        hp[t] += g.ch(cid)['hp'][i0] or 0
                        n[t] += 1
            dead = collections.Counter()
            for d in g.deaths:
                if c['first'] <= d['r'] <= c['last'] + 1 and not d.get('linked') and d.get('by') is not None:
                    p = tuple(d['at']) if d.get('at') else None
                    if p and any(cheb(p, w) <= 10 for w in c['where']):
                        dead[g.team_of[d['v']]] += 1
            if not dead:
                continue
            s, r, att, vic, amt = c['hits'][0]
            ev = next(e for e in g.events if e['s'] == s and e.get('a') == att)
            how = ev['k'] + (':' + ev.get('ab', '') if ev['k'] == 'cast' else '')
            ach = g.ch(att)
            vic_hp = g.ch(vic)['hp'][i0] or 0
            vic_frac = vic_hp / (g.ch(vic)['maxHp'][i0] or 1)
            # moved towards the victim in the 3 rounds before (chasing) or stood (poke)
            p_before = g.pos(att, max(0, r0 - 5))
            p_now = g.pos(att, i0)
            vp = g.pos(vic, i0)
            approach = (cheb(p_before, vp) - cheb(p_now, vp)) if p_before and p_now and vp else 0
            rows.append(dict(game=g.dir, map=g.map_name, res='W' if g.winner == g.us else 'L', r=r0, att=g.name_of[att], vic=g.name_of[vic],
                             how=how, bag=ach['gems'][i0], outhp=hp[g.us] < 0.8 * hp[g.them], n=(n[g.us], n[g.them]), hp=(round(hp[g.us]), round(hp[g.them])),
                             dead=(dead[g.us], dead[g.them]), vic_frac=round(vic_frac, 2), approach=approach,
                             half=g.map.half(g.map.own(g.us, p_now)) if p_now else None))
    out = [x for x in rows if x['outhp']]
    print(len(rows), 'lethal engagements we started;', len(out), 'with under 0.8x their hp present')
    for key in ('att', 'how', 'half', 'res'):
        c = collections.Counter(x[key] for x in out)
        d = collections.Counter()
        for x in out:
            d[(x[key], 0)] += x['dead'][0]
            d[(x[key], 1)] += x['dead'][1]
        print(key, [(k, v, d[(k, 0)], d[(k, 1)]) for k, v in c.most_common()])
    vb = collections.Counter('victim<50%' if x['vic_frac'] < 0.5 else 'victim>=50%' for x in out)
    print('victim health', vb, 'our deaths when victim>=50%', sum(x['dead'][0] for x in out if x['vic_frac'] >= 0.5), 'theirs', sum(x['dead'][1] for x in out if x['vic_frac'] >= 0.5))
    ap_ = collections.Counter('approached' if x['approach'] > 0 else 'held/retreated' for x in out)
    print('attacker movement 3 rounds before', ap_)
    print('numbers (us,them)', collections.Counter(x['n'] for x in out).most_common(12))
    for x in out[:a.examples]:
        print(x)


if __name__ == '__main__':
    main()
