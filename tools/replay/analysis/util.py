import csv
import math
import random
from collections import defaultdict


def clean(xs):
    return [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]


def mean(xs):
    xs = clean(xs)
    return sum(xs) / len(xs) if xs else None


def quantile(xs, q):
    xs = sorted(clean(xs))
    if not xs:
        return None
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def median(xs):
    return quantile(xs, 0.5)


def rate(k, n):
    return k / n if n else None


def wilson(k, n, z=1.96):
    if not n:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def fmt(x, nd=1):
    if x is None:
        return '-'
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if abs(x) >= 100 or x == int(x) and abs(x) >= 10:
            return f'{x:.0f}'
        return f'{x:.{nd}f}'
    return str(x)


def pct(x, nd=0):
    return '-' if x is None else f'{100 * x:.{nd}f}%'


def wr(k, n):
    """Win rate with sample size and 95% interval."""
    if not n:
        return '- (n=0)'
    lo, hi = wilson(k, n)
    return f'{100 * k / n:.0f}% (n={n}, {100 * lo:.0f}-{100 * hi:.0f})'


def mqr(xs, nd=1):
    """median [p25-p75] (n)."""
    xs = clean(xs)
    if not xs:
        return '- (n=0)'
    return f'{fmt(median(xs), nd)} [{fmt(quantile(xs, .25), nd)}-{fmt(quantile(xs, .75), nd)}] (n={len(xs)})'


