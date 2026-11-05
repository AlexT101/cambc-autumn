"""Shared loading, split and scoring helpers for the tactic_* studies.

Fit cohorts: model, confirm, third, fourth. Held out: fifth, sixth (later games, disjoint match groups).
"""
import collections
import gzip
import json
from pathlib import Path

FIT = ['model', 'confirm', 'third', 'fourth']
HELD = ['fifth', 'sixth']
ROWS = 'replays/fish-tactics'
NAMES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren',
         'Varg', 'Tavi', 'HoR']


def rows(kinds, cohorts=FIT + HELD, path=ROWS):
    kinds = set(kinds)
    for c in cohorts:
        with gzip.open(Path(path) / f'{c}-tactic-v3.jsonl.gz', 'rt') as f:
            for line in f:
                # Cheap prefilter on the kind field before parsing.
                k = line[line.index('"kind":"') + 8:].split('"', 1)[0]
                if k in kinds:
                    yield json.loads(line)


class Score:
    """Accuracy per cohort with a baseline and per-game/group coverage; keeps counterexamples."""

    def __init__(self, name, keep=12):
        self.name, self.keep = name, keep
        self.n = collections.Counter(); self.ok = collections.Counter(); self.base = collections.Counter()
        self.games = collections.defaultdict(set); self.groups = collections.defaultdict(set)
        self.errors = collections.defaultdict(list)

    def add(self, r, pred, actual, base=None, extra=None):
        c = r['cohort']
        self.n[c] += 1; self.ok[c] += pred == actual
        if base is not None:
            self.base[c] += base == actual
        self.games[c].add(r['game']); self.groups[c].add(r.get('group'))
        if pred != actual and len(self.errors[c]) < self.keep:
            e = dict(game=r['game'], round=r['round'], actor=r['actor'], type=NAMES[r['type']],
                     predicted=pred, actual=actual)
            if extra:
                e.update(extra)
            self.errors[c].append(e)

    def split(self, cohorts):
        n = sum(self.n[c] for c in cohorts); ok = sum(self.ok[c] for c in cohorts)
        b = sum(self.base[c] for c in cohorts)
        return dict(n=n, ok=ok, acc=round(ok / n, 4) if n else None, base=b, base_acc=round(b / n, 4) if n else None,
                    games=sum(len(self.games[c]) for c in cohorts), groups=sum(len(self.groups[c]) for c in cohorts))

    def report(self):
        return dict(fit=self.split(FIT), held=self.split(HELD),
                    by_cohort={c: self.split([c]) for c in FIT + HELD if self.n[c]},
                    errors={c: v for c, v in self.errors.items() if c in HELD} or dict(self.errors))

    def line(self):
        f, h = self.split(FIT), self.split(HELD)
        fmt = lambda s: f"{s['ok']}/{s['n']} ({100 * (s['acc'] or 0):.1f}%, base {100 * (s['base_acc'] or 0):.1f}%)"
        return f'{self.name}: fit {fmt(f)}  held {fmt(h)}'


def write(path, obj):
    if Path(path).exists():
        raise SystemExit(f'refusing to overwrite {path}')
    Path(path).write_text(json.dumps(obj, indent=1))
