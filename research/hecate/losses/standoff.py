"""Standoffs: a champion alternating between the same two tiles for 10+ rounds in a row (A,B,A,B...).

py research/hecate/losses/standoff.py [--examples N]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games  # noqa


def runs(g, cid, min_len=10):
    ch = g.ch(cid)
    out = []
    start = None
    n = len(ch['x'])
    for r in range(3, n + 1):
        i = r - 1
        p0, p1, p2 = g.pos(cid, i - 2), g.pos(cid, i - 1), g.pos(cid, i)
        ok = p0 and p1 and p2 and p2 == p0 and p1 != p0
        if ok:
            if start is None:
                start = r - 2
        else:
            if start is not None and r - 1 - start + 1 >= min_len:
                out.append((start, r - 1))
            start = None
    if start is not None and n - start + 1 >= min_len:
        out.append((start, n))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--examples', type=int, default=0)
    a = ap.parse_args()
    agg = collections.defaultdict(collections.Counter)
    ex = []
    for g in our_games():
        res = 'W' if g.winner == g.us else 'L'
        agg[res]['games'] += 1
        for team, side in ((g.us, 'us'), (g.them, 'them')):
            for cid in g.team_ids[team]:
                for s, e in runs(g, cid):
                    agg[res][side + ' standoffs'] += 1
                    agg[res][side + ' rounds'] += e - s + 1
                    if side == 'us':
                        ch = g.ch(cid)
                        seen = sum(1 for r in range(s, e + 1) if ch['sees'][r - 1])
                        bag = ch['gems'][s - 1]
                        agg[res]['us rounds with enemy in sight'] += seen
                        ex.append((e - s + 1, g.dir, g.map_name, res, g.name_of[cid], s, e, 'bag', bag, 'enemy seen', seen, g.pos(cid, s - 1), g.pos(cid, s)))
    for res, c in agg.items():
        n = c['games']
        print(res, n, 'games', {k: round(v / n, 1) for k, v in c.items() if k != 'games'}, '(per game)')
    for x in sorted(ex, reverse=True)[:a.examples]:
        print(x)


if __name__ == '__main__':
    main()