def md_table(headers, rows):
    out = ['| ' + ' | '.join(str(h) for h in headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
    for r in rows:
        out.append('| ' + ' | '.join(str(fmt(c)).replace('|', '/') for c in r) + ' |')
    return '\n'.join(out)


BOOT = {'B': 1000, 'seed': 1}


def boot_ratio(clusters, B=None, seed=None):
    """clusters: [(k, n)] per cluster. 95% percentile CI of sum(k) / sum(n), resampling whole clusters."""
    clusters = [c for c in clusters if c[1]]
    if len(clusters) < 2:
        return (None, None)
    rng = random.Random(BOOT['seed'] if seed is None else seed)
    m = len(clusters)
    out = []
    for _ in range(B or BOOT['B']):
        k = n = 0
        for i in rng.choices(range(m), k=m):
            k += clusters[i][0]
            n += clusters[i][1]
        out.append(k / n if n else 0)
    out.sort()
    return (out[int(0.025 * len(out))], out[int(0.975 * len(out)) - 1])


def boot_stat(groups, stat, B=None, seed=None):
    """groups: [[item, ...]] per cluster; stat(items) -> number. 95% percentile CI resampling clusters."""
    groups = [g for g in groups if g]
    if len(groups) < 2:
        return (None, None)
    rng = random.Random(BOOT['seed'] if seed is None else seed)
    m = len(groups)
    out = []
    for _ in range(B or BOOT['B']):
        items = []
        for i in rng.choices(range(m), k=m):
            items += groups[i]
        v = stat(items)
        if v is not None:
            out.append(v)
    if not out:
        return (None, None)
    out.sort()
    return (out[int(0.025 * len(out))], out[min(len(out) - 1, int(0.975 * len(out)))])


def by_cluster(items):
    """items: [(cluster, value)] -> {cluster: [values]}."""
    out = defaultdict(list)
    for c, v in items:
        out[c].append(v)
    return out


def cwr(items):
    """Win rate over (cluster, won) items with n, number of clusters and a cluster-bootstrap 95% CI."""
    items = [(c, w) for c, w in items if w is not None]
    if not items:
        return '- (n=0)'
    cl = by_cluster(items)
    k = sum(w for _, w in items)
    lo, hi = boot_ratio([(sum(v), len(v)) for v in cl.values()])
    ci = f', {100 * lo:.0f}-{100 * hi:.0f}' if lo is not None else ''
    return f'{100 * k / len(items):.0f}% (n={len(items)}, c={len(cl)}{ci})'


def crate(items, scale=1, nd=2):
    """Pooled ratio over (cluster, k, n) items with a cluster-bootstrap CI."""
    items = [(c, k, n) for c, k, n in items if k is not None and n]
    if not items:
        return '-'
    cl = defaultdict(lambda: [0, 0])
    for c, k, n in items:
        cl[c][0] += k
        cl[c][1] += n
    K, N = sum(v[0] for v in cl.values()), sum(v[1] for v in cl.values())
    lo, hi = boot_ratio([tuple(v) for v in cl.values()])
    ci = f' [{fmt(scale * lo, nd)}-{fmt(scale * hi, nd)}]' if lo is not None else ''
    return f'{fmt(scale * K / N, nd)}{ci} (c={len(cl)})'


def paired(pairs):
    """pairs of (winner value, loser value[, cluster]): share where winner > loser / < loser, median difference, with cluster-bootstrap CIs."""
    pairs = [p if len(p) == 3 else (p[0], p[1], None) for p in pairs]
    pairs = [(a, b, c) for a, b, c in pairs if a is not None and b is not None]
    if not pairs:
        return None
    gt = sum(1 for a, b, _ in pairs if a > b)
    lt = sum(1 for a, b, _ in pairs if a < b)
    groups = list(by_cluster([(c if c is not None else i, (a - b, 1 if a > b else -1 if a < b else 0)) for i, (a, b, c) in enumerate(pairs)]).values())
    ci_gt = boot_ratio([(sum(1 for _, s in g if s > 0), len(g)) for g in groups])
    ci_lt = boot_ratio([(sum(1 for _, s in g if s < 0), len(g)) for g in groups])
    ci_diff = boot_stat(groups, lambda items: median([d for d, _ in items]), B=300)
    return {'n': len(pairs), 'gt': gt, 'lt': lt, 'eq': len(pairs) - gt - lt, 'diff': median([a - b for a, b, _ in pairs]),
            'clusters': len(groups), 'ci_gt': ci_gt, 'ci_lt': ci_lt, 'ci_diff': ci_diff}


def _ci(ci, f=lambda x: pct(x)):
    return f'{f(ci[0])}-{f(ci[1])}' if ci and ci[0] is not None else '-'


def paired_str(p, lower_better=False):
    if not p:
        return '- (n=0)'
    if lower_better:
        return (f'winner lower in {p["lt"]}/{p["n"]} ({pct(p["lt"] / p["n"])}, 95% CI {_ci(p["ci_lt"])}), higher in {p["gt"]}, '
                f'median diff {fmt(p["diff"])} [{_ci(p["ci_diff"], fmt)}], {p["clusters"]} clusters')
    return (f'winner higher in {p["gt"]}/{p["n"]} ({pct(p["gt"] / p["n"])}, 95% CI {_ci(p["ci_gt"])}), lower in {p["lt"]}, '
            f'median diff {fmt(p["diff"])} [{_ci(p["ci_diff"], fmt)}], {p["clusters"]} clusters')


CAVEAT = ('Reverse causality: winner-vs-loser differences partly reflect winning (a team that is ahead dies less, banks more gold and fights on its own terms). '
          'Prefer the early-window and lead-conditioned comparisons, and treat the rest as correlations. '
          'CIs are 95% cluster bootstraps over match groups (ladder: one five-game group = one cluster; local batches: one map pair = one cluster); c = clusters.')


SCALE = ' .:-=+*#%@'


def ascii_grid(mp, values, levels, mask=None, landmarks=False):
    """Render a cell grid (team A frame, north up). values: {cell: number}. levels: ascending thresholds for SCALE[1:]."""
    cw, ch = mp.grid_size
    marks = mp.landmarks if landmarks else {}
    lines = []
    for cy in range(ch - 1, -1, -1):
        row = []
        for cx in range(cw):
            c = (cx, cy)
            if landmarks:
                row.append(marks.get(c, '.'))
                continue
            if mask is not None and c not in mask:
                row.append(' ')
                continue
            v = values.get(c)
            if v is None:
                row.append(' ')
                continue
            k = 0
            for i, t in enumerate(levels):
                if v >= t:
                    k = i + 1
            row.append(SCALE[min(k, len(SCALE) - 1)])
        lines.append(''.join(row))
    return lines


def side_by_side(blocks, titles, gap=3):
    widths = [max([len(t)] + [len(l) for l in b]) for b, t in zip(blocks, titles)]
    height = max(len(b) for b in blocks)
    out = ['   '.join(t.ljust(w) for t, w in zip(titles, widths)).rstrip()]
    for i in range(height):
        out.append((' ' * gap).join((b[i] if i < len(b) else '').ljust(w) for b, w in zip(blocks, widths)).rstrip())
    return out


class Report:
    def __init__(self, name, title, out_dir):
        self.name = name
        self.title = title
        self.out_dir = out_dir
        self.lines = [f'# {title}', '']
        self.highlights = []
        self.csvs = []

    def h(self, text, level=2):
        self.lines += [f'{"#" * level} {text}', '']

    def p(self, *texts):
        for t in texts:
            self.lines += [t, '']

    def bullets(self, items):
        self.lines += [f'- {i}' for i in items] + ['']

    def code(self, lines):
        self.lines += ['```'] + list(lines) + ['```', '']

    def table(self, headers, rows, csv_name=None, limit=None, csv_rows=None):
        rows = list(rows)
        if csv_name:
            self.write_csv(csv_name, headers, csv_rows if csv_rows is not None else rows)
        shown = rows[:limit] if limit else rows
        self.lines += [md_table(headers, shown), '']
        if limit and len(rows) > limit:
            self.lines += [f'({len(rows) - limit} more rows' + (f' in `{self.name}-{csv_name}.csv`)' if csv_name else ')'), '']

    def write_csv(self, csv_name, headers, rows):
        fn = f'{self.name}-{csv_name}.csv'
        with open(self.out_dir / fn, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(headers)
            for r in rows:
                w.writerow(['' if c is None else (round(c, 4) if isinstance(c, float) else c) for c in r])
        self.csvs.append(fn)

    def highlight(self, text):
        self.highlights.append(text)

    def save(self):
        path = self.out_dir / f'{self.name}.md'
        path.write_text('\n'.join(self.lines).rstrip() + '\n', encoding='utf-8')
        return path


def group_by(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[key(r)].append(r)
    return out
