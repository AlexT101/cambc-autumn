"""Per-game summary of nemesis-era games: kills, bags lost, gems collected, tribute gap timing.

py research/hecate/losses/games.py
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games, strong  # noqa


def collected(g, team):
    """Gems from captures and from kills, per team."""
    cap = kill = 0
    for e in g.events:
        if e['k'] == 'capture' and e['team'] == team:
            cap += sum(s[1] for s in e['shares'])
        if e['k'] == 'death' and e.get('by') is not None and g.team_of.get(e['by']) == team:
            kill += e.get('gemsTo', 0) or 0
    return cap, kill


def main():
    games = our_games()
    tot = collections.defaultdict(lambda: collections.Counter())
    print('game             map        opp                    res  gems      deaths(us/them) camp-d  bags lost us/them  cap us/them  kill-gems us/them  gap200 gap400')
    for g in games:
        us, them = g.us, g.them
        dus = [d for d in g.deaths if g.team_of[d['v']] == us and not d.get('linked')]
        dth = [d for d in g.deaths if g.team_of[d['v']] == them and not d.get('linked')]
        bag = lambda ds: sum(d.get('gems', 0) for d in ds)
        bus = sum(d.get('gems', 0) for d in g.deaths if g.team_of[d['v']] == us)
        bth = sum(d.get('gems', 0) for d in g.deaths if g.team_of[d['v']] == them)
        camp_us = sum(1 for d in dus if d.get('by') is None)
        cu, ku = collected(g, us)
        ct, kt = collected(g, them)
        gap = lambda r: g.gems_at(us, r) - g.gems_at(them, r)
        res = 'W' if g.winner == us else 'L'
        k = res
        t = tot[k]
        t['n'] += 1
        t['dus'] += len(dus)
        t['dth'] += len(dth)
        t['camp_us'] += camp_us
        t['camp_th'] += sum(1 for d in dth if d.get('by') is None)
        t['bus'] += bus
        t['bth'] += bth
        t['cu'] += cu
        t['ct'] += ct
        t['ku'] += ku
        t['kt'] += kt
        t['rounds'] += g.n_rounds
        if res == 'L':
            print(f"{g.dir} {g.map_name[:10]:10} {g.opp[:22]:22} {res} {g.final_gems[us]:4}-{g.final_gems[them]:4}  {len(dus):3}/{len(dth):3}      {camp_us:3}    {bus:5}/{bth:5}      {cu:5}/{ct:5}    {ku:5}/{kt:5}   {gap(200):5} {gap(400):5}")
    for k, t in tot.items():
        n = t['n']
        print(k, n, {x: round(v / n, 1) for x, v in t.items() if x != 'n'})


if __name__ == '__main__':
    main()
