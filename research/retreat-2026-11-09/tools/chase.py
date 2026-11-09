"""Do the planner's pursuers chase? For each plan (ESE lines), each visible pursuer's distance to us at the plan and 1 and 3 rounds later: the share closer and farther.
usage: chase.py EXTRACT_DIR BOT"""
import sys, json, gzip, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, __import__('os').path.dirname(__file__))
from esc_diag import parse_stdout


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(args):
    ex, g, bot = args
    R = json.load(gzip.open(f"{ex}/{g['dir']}/rounds.json.gz"))
    ridx = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    out = Counter()
    for t in (0, 1):
        if g['teams'][t] != bot: continue
        try:
            esh, esk, ese, esr, esd = parse_stdout(g['source'], 'ab'[t])
        except KeyError:
            continue
        for (r, h), info in ese.items():
            i0 = ridx.get(r - 1)
            if i0 is None: continue
            A = ch[h]
            if A['x'][i0] is None or A['x'][i0] < 0: continue
            me0 = (A['x'][i0], A['y'][i0])
            for x in info:
                if x[1] != 1: continue
                B = ch.get(x[0])
                if B is None: continue
                p0 = (x[6], x[7])
                d0 = cheb(me0, p0)
                b = min(d0, 9)
                out[('n', b)] += 1
                for dk in (1, 3):
                    i = ridx.get(r - 1 + dk)
                    if i is None or not A['alive'][i] or not B['alive'][i] or A['x'][i] is None or B['x'][i] is None: break
                    d = cheb((A['x'][i], A['y'][i]), (B['x'][i], B['y'][i]))
                    out[('closer', dk, b)] += d < d0
                    out[('farther', dk, b)] += d > d0
                    out[('seen', dk, b)] += 1
    return out


def main():
    ex, bot = sys.argv[1], sys.argv[2]
    idx = json.load(open(f'{ex}/index.json'))
    games = [g for g in idx['games'] if bot in g['teams']]
    tot = Counter()
    with ProcessPoolExecutor(16) as pool:
        for o in pool.map(one, [(ex, g, bot) for g in games]): tot.update(o)
    print('d0  n  | +1: closer farther | +3: closer farther')
    for b in range(0, 10):
        n = tot[('n', b)]
        if not n: continue
        row = [f'{b:2d} {n:6d}']
        for dk in (1, 3):
            s = tot[('seen', dk, b)] or 1
            row.append(f"{tot[('closer', dk, b)] / s:.2f} {tot[('farther', dk, b)] / s:.2f}")
        print(' | '.join(row))


if __name__ == '__main__':
    main()
