"""Which behaviours changed between two batches played on the same maps against the same opponent (CAND vs X and REF vs
X, e.g. two A/Bs that share a reference), and which changes go with the games whose result flipped.

    py tools/replay/abdiff.py --a SRC [SRC ...] --a-team NAME --b SRC [SRC ...] --b-team NAME [--out FILE] [--threads N] [--analysis DIR]

Games pair by map and the focus team's side (A or B). Every number is A's minus B's on the same map and side, with a
95% bootstrap CI over maps. Bots are deterministic, so a paired game differs only through the bots; with different bots
the games diverge from the start, so the per-game differences are effects plus the chaos of a different game.
"Flip association" is the mean difference in games A won and B lost minus that in games A lost and B won: a behaviour
change that drives the result shows up there more strongly than in the mean. Both batches must be extracted into the
same analysis root (extract.mjs --out DIR on both)."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for i, a in enumerate(sys.argv):
    if a == '--analysis' and i + 1 < len(sys.argv):
        os.environ['CAMBC_ANALYSIS'] = sys.argv[i + 1]

import argparse  # noqa: E402
from collections import defaultdict  # noqa: E402

from analysis import load_index, losses, macro, resolve  # noqa: E402
from analysis.cli import extract_all  # noqa: E402
from analysis.util import boot_stat, by_cluster, fmt, mean, md_table, pct  # noqa: E402


def side_of(info, team):
    m = [t for t in (0, 1) if info['names'][t].lower() == team.lower()]
    return m[0] if m else None


def episode_costs(d, t):
    out = defaultdict(float)
    for e in d['losses']['episodes']:
        if e['team'] == t:
            out[losses.ckey(e)] += e['cost']
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--a', nargs='+', required=True, help='batch A replay dirs/files (e.g. CAND vs X)')
    ap.add_argument('--a-team', required=True)
    ap.add_argument('--b', nargs='+', required=True, help='batch B replay dirs/files (e.g. REF vs X)')
    ap.add_argument('--b-team', required=True)
    ap.add_argument('--out', help='write the Markdown here (default stdout)')
    ap.add_argument('--threads', type=int, default=1)
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--analysis')
    args = ap.parse_args()
    index = load_index()
    da, db = resolve(args.a, index), resolve(args.b, index)
    data = extract_all(list(dict.fromkeys(da + db)), args.threads, only=['macro', 'losses'])

    def keyed(dirs, team):
        out = {}
        for d in dirs:
            info = data[d]['info']
            t = side_of(info, team)
            if t is None:
                continue
            out.setdefault((info['map'], t), (d, t))
        return out
    A, B = keyed(da, args.a_team), keyed(db, args.b_team)
    keys = sorted(set(A) & set(B))
    if not keys:
        raise SystemExit('no map and side in common (check --a-team / --b-team)')
    rows = []
    for k in keys:
        (d1, t1), (d2, t2) = A[k], B[k]
        x, y = data[d1], data[d2]
        rows.append({'map': k[0], 'side': k[1], 'da': d1, 'db': d2, 'wa': x['info']['winner'] == t1, 'wb': y['info']['winner'] == t2,
                     'ma': {**x['macro']['sides'][t1], **x['losses']['sides'][t1]}, 'mb': {**y['macro']['sides'][t2], **y['losses']['sides'][t2]},
                     'ca': episode_costs(x, t1), 'cb': episode_costs(y, t2),
                     'opp': (x['info']['names'][1 - t1], y['info']['names'][1 - t2])})
    n = len(rows)
    up = [r for r in rows if r['wa'] and not r['wb']]
    down = [r for r in rows if not r['wa'] and r['wb']]
    L = [f'# Behaviour diff: {args.a_team} (A) against {args.b_team} (B)', '',
         f'{n} paired games (map and side). Opponents: A {sorted({r["opp"][0] for r in rows})}, B {sorted({r["opp"][1] for r in rows})}.', '',
         f'Win rate A {pct(mean([r["wa"] for r in rows]), 1)}, B {pct(mean([r["wb"] for r in rows]), 1)}; flips: {len(up)} games A won and B lost, '
         f'{len(down)} A lost and B won, {n - len(up) - len(down)} the same.', '',
         'Columns: mean A, mean B, mean A - B with a 95% bootstrap CI over maps; "flip assoc." = mean (A - B) in the games A won and B lost '
         'minus that in the games A lost and B won (large when the change goes with the flips). Sorted by |diff| / CI half-width.', '']

    def diff_row(name, fa, fb, desc, rate):
        vals = [(r['map'], fa(r), fb(r)) for r in rows]
        vals = [(m, a, b) for m, a, b in vals if a is not None and b is not None]
        if len(vals) < 4:
            return None
        lo, hi = boot_stat(list(by_cluster([(m, a - b) for m, a, b in vals]).values()), lambda xs: sum(xs) / len(xs), B=400)
        dm = mean([a - b for _, a, b in vals])
        fu = mean([fa(r) - fb(r) for r in up if fa(r) is not None and fb(r) is not None])
        fd = mean([fa(r) - fb(r) for r in down if fa(r) is not None and fb(r) is not None])
        f = (lambda v: '-' if v is None else f'{100 * v:+.1f}pt') if rate else (lambda v: '-' if v is None else ('+' if v > 0 else '') + fmt(v))
        g = (lambda v: pct(v, 1)) if rate else fmt
        half = (hi - lo) / 2 if lo is not None else None
        score = abs(dm) / half if half else 0
        return score, [name, g(mean([a for _, a, _ in vals])), g(mean([b for _, _, b in vals])),
                       f(dm) + (f' [{f(lo)} .. {f(hi)}]' if lo is not None else ''), f(fu - fd) if fu is not None and fd is not None else '-', desc]

    out = []
    for key, (desc, better, opp) in {**macro.METRICS, **losses.METRICS}.items():
        res = diff_row(key, lambda r, k=key: r['ma'].get(k), lambda r, k=key: r['mb'].get(k), desc, key in macro.RATEISH)
        if res:
            out.append(res)
    out.sort(key=lambda x: -x[0])
    L += ['## Behaviour metrics', '', md_table(['metric', 'A', 'B', 'A - B [95% CI]', 'flip assoc.', 'definition'], [x[1] for x in out]), '']

    allk = set()
    for r in rows:
        allk |= set(r['ca']) | set(r['cb'])
    out = []
    for k in allk:
        res = diff_row(losses._ckeystr(k), lambda r, k=k: r['ca'].get(k, 0.0), lambda r, k=k: r['cb'].get(k, 0.0), '', False)
        if res and (abs(mean([r['ca'].get(k, 0.0) for r in rows])) + abs(mean([r['cb'].get(k, 0.0) for r in rows]))) >= 1:
            out.append(res)
    out.sort(key=lambda x: -x[0])
    L += ['## Loss episode clusters (gems per game)', '',
          md_table(['cluster', 'A', 'B', 'A - B [95% CI]', 'flip assoc.'], [x[1][:5] for x in out[:args.top]]), '']

    def biggest(r):
        ks = set(r['ca']) | set(r['cb'])
        dd = sorted(((r['ca'].get(k, 0) - r['cb'].get(k, 0), k) for k in ks), key=lambda x: -abs(x[0]))[:3]
        return '; '.join(f'{losses._ckeystr(k)} {v:+.0f}' for v, k in dd)
    for title, sel in (('Games A lost and B won (regressions)', down), ('Games A won and B lost', up)):
        sel = sorted(sel, key=lambda r: -abs(sum(r['ca'].values()) - sum(r['cb'].values())))
        L += [f'## {title}', '', 'Open with `py tools/replay/triage.py DIR --team NAME` (A dir with the A team, B dir with the B team).', '',
              md_table(['map', 'side', 'A dir', 'B dir', 'episode cost A - B', 'largest cluster differences'],
                       [[r['map'], 'AB'[r['side']], r['da'], r['db'], fmt(sum(r['ca'].values()) - sum(r['cb'].values())), biggest(r)] for r in sel[:15]]), '']
    text = '\n'.join(L)
    if args.out:
        Path(args.out).write_text(text, encoding='utf-8')
        print(f'{n} pairs -> {args.out}')
    else:
        print(text)


if __name__ == '__main__':
    main()
