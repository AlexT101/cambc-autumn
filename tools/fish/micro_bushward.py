"""Bushes and wards around fights (MICRO.md section 4), from the actor caches (all turns).

    python3 tools/fish/micro_bushward.py OUT.json [--splits fit held seventh] [--jobs N]

- Bush pathing: on walking turns (no dash), among the candidate tiles that make the same progress
  towards where the actor stands three turns later (an outcome proxy for its destination), the
  share ending on a bush against the bush share of those tiles; by context (enemy within 5,
  enemy visible farther, none).
- Hits from bushes: with a visible enemy within basic range at turn start (melee 1, ranged 3),
  off spawn, the share of turns hitting an enemy champion, on a bush or not; and whether that
  enemy could see the actor (same edge-connected bush cluster, or the actor off bushes).
- Wards: turns with a 'Place ward' input by context, with the ward approximately ready (10+
  rounds since the actor's previous placement input); the ward tile's distance to the nearest
  visible enemy against the actor's own, and whether it is a bush.
"""
import argparse
import collections
import json
import multiprocessing as mp
from pathlib import Path

from breadth import RANGED, dist, xy
from combat_common import COHORTS, load
from micro_common import SPLITS, write
from misc_rows import spawn_tiles

NB = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def clusters(bush):
    lab, k = {}, 0
    for p in sorted(bush):
        if p in lab:
            continue
        stack = [p]; lab[p] = k
        while stack:
            q = stack.pop()
            for n in ((q[0] + 1, q[1]), (q[0] - 1, q[1]), (q[0], q[1] + 1), (q[0], q[1] - 1)):
                if n in bush and n not in lab:
                    lab[n] = k; stack.append(n)
        k += 1
    return lab


def game(args):
    name, cache, entry = args
    g = load(cache, entry)
    m = g['map']
    bush = set(map(tuple, m['bushes']))
    lab = clusters(bush)
    home = spawn_tiles(m, g['side'])
    static = set(map(tuple, m['walls'] + m['holes'] + m['altars'])) | spawn_tiles(m, 1 - g['side'])
    C = collections.Counter()
    by = collections.defaultdict(list)
    for t in g['turns']:
        by[t['id']].append(t)
    for aid, ts in by.items():
        last_ward = -99
        for i, t in enumerate(ts):
            s = t['start']; me = s['me']
            if not me['alive'] or 'x' not in me:
                continue
            pos = xy(me)
            en = [e for e in s['enemies'] if 'x' in e and e.get('alive', True)]
            dmin = min((dist(pos, xy(e)) for e in en), default=99)
            ctx = 'contact' if dmin <= 5 else ('visible' if en else 'none')
            done = t.get('finish') == 'End turn' and 'x' in t.get('end', {}).get('me', {})
            stunned = any(b['type'] == 1 for b in me['buffs'])
            wards = [a for a in t['actions'] if a['kind'] == 'Place ward']
            ready = t['round'] - last_ward >= 10
            if done and not stunned and pos not in home:
                C[('ward', ctx, 'ready' if ready else 'not ready', 'turns')] += 1
                C[('ward', ctx, 'ready' if ready else 'not ready', 'placed')] += bool(wards)
                if wards and en:
                    w = tuple(wards[0]['to'])
                    dw = min(dist(w, xy(e)) for e in en)
                    C[('ward', ctx, 'tile vs self, nearer the nearest enemy')] += dw < dmin
                    C[('ward', ctx, 'tile vs self, same distance')] += dw == dmin
                    C[('ward', ctx, 'tile vs self, farther')] += dw > dmin
                    C[('ward', ctx, 'tile on bush')] += w in bush
                    C[('ward', ctx, 'placed with enemy')] += 1
                    C[('ward', ctx, 'enemy on a bush within 8')] += any(xy(e) in bush for e in en)
            if wards:
                last_ward = t['round']
            if not done or stunned:
                continue
            end = xy(t['end']['me'])
            hit = any(a['kind'] in ('Attack', 'Cast ability') and 'before' in a and
                      any([e['x'], e['y']] == a['to'] for e in a['before']['enemies'] if 'x' in e) for a in t['actions']
                      if a.get('ability') not in (6, 7, 5, 1))
            rng = 3 if me['type'] in RANGED else 1
            if pos not in home and any(dist(pos, xy(e)) <= rng for e in en):
                onb = pos in bush
                seen = [e for e in en if dist(pos, xy(e)) <= rng and (not onb or lab.get(xy(e)) == lab.get(pos))]
                key = ('hit from', 'bush' if onb else 'open', 'some in-range enemy can see me' if seen else 'unseen by in-range enemies')
                C[key + ('turns',)] += 1
                C[key + ('hit',)] += hit
            # Bush pathing (walking, no dash).
            if end == pos or i + 3 >= len(ts) or any(a['kind'] == 'Cast ability' and a.get('ability') == 6 for a in t['actions']):
                continue
            later = ts[i + 3]['start']['me']
            if not later.get('alive') or 'x' not in later:
                continue
            goal = xy(later)
            blocked = static | {xy(c) for c in s['allies'] + en if 'x' in c} | {xy(c) for c in s['camps'] if c['hp'] > 0}
            cand = [(pos[0] + dx, pos[1] + dy) for dx, dy in NB if 0 <= pos[0] + dx < m['width'] and 0 <= pos[1] + dy < m['height']
                    and (pos[0] + dx, pos[1] + dy) not in blocked]
            if end not in cand:
                continue
            same = [q for q in cand if dist(q, goal) == dist(end, goal)]
            nb = sum(q in bush for q in same)
            if 0 < nb < len(same):
                C[('bush path', ctx, 'n')] += 1
                C[('bush path', ctx, 'ends on bush')] += end in bush
                C[('bush path', ctx, 'expected x1000')] += round(1000 * nb / len(same))
    return name, C


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--splits', nargs='+', default=['fit', 'held'])
    p.add_argument('--jobs', type=int, default=6)
    a = p.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f'refusing to overwrite {a.out}')
    want = [c for s in a.splits for c in SPLITS[s]]
    jobs = []
    for name, manifest, cache in COHORTS:
        if name in want:
            jobs += [(name, cache, e) for e in json.loads(Path(manifest).read_text())]
    tot = collections.defaultdict(collections.Counter)
    with mp.Pool(min(a.jobs, 6)) as pool:
        for name, C in pool.imap_unordered(game, jobs):
            s = next(k for k, v in SPLITS.items() if name in v)
            tot[s].update(C)
    out = {s: {' | '.join(map(str, k)): v for k, v in sorted(c.items(), key=str)} for s, c in tot.items()}
    for s, c in out.items():
        print(s)
        for k, v in c.items():
            print('  ', k, v)
    write(a.out, dict(tallies=out, cohorts=want))


if __name__ == '__main__':
    main()
