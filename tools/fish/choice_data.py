"""Attach the actor's visible allies at each route-episode start to routes-v3 rows.

Only the actor's own turn-start perspective is read; labels stay in `y`.
"""
import argparse
import gzip
import json
from pathlib import Path

from breadth import spawn, xy


def main(cache, routes, out):
    rows = {}
    with gzip.open(routes, 'rt') as f:
        for line in f:
            r = json.loads(line)
            if r['kind'] == 'route':
                rows.setdefault(r['game'], {})[r['step']] = r
    n = 0
    with gzip.open(out, 'xt') as output:
        for key, steps in rows.items():
            with gzip.open(Path(cache) / f'{key}.json.gz') as f:
                g = json.load(f)
            home = spawn(g['map'], g['side'])
            for t in g['turns']:
                r = steps.get(t['step'])
                if r is None:
                    continue
                s = t['start']
                r['x']['me_xy'] = xy(s['me'])
                r['x']['visible_allies'] = [dict(x=c['x'], y=c['y'], type=c['type'], home=xy(c) in home) for c in s['allies']]
                output.write(json.dumps(dict(kind='choice', **{k: r[k] for k in ('game', 'round', 'actor', 'step', 'x', 'y')}),
                                        separators=(',', ':')) + '\n')
                n += 1
    print(n, 'rows')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for a in ('cache', 'routes', 'out'):
        p.add_argument(a)
    a = p.parse_args()
    main(a.cache, a.routes, a.out)
