"""Lethal engagements the enemy starts: what our first victim was doing, whether it saw them coming.

py research/hecate/losses/jumped.py [--losses] [--examples N]
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
        cg = {c['id']: c['group'] for c in g.map.raw['camps']}
        acts = collections.defaultdict(set)
        for e in g.events:
            if e.get('a') in g.team_of and g.team_of[e['a']] == g.us:
                if e['k'] in ('attack', 'cast') and e.get('cdmg'):
                    acts[(e['a'], e['r'])].add('camp')
                if e['k'] == 'move':
                    acts[(e['a'], e['r'])].add('move')
        for c in engagements(g):
            if len(c['hits']) < 2 or g.team_of[c['start_att']] != g.them:
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
            if not dead[g.us]:
                continue
            s, r, att, vic, amt = c['hits'][0]
            vch = g.ch(vic)
            sees = vch['sees']
            first_seen = next((rr for rr in range(max(1, r0 - 20), r0 + 1) if att in (sees[rr - 1] or [])), None)
            ap_ = g.pos(att, max(0, (first_seen or r0) - 2))
            vp_ = g.pos(vic, max(0, (first_seen or r0) - 2))
            d_seen = cheb(ap_, vp_) if ap_ and vp_ else None
            doing = []
            for rr in range(r0 - 3, r0 + 1):
                doing += sorted(acts.get((vic, rr), ()))
            chan = vch['chan'][i0]
            state = 'tribute' if chan == 2 else 'recall' if chan == 1 and (vch['chanT'][i0] or 9) < 4 else ('camp' if 'camp' in doing else 'move' if 'move' in doing else 'still')
            bush = g.pos(att, i0) in g.map.bushes
            rows.append(dict(game=g.dir, map=g.map_name, r=r0, att=g.name_of[att], vic=g.name_of[vic], state=state, bag=vch['gems'][i0],
                             vic_frac=round((vch['hp'][i0] or 0) / (vch['maxHp'][i0] or 1), 2), lead=(r0 - first_seen) if first_seen else None, d_seen=d_seen,
                             bush=bush, n=(n[g.us], n[g.them]), hp=(round(hp[g.us]), round(hp[g.them])), dead=(dead[g.us], dead[g.them]),
                             half=g.map.half(g.map.own(g.us, g.pos(vic, i0))) if g.pos(vic, i0) else None))
    print(len(rows), 'enemy-started engagements with our deaths')
    tot_d = sum(x['dead'][0] for x in rows)
    print('our deaths', tot_d, 'theirs', sum(x['dead'][1] for x in rows))
    for key in ('state', 'half', 'att', 'vic'):
        c = collections.Counter(x[key] for x in rows)
        print(key, c.most_common())
    lead = collections.Counter('unseen' if x['lead'] is None else '0' if x['lead'] == 0 else '1-2' if x['lead'] <= 2 else '3-5' if x['lead'] <= 5 else '6+' for x in rows)
    print('rounds the victim saw the attacker before the first hit', lead)
    print('distance at first sight', collections.Counter(x['d_seen'] for x in rows if x['lead']).most_common())
    print('attacker in bush at first hit', sum(x['bush'] for x in rows))
    print('outnumbered at start', sum(x['n'][1] > x['n'][0] for x in rows), 'less hp', sum(x['hp'][0] < 0.8 * x['hp'][1] for x in rows))
    print('victim <50% hp', sum(x['vic_frac'] < 0.5 for x in rows), 'victim carrying', sum(x['bag'] > 0 for x in rows))
    for x in rows[:a.examples]:
        print(x)


if __name__ == '__main__':
    main()
