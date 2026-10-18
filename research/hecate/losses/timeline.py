"""Per-window timeline of a game from our side: tributed, carried, captured, deaths, captures by group.

py research/hecate/losses/timeline.py GAME_DIR [--step 25]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import Game, US  # noqa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('game')
    ap.add_argument('--step', type=int, default=25)
    a = ap.parse_args()
    g = Game(a.game)
    us = g.names.index(US)
    them = 1 - us
    lab = g.map.group_label
    print(g, 'us = team', us)
    win = collections.defaultdict(lambda: {'cap': [[], []], 'die': [[], []]})
    for e in g.events:
        w = (e['r'] - 1) // a.step
        if e['k'] == 'capture':
            t = 0 if e['team'] == us else 1
            win[w]['cap'][t].append(f"{lab(g.map.own_group(us, e['g']))}:{sum(s[1] for s in e['shares'])}")
        if e['k'] == 'death' and not e.get('linked'):
            t = 0 if g.team_of[e['v']] == us else 1
            win[w]['die'][t].append(f"{g.name_of[e['v']]}({e.get('gems', 0)})<{g.name_of.get(e.get('by'), 'camp')}")
    n = len(g.rounds['round'])
    for w in range(0, (n - 1) // a.step + 1):
        r = min(n, (w + 1) * a.step)
        carried = [sum(g.ch(c)['gems'][r - 1] for c in g.team_ids[t]) for t in (us, them)]
        earned = [sum(g.ch(c)['earned'][r - 1] for c in g.team_ids[t]) for t in (us, them)]
        x = win[w]
        print(f"r{r:4} trib {g.gems_at(us, r):4}-{g.gems_at(them, r):4} carry {carried[0]:3}-{carried[1]:3} gold {earned[0]:5.0f}-{earned[1]:5.0f} | "
              f"us cap {' '.join(x['cap'][0])} | them cap {' '.join(x['cap'][1])} | us die {' '.join(x['die'][0])} | them die {' '.join(x['die'][1])}")


if __name__ == '__main__':
    main()
