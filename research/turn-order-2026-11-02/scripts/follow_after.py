"""What became of a kill-bid target we did not hit at the bound turn: died within 3 rounds (by us, by an ally),
escaped. Base and fix on the same games (follow-through.md).

usage: python3 follow_after.py EXTRACT_DIR RUN [RUN ...]
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from follow_trace import key, lines, parse_ft, replays  # noqa: E402
from tolib import G, index  # noqa: E402


def main():
    ex, runs = sys.argv[1], sys.argv[2:]
    by_source = {key(r['source']): r['dir'] for r in index(ex) if r['ok']}
    for run in runs:
        c = Counter()
        for path in replays(run):
            recs = []
            for l in lines(path):
                if not l.startswith('FT '):
                    continue
                try:
                    x = parse_ft(l)
                except (ValueError, IndexError):
                    continue
                if x['need'] < x['hpbid'] or x['hp0'] <= 0 or x['acted'] or x['stun']:
                    continue
                killed = not x['alive'] or x['hp1'] == 0
                if killed or (x['vis'] and x['hp1'] < x['hp0']):
                    continue
                recs.append(x)
            d = by_source.get(key(path)) if recs else None
            if d is None:
                continue
            g = G(ex, d)
            us = g.team[recs[0]['me']]
            enemies = [c_ for c_ in g.ids if g.team[c_] != us]
            for x in recs:
                t = enemies[x['t']] if x['t'] < len(enemies) else None
                if t is None:
                    continue
                c['n'] += 1
                fate = 'alive after 3 rounds'
                for rr in range(x['r'], min(g.N, x['r'] + 3) + 1):
                    de = g.death(t, rr)
                    if de is not None:
                        by = de.get('by')
                        fate = ('by this champion' if by == x['me'] else 'by an ally' if by in g.members[us] else 'other') + (
                            ', same round' if rr == x['r'] else f', +{rr - x["r"]} round')
                        break
                c[fate] += 1
        n = c.pop('n')
        print(f'{run}: {n} bound turns not hitting a live target')
        for k, v in c.most_common():
            print(f'  {k}: {v} ({100 * v / n:.1f}%)')


if __name__ == '__main__':
    main()
