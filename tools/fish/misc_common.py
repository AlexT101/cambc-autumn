"""Shared helpers for the misc_* analyses: load misc_rows output, item logs, safe result writing."""
import gzip, json, os, sys
from collections import defaultdict

ROWS = 'replays/fish-misc/rows-v1.jsonl.gz'
ITEMS = 'research/fish-2026-11-05/drafts-emblems-games.json.gz'
# Cohort roles: fit on the two oldest, hold out the three later ones (each a separate check).
FIT = ('model', 'confirm')
HELD = ('third', 'fourth', 'fifth')


def games(path=ROWS):
    with gzip.open(path, 'rt') as f:
        for line in f:
            yield json.loads(line)


def item_logs(path=ITEMS):
    """{(game16, champion id): [log entries]} from drafts_emblems.mjs (four oldest cohorts only)."""
    with gzip.open(path) as f: d = json.load(f)
    out = {}
    for g in d['games']:
        for c in g['champions']: out[(g['sha256'][:16], c['id'])] = c['log']
    return out


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def by_actor(rows):
    d = defaultdict(list)
    for r in rows: d[r['id']].append(r)
    for v in d.values(): v.sort(key=lambda r: r['r'])
    return d


def pct(k, n): return f'{k}/{n} ({100 * k / n:.2f}%)' if n else f'{k}/0'


def write_result(path, obj):
    if os.path.exists(path): sys.exit(f'refusing to overwrite {path}')
    with open(path, 'w') as f: json.dump(obj, f, indent=1, sort_keys=True)
    print(f'wrote {path}', file=sys.stderr)
