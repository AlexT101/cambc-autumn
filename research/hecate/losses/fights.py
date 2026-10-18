"""Engagements behind our deaths: who struck first, numbers and health at the start, trades.

py research/hecate/losses/fights.py [--print]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games, strong  # noqa

R = 8  # radius counted as "in the fight"


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def engagements(g):
    """Cluster champion-vs-champion damage: events within 4 rounds and 10 tiles join a cluster."""
    hits = sorted(g.champ_damage, key=lambda x: x[0])
    clusters = []
    for s, r, a, v, amt, ap, vp in hits:
        vpos = g.pos(v, max(0, r - 2)) or ap
        apos = g.pos(a, max(0, r - 2)) or ap
        if vpos is None:
            continue
        for c in reversed(clusters):
            if r - c['last'] > 4:
                continue
            if any(cheb(vpos, p) <= 10 for p in c['where'][-6:]):
                c['hits'].append((s, r, a, v, amt))
                c['last'] = r
                c['where'].append(vpos)
                break
        else:
            clusters.append(dict(first=r, last=r, hits=[(s, r, a, v, amt)], where=[vpos], start_pos=vpos, start_att=a, apos=apos))
    return clusters


def summarise(g, c):
    us, them = g.us, g.them
    r0 = c['first']
    i0 = max(0, r0 - 2)
    centre = c['start_pos']
    side = {0: [], 1: []}
    for t in (0, 1):
        for cid in g.team_ids[t]:
            p = g.pos(cid, i0)
            if p and cheb(p, centre) <= R:
                ch = g.ch(cid)
                side[t].append((cid, ch['hp'][i0], ch['maxHp'][i0]))
    dead = {0: 0, 1: 0}
    bags = {0: 0, 1: 0}
    for d in g.deaths:
        if c['first'] <= d['r'] <= c['last'] + 1 and not d.get('linked'):
            p = tuple(d['at']) if d.get('at') else None
            if p and any(cheb(p, w) <= 10 for w in c['where']):
                if d.get('by') is not None:
                    dead[g.team_of[d['v']]] += 1
                    bags[g.team_of[d['v']]] += d.get('gems', 0)
    init = g.team_of[c['start_att']]
    dmg = {0: 0.0, 1: 0.0}
    for s, r, a, v, amt in c['hits']:
        dmg[g.team_of[a]] += amt
    return dict(game=g.dir, map=g.map_name, opp=g.opp, won=g.winner == us, r0=r0, r1=c['last'], init='us' if init == us else 'them',
                n_us=len(side[us]), n_them=len(side[them]), hp_us=sum(x[1] for x in side[us]), hp_them=sum(x[1] for x in side[them]),
                dead_us=dead[us], dead_them=dead[them], bag_us=bags[us], bag_them=bags[them], dmg_us=dmg[us], dmg_them=dmg[them],
                half=g.map.half(g.map.own(us, centre)), first_att=g.name_of[c['start_att']])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--print', action='store_true')
    ap.add_argument('--losses', action='store_true')
    a = ap.parse_args()
    rows = []
    for g in our_games():
        if a.losses and g.winner == g.us:
            continue
        for c in engagements(g):
            if len(c['hits']) < 2:
                continue
            rows.append(summarise(g, c))
    print(len(rows), 'engagements')
    tab = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for x in rows:
        if x['dead_us'] + x['dead_them'] == 0:
            continue
        nd = x['n_us'] - x['n_them']
        key = (x['init'], 'fewer' if nd < 0 else 'even' if nd == 0 else 'more')
        t = tab[key]
        t[0] += 1
        t[1] += x['dead_us']
        t[2] += x['dead_them']
        t[3] += x['bag_us']
        t[4] += x['bag_them']
    print('lethal engagements by (initiator, our numbers): count, our deaths, their deaths, our bags lost, their bags lost')
    for k in sorted(tab):
        print(' ', k, tab[k])
    # health share bins
    hb = collections.defaultdict(lambda: [0, 0, 0])
    for x in rows:
        if x['dead_us'] + x['dead_them'] == 0:
            continue
        share = x['hp_us'] / max(1, x['hp_us'] + x['hp_them'])
        b = round(share * 5) / 5
        hb[(x['init'], b)][0] += 1
        hb[(x['init'], b)][1] += x['dead_us']
        hb[(x['init'], b)][2] += x['dead_them']
    print('by (initiator, our health share): count, our deaths, their deaths')
    for k in sorted(hb):
        print(' ', k, hb[k])
    hh = collections.defaultdict(lambda: [0, 0, 0])
    for x in rows:
        if x['dead_us'] + x['dead_them'] == 0:
            continue
        hh[x['half']][0] += 1
        hh[x['half']][1] += x['dead_us']
        hh[x['half']][2] += x['dead_them']
    print('by half (0 ours): count, our deaths, their deaths', dict(hh))
    if a.print:
        for x in rows:
            if x['dead_us'] + x['dead_them']:
                print(x)


if __name__ == '__main__':
    main()
