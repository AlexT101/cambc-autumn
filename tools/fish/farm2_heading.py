"""Heading labels for choice-v1 episodes: which groups the actor's next k moves stay on a shortest path to.

Over the turn starts after the decision (up to 40 rounds, stopping at the labelled hit, death or
a missing round), the positions that differ from the previous one are the actor's moves. After the
k-th move (k = 1..12), with s the Chebyshev length travelled so far (a dash counts 2),
`heading[k]` lists the groups g with walk_g(position) = walk_g(start) - s, walks by
8-neighbour BFS onto a tile adjacent to g with terrain, the enemy spawn and every camp tile blocked
(no dashes). Future positions only label; nothing here is a model input.

usage: farm2_heading.py CHOICE_V1 CACHE_DIR OUT
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

from breadth import spawn, static_groups, xy
from farm2_data import approach, multi_field

K = 12


def main(choice, cache, out):
    wanted = collections.defaultdict(dict)
    with gzip.open(choice, 'rt') as f:
        for line in f:
            r = json.loads(line)
            if r['x']['reason'] != 'opening' and r['y']['status'] == 'hit':
                wanted[r['game']][r['step']] = r['y']['round']
    n = 0
    with gzip.open(out, 'xt') as output:
        for gi, (key, steps) in enumerate(sorted(wanted.items())):
            with gzip.open(Path(cache) / f'{key}.json.gz') as f:
                g = json.load(f)
            m = g['map']
            groups, at = static_groups(m)
            blocked = set(map(tuple, m['walls'] + m['holes'] + m['altars'])) | spawn(m, 1 - g['side']) | set(at)
            fields = {}
            for q in groups:
                src = [p for p in approach(q['tiles']) if p not in blocked and 0 <= p[0] < m['width'] and 0 <= p[1] < m['height']]
                fields[q['id']] = multi_field(m, src, blocked)
            actors = collections.defaultdict(list)
            for t in g['turns']:
                actors[t['id']].append(t)
            for actor, turns in actors.items():
                for i, t in enumerate(turns):
                    if t['step'] not in steps:
                        continue
                    hit_round = steps[t['step']]
                    p0 = xy(t['start']['me'])
                    d0 = {k: f.get(p0) for k, f in fields.items()}
                    heading = {}; prev = p0; travelled = 0; k = 0
                    for u in turns[i + 1:]:
                        if u['round'] > hit_round or not u['start']['me']['alive'] or k >= K:
                            break
                        p = xy(u['start']['me'])
                        if p == prev:
                            continue
                        travelled += max(abs(p[0] - prev[0]), abs(p[1] - prev[1])); prev = p; k += 1
                        heading[k] = sorted(q for q, f in fields.items()
                                            if d0[q] is not None and f.get(p) is not None and f[p] == d0[q] - travelled)
                    output.write(json.dumps(dict(game=key, step=t['step'], actor=actor, heading=heading),
                                            separators=(',', ':')) + '\n')
                    n += 1
            if (gi + 1) % 20 == 0:
                print(gi + 1, n, flush=True)
    print(n, 'rows', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for a in ('choice', 'cache', 'out'):
        p.add_argument(a)
    a = p.parse_args()
    main(a.choice, a.cache, a.out)
