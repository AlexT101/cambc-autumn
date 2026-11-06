"""Shared loading, splits and scoring for the micro_* studies (MICRO.md).

Fit: model, confirm, third, fourth. Held out: fifth, sixth. Final test: seventh (scored once,
after micro-seventh-freeze.json). Rows: replays/fish-micro/<cohort>-micro-v1.jsonl.gz.
"""
import collections
import gzip
import json
from pathlib import Path

FIT = ['model', 'confirm', 'third', 'fourth']
HELD = ['fifth', 'sixth']
SEVENTH = ['seventh']
SPLITS = dict(fit=FIT, held=HELD, seventh=SEVENTH)
ROWS = Path('replays/fish-micro')
NAMES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren',
         'Varg', 'Tavi', 'HoR']
RANGED = {1, 3, 5, 6, 8, 11}
MELEE_T = {0, 2, 4, 7, 9, 10, 12}


def cohorts(split_names):
    out = []
    for s in split_names:
        out += SPLITS[s]
    return [c for c in out if (ROWS / f'{c}-micro-v1.jsonl.gz').exists()]


def rows(cs):
    for c in cs:
        with gzip.open(ROWS / f'{c}-micro-v1.jsonl.gz', 'rt') as f:
            for line in f:
                yield json.loads(line)


def by_round(cs):
    """Rows grouped per (game, round), in turn order."""
    cur, buf = None, []
    for r in rows(cs):
        key = (r['game'], r['round'])
        if key != cur:
            if buf:
                yield sorted(buf, key=lambda x: x['k'])
            cur, buf = key, []
        buf.append(r)
    if buf:
        yield sorted(buf, key=lambda x: x['k'])


def ehp(c):
    return c['hp'] + c['sh']


def dist(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def split_of(cohort):
    return next(s for s, cs in SPLITS.items() if cohort in cs)


class Score:
    """Agreement per split with an optional baseline; per-game coverage; keeps counterexamples."""

    def __init__(self, name, keep=12):
        self.name, self.keep = name, keep
        self.n = collections.Counter(); self.ok = collections.Counter(); self.base = collections.Counter()
        self.games = collections.defaultdict(set); self.groups = collections.defaultdict(set)
        self.errors = collections.defaultdict(list)

    def add(self, r, pred, actual, base=None, extra=None):
        s = split_of(r['cohort'])
        self.n[s] += 1; self.ok[s] += pred == actual
        if base is not None:
            self.base[s] += base == actual
        self.games[s].add(r['game']); self.groups[s].add(r.get('group'))
        if pred != actual and len(self.errors[s]) < self.keep:
            e = dict(game=r['game'], round=r['round'], actor=r['actor'], type=NAMES[r['type']], predicted=pred, actual=actual)
            if extra:
                e.update(extra)
            self.errors[s].append(e)

    def split(self, s):
        n, ok, b = self.n[s], self.ok[s], self.base[s]
        return dict(n=n, ok=ok, acc=round(ok / n, 4) if n else None, base=b, base_acc=round(b / n, 4) if n else None,
                    games=len(self.games[s]), groups=len(self.groups[s]))

    def report(self):
        return dict({s: self.split(s) for s in SPLITS if self.n[s]}, errors=dict(self.errors))

    def line(self):
        def fmt(s):
            d = self.split(s)
            return f"{d['ok']}/{d['n']} ({100 * (d['acc'] or 0):.1f}%, base {100 * (d['base_acc'] or 0):.1f}%)"
        return f'{self.name}: ' + '  '.join(f'{s} {fmt(s)}' for s in SPLITS if self.n[s])


class Tally:
    """Plain counts per split (descriptive tables)."""

    def __init__(self):
        self.c = collections.defaultdict(collections.Counter)

    def add(self, r, key, v=1):
        self.c[split_of(r['cohort'])][key] += v

    def report(self):
        return {s: {str(k): v for k, v in sorted(c.items(), key=str)} for s, c in self.c.items()}


def write(path, obj):
    if Path(path).exists():
        raise SystemExit(f'refusing to overwrite {path}')
    Path(path).write_text(json.dumps(obj, indent=1))
