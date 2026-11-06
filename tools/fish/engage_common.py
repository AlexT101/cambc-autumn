"""Shared loading, opportunity filters, split and scoring for the engage_* studies (ENGAGE.md).

Fit cohorts: model, confirm, third, fourth. Held out: fifth, sixth (and seventh once pinned).
Rows: replays/fish-engage/<cohort>-rows-v1.jsonl.gz (engage_rows.py), one game a line.
"""
import collections
import gzip
import json
import multiprocessing as mp
from pathlib import Path

FIT = ['model', 'confirm', 'third', 'fourth']
HELD = ['fifth', 'sixth']
ROWS = Path('replays/fish-engage')
NAMES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren',
         'Varg', 'Tavi', 'HoR']
RANGED = {1, 3, 5, 6, 8, 11}
# A champion's reach for the "in reach" test of TEAM.md 1d: ranged 3, melee 2 (walk + hit).
REACH = {t: (3 if t in RANGED else 2) for t in range(13)}
# Threat reach: farthest distance at which a champion's one-turn damage (combat_common D) is positive
# with everything ready: dash +2, unit spells 4, ground spells 5, Heart of Ruin's dash 4.
THREAT_REACH = {0: 5, 1: 5, 2: 4, 3: 4, 4: 4, 5: 5, 6: 5, 7: 4, 8: 3, 9: 4, 10: 2, 11: 4, 12: 4}


def games(cohort, path=ROWS):
    with gzip.open(Path(path) / f'{cohort}-rows-v1.jsonl.gz', 'rt') as f:
        for line in f:
            yield json.loads(line)


def cohort_games(cohorts):
    for c in cohorts:
        yield from games(c)


def pool_map(fn, cohorts, jobs=6):
    """fn(game dict) -> list; flattened over every game of `cohorts`, at most `jobs` processes."""
    with mp.Pool(jobs) as p:
        out = []
        for c in cohorts:
            for res in p.imap_unordered(fn, _lines(c), chunksize=2):
                out.extend(res)
        return out


def _lines(cohort):
    with gzip.open(ROWS / f'{cohort}-rows-v1.jsonl.gz', 'rt') as f:
        for line in f:
            yield line


def hpf(x):
    return x['hp'] / x['mhp']


def free(x):
    """Alive, unstunned, off spawn, not channelling a tribute (2) or teleport (3)."""
    return not x['stn'] and not x['home'] and x['ch'] not in (2, 3)


class Score:
    def __init__(self, name, keep=12):
        self.name, self.keep = name, keep
        self.n = collections.Counter(); self.ok = collections.Counter(); self.base = collections.Counter()
        self.games = collections.defaultdict(set); self.groups = collections.defaultdict(set)
        self.errors = collections.defaultdict(list)

    def add(self, r, pred, actual, base=None):
        c = r['cohort']
        self.n[c] += 1; self.ok[c] += pred == actual
        if base is not None:
            self.base[c] += base == actual
        self.games[c].add(r['game']); self.groups[c].add(r.get('group'))
        if pred != actual and len(self.errors[c]) < self.keep:
            self.errors[c].append(dict(game=r['game'], round=r['round'], actor=r['actor'], type=NAMES[r['type']],
                                       predicted=pred, actual=actual))

    def split(self, cohorts):
        n = sum(self.n[c] for c in cohorts); ok = sum(self.ok[c] for c in cohorts)
        b = sum(self.base[c] for c in cohorts)
        return dict(n=n, ok=ok, acc=round(ok / n, 4) if n else None, base=b, base_acc=round(b / n, 4) if n else None,
                    games=sum(len(self.games[c]) for c in cohorts), groups=len(set().union(*[self.groups[c] for c in cohorts])) if cohorts else 0)

    def report(self, held=HELD):
        return dict(fit=self.split(FIT), held=self.split(held),
                    by_cohort={c: self.split([c]) for c in FIT + list(held) if self.n[c]},
                    errors={c: self.errors[c] for c in held if self.errors[c]})

    def line(self, held=HELD):
        f, h = self.split(FIT), self.split(held)
        fmt = lambda s: f"{s['ok']}/{s['n']} ({100 * (s['acc'] or 0):.1f}%, base {100 * (s['base_acc'] or 0):.1f}%)"
        return f'{self.name}: fit {fmt(f)}  held {fmt(h)}'


def write(path, obj):
    if Path(path).exists():
        raise SystemExit(f'refusing to overwrite {path}')
    Path(path).write_text(json.dumps(obj, indent=1) + '\n')
