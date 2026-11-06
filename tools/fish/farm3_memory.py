"""Team-union camp memory for farm2 destination episodes (FARM3.md section 3).

For each clean episode (non-opening, label `hit`) of a cohort, finds per candidate group the latest
group-state sighting (live id, state, capture team, capture timer, respawn countdown) recorded in
any *other* Fish champion's perspective (turn start, before-action and turn-end contexts) whose turn
precedes the decision turn (smaller engine step). Where that sighting is newer (a later round) than
the actor's own memory of the group, it replaces state, age and remaining respawn. Labels and later
frames are never read: inputs are allies' views up to the decision, which Fish could share through
its 8 bytes of team memory (not recorded in replays).

Writes replays/fish-farm3/<COHORT>/team-v1.jsonl.gz: per (game, step) {group: [state, age,
respawn, respawn_raw]}; refuses to overwrite.
  python3 tools/fish/farm3_memory.py COHORT
"""
import argparse
import bisect
import collections
import gzip
import json
from pathlib import Path

from breadth import static_groups, xy
from decision_data import contexts
from farm3_lib import cohort_paths, load_rows


def sightings(raw):
    g = json.loads(gzip.open(raw).read())
    groups, at = static_groups(g['map'])
    live = {}
    for t in g['turns']:
        for s in contexts(t):
            for c in s['camps']:
                live[c['group']] = at[xy(c)]
    seen = collections.defaultdict(list)  # static group -> [(step, round, actor, q)]
    for t in g['turns']:
        for s in contexts(t):
            for q in s['groups']:
                if q[0] in live:
                    seen[live[q[0]]].append((t['step'], t['round'], t['id'], q))
    for v in seen.values():
        v.sort(key=lambda z: (z[0], z[1]))
    return seen


def overrides(r, seen):
    t = r['round']; out = {}
    for c in r['x']['candidates']:
        v = seen.get(c['id'], [])
        k = bisect.bisect_left(v, (r['step'],)) - 1
        while k >= 0 and v[k][2] == r['actor']:
            k -= 1
        if k < 0:
            continue
        _, rd, _, q = v[k]
        own = t - c['age'] if c['age'] is not None else -1
        if rd <= own:
            continue
        out[str(c['id'])] = [q[1], t - rd, max(0, q[4] - (t - rd)) if q[1] == 3 else 0, q[4] if q[1] == 3 else None]
    return out


def main(cohort):
    p = cohort_paths(cohort)
    out = Path('replays/fish-farm3') / cohort / 'team-v1.jsonl.gz'
    if out.exists():
        raise SystemExit(f'refusing to overwrite {out}')
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = load_rows(cohort, team=False)
    by = collections.defaultdict(list)
    for r in rows:
        by[r['game']].append(r)
    n = changed = 0
    with gzip.open(out, 'xt') as f:
        for game, rs in sorted(by.items()):
            seen = sightings(Path(p['raw']) / f'{game}.json.gz')
            for r in rs:
                o = overrides(r, seen)
                n += 1; changed += bool(o)
                f.write(json.dumps(dict(game=game, step=r['step'], o=o), separators=(',', ':')) + '\n')
    print(cohort, n, 'episodes,', changed, 'with a newer ally sighting')


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('cohort')
    main(a.parse_args().cohort)
