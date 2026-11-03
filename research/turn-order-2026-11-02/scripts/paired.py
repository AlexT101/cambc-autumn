"""Paired comparison of two A/B runs against the same REF on the same games (map and side): the difference in CAND
win rate with a 95% interval over the paired differences.

usage: python3 paired.py RUN_A RUN_B   (ab.py run names, e.g. pred-pwc-vs-adv2 pred-ref-vs-adv2)
"""
import glob
import json
import math
import os
import re
import sys


def wins(run):
    out = {}
    for d in glob.glob(f'replays/batch-*-ab-{run}-*'):
        # the suite follows the run name: run 'x' must not take run 'x-B's batches
        if not re.fullmatch(re.escape(run) + r'-(fresh-\d+|ladder|gen(-s\d+)?)', d.rsplit('-ab-', 1)[1]):
            continue
        try:
            res = json.load(open(f'{d}/results.json'))
        except (OSError, ValueError):
            continue
        for m in res['matches']:
            if m.get('winner') is None:
                continue
            key = (os.path.basename(m['map']), tuple(m['order']))
            out[key] = 1.0 if m['winner'] == 0 else 0.0  # bot 0 is CAND
    return out


def main():
    a, b = wins(sys.argv[1]), wins(sys.argv[2])
    keys = sorted(set(a) & set(b))
    n = len(keys)
    d = [a[k] - b[k] for k in keys]
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / (n - 1)
    se = math.sqrt(var / n)
    wa = sum(a[k] for k in keys) / n
    wb = sum(b[k] for k in keys) / n
    print(f'{n} paired games: {sys.argv[1]} {100 * wa:.2f}%, {sys.argv[2]} {100 * wb:.2f}%; '
          f'difference {100 * mean:+.2f} points, 95% CI {100 * (mean - 1.96 * se):+.2f}..{100 * (mean + 1.96 * se):+.2f}, '
          f'z {mean / se if se else 0:.2f}; {sum(x > 0 for x in d)} games went the first way, {sum(x < 0 for x in d)} the second')


if __name__ == '__main__':
    main()
