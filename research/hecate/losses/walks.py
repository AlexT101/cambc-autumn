"""Walking rounds split by bag (carrying gems or not) and by direction (towards an altar, own spawn, else).

py research/hecate/losses/walks.py [GAME_DIR ...]   (default: every loss)
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games, Game, US  # noqa


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def walks(g, team):
    moves = collections.defaultdict(int)
    for e in g.events:
        if e['k'] == 'move' and g.team_of.get(e['a']) == team:
            moves[(e['a'], e['r'])] += 1
    out = collections.Counter()
    sc = g.map.spawn_center(team)
    for cid in g.team_ids[team]:
        ch = g.ch(cid)
        for r in range(2, len(ch['x']) + 1):
            if not moves.get((cid, r)):
                continue
            i = r - 1
            p0, p1 = g.pos(cid, i - 1), g.pos(cid, i)
            if not p0 or not p1:
                continue
            bag = ch['gems'][i - 1] > 0
            if bag and g.map.altar_dist(p1) < g.map.altar_dist(p0):
                k = 'bag:to-altar'
            elif cheb(p1, sc) < cheb(p0, sc):
                k = ('bag' if bag else 'empty') + ':homeward'
            else:
                k = ('bag' if bag else 'empty') + ':out'
            out[k] += 1
            out['all'] += 1
    return out


def main():
    games = [Game(d) for d in sys.argv[1:]] if len(sys.argv) > 1 else [g for g in our_games() if g.winner != g.us]
    tot = {'us': collections.Counter(), 'them': collections.Counter()}
    rounds = 0
    for g in games:
        us = g.names.index(US)
        tot['us'].update(walks(g, us))
        tot['them'].update(walks(g, 1 - us))
        rounds += g.n_rounds
    for k, c in tot.items():
        print(k, f"walk rounds per 100 game rounds {100 * c['all'] / rounds:.0f}", {x: round(100 * v / rounds) for x, v in sorted(c.items()) if x != 'all'})


if __name__ == '__main__':
    main()
