"""Back-and-forth walking: a step that returns to the tile of two rounds before (A->B->A), per 100
game rounds and as a share of walks, us vs them, with the most common jitter spots of ours.

py research/hecate/losses/jitter.py [--examples N]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games  # noqa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--examples', type=int, default=0)
    a = ap.parse_args()
    agg = collections.defaultdict(collections.Counter)
    spots = collections.Counter()
    for g in our_games():
        res = 'W' if g.winner == g.us else 'L'
        agg[res]['rounds'] += g.n_rounds
        for team, side in ((g.us, 'us'), (g.them, 'them')):
            for cid in g.team_ids[team]:
                ch = g.ch(cid)
                for r in range(3, len(ch['x']) + 1):
                    i = r - 1
                    p0, p1, p2 = g.pos(cid, i - 2), g.pos(cid, i - 1), g.pos(cid, i)
                    if not (p0 and p1 and p2) or p1 == p2:
                        continue
                    agg[res][side + ' walks'] += 1
                    if p2 == p0 and p1 != p0:
                        agg[res][side + ' reversals'] += 1
                        if side == 'us':
                            seen = bool(ch['sees'][i])
                            agg[res]['us reversals with enemy in sight'] += seen
                            spots[(g.dir, g.map_name, g.name_of[cid], p0, p1, seen)] += 1
    for res, c in agg.items():
        R = c['rounds']
        print(res, {k: round(100 * v / R, 1) for k, v in c.items() if k != 'rounds'}, 'per 100 game rounds;',
              'reversal share us', round(c['us reversals'] / c['us walks'], 3), 'them', round(c['them reversals'] / c['them walks'], 3))
    for k, v in spots.most_common(a.examples):
        print(v, k)


if __name__ == '__main__':
    main()
