"""Compare scorecard datasets against Fish: a markdown and a JSON table, a fidelity summary and the
metrics furthest from Fish.

  py tools/fish/scorecard/compare.py --candidate NAME [--control control-ast37] [--fish fish] --out PREFIX
      -> PREFIX.md, PREFIX.json (metrics.json of each dataset is computed first if missing)

gap: distance from Fish on an effect-size scale (metric_defs.py): Cohen's h for proportions, |ln ratio|
for levels; 0.2 small, 0.5 medium, 0.8 large. ratio = candidate gap / control gap (< 1: the candidate is
closer to Fish than the control). Fidelity = 100 x mean over core metrics of (1 - min(gap, 0.8) / 0.8):
100 means every core metric matches Fish, 0 that every one is a large effect away. A '*' marks a
difference from Fish beyond twice its bootstrap standard error (games resampled), a '~' one within it.
"""
import argparse
import json
import math
import random
from pathlib import Path

import metrics
from metric_defs import defs

MIN_N = {'rate': 20, 'share': 20, 'hshare': 20, 'mean': 10, 'median': 10}
B = 200
_IDX = {}


def hist_of(C, key):
    pre = key + '@'
    return sorted((float(k[len(pre):]), v) for k, v in C.items() if k.startswith(pre) and v)


def median(h):
    n = sum(v for _, v in h)
    if not n:
        return None, 0
    acc = 0
    for x, v in h:
        acc += v
        if acc * 2 >= n:
            return x, n
    return h[-1][0], n


def num_den(C, m):
    k = m['kind']
    if k == 'rate':
        return C.get(m['key'] + '#k', 0), C.get(m['key'] + '#n', 0)
    if k == 'mean':
        return C.get(m['key'] + '#s', 0), C.get(m['key'] + '#n', 0)
    if k == 'share':
        return C.get(m['key'], 0), C.get(m['den'], 0)
    if k == 'hshare':
        pre = m['den'] + '@'
        return C.get(m['key'], 0), sum(v for k, v in C.items() if k.startswith(pre))
    raise ValueError(k)


def value(res, m):
    C = res['total']
    if m['kind'] == 'median':
        v, n = median(hist_of(C, m['key']))
        return (v, n, None) if n >= MIN_N['median'] else (None, n, None)
    a, n = num_den(C, m)
    if n < MIN_N[m['kind']]:
        return None, n, None
    v = a / n
    # Bootstrap standard error over games (the same resamples for every metric of a dataset).
    games = list(res['per_game'].values())
    G = len(games)
    if G not in _IDX:
        rng = random.Random(0)
        _IDX[G] = [rng.choices(range(G), k=G) for _ in range(B)]
    pairs = [num_den(g, m) for g in games]
    bs = []
    for idx in _IDX[G]:
        a_ = sum(pairs[i][0] for i in idx); n_ = sum(pairs[i][1] for i in idx)
        if n_:
            bs.append(a_ / n_)
    if len(bs) <= 10:
        return v, n, None
    mu = sum(bs) / len(bs)
    return v, n, math.sqrt(sum((b - mu) ** 2 for b in bs) / (len(bs) - 1))


def gap(m, f, c):
    if f is None or c is None:
        return None
    if m['scale'] == 'p':
        cl = lambda q: min(1.0, max(0.0, q))
        return abs(2 * math.asin(math.sqrt(cl(c))) - 2 * math.asin(math.sqrt(cl(f))))
    eps = max(1e-3, 0.02 * max(abs(f), abs(c)))
    return min(2.0, abs(math.log(max(c, eps) / max(f, eps))))


def fmt(m, v):
    if v is None:
        return 'n/a'
    if m['scale'] == 'p' and m['kind'] != 'median':
        return f'{100 * v:.1f}%'
    return f'{v:.3g}' if abs(v) < 1000 else f'{v:,.0f}'


def fidelity(rows, col):
    gs = [r[f'gap_{col}'] for r in rows if r['core'] and r.get(f'gap_{col}') is not None]
    return (round(100 * sum(1 - min(g, 0.8) / 0.8 for g in gs) / len(gs), 1), len(gs)) if gs else (None, 0)


def build(fish, cand, ctrl, jobs):
    data = {'fish': metrics.get(fish, jobs)}
    if cand:
        data['cand'] = metrics.get(cand, jobs)
    if ctrl:
        data['ctrl'] = metrics.get(ctrl, jobs)
    rows = []
    for m in defs():
        r = dict(id=m['id'], section=m['section'], label=m['label'], core=m['core'], ref=m['ref'], scale=m['scale'], kind=m['kind'])
        for col, res in data.items():
            v, n, se = value(res, m)
            r[col], r[f'n_{col}'], r[f'se_{col}'] = v, n, se
        for col in ('cand', 'ctrl'):
            if col in data:
                r[f'gap_{col}'] = gap(m, r['fish'], r[col])
                sf, sc = r.get('se_fish'), r.get(f'se_{col}')
                if r[f'gap_{col}'] is not None and sf is not None and sc is not None:
                    se = math.hypot(sf, sc)
                    r[f'sig_{col}'] = abs(r[col] - r['fish']) > 2 * se if se > 0 else r[col] != r['fish']
        if r.get('gap_cand') is not None and r.get('gap_ctrl') is not None:
            r['ratio'] = r['gap_cand'] / r['gap_ctrl'] if r['gap_ctrl'] > 1e-9 else None
        rows.append(r)
    meta = {col: dict(dataset=res['dataset'], parts=res['parts'], games=res['games']) for col, res in data.items()}
    return rows, meta


def mark(r, col):
    s = r.get(f'sig_{col}')
    return '' if s is None else '*' if s else '~'


def markdown(rows, meta, top):
    has_c, has_k = 'cand' in meta, 'ctrl' in meta
    L = ['# Fish fidelity scorecard', '']
    L.append('| column | dataset | games (sides in Fish\'s role) |')
    L.append('| --- | --- | ---: |')
    for col, name in (('fish', 'Fish (ladder)'), ('cand', 'candidate'), ('ctrl', 'control')):
        if col in meta:
            L.append(f"| {name} | `{meta[col]['dataset']}` ({', '.join(meta[col]['parts'])}) | {meta[col]['games']} |")
    L.append('')
    for col, name in (('cand', 'candidate'), ('ctrl', 'control')):
        if col in meta:
            f, n = fidelity(rows, col)
            L.append(f'- **Fidelity, {name}: {f}** over {n} core metrics (100 = Fish on every one).')
    if has_c and has_k:
        both = [r for r in rows if r['core'] and r.get('gap_cand') is not None and r.get('gap_ctrl') is not None]
        closer = sum(r['gap_cand'] < r['gap_ctrl'] for r in both)
        L.append(f'- Candidate closer to Fish than the control on {closer} of {len(both)} core metrics.')
    L.append('')
    lead = 'cand' if has_c else 'ctrl'
    ranked = sorted((r for r in rows if r['core'] and r.get(f'gap_{lead}') is not None), key=lambda r: -r[f'gap_{lead}'])
    L.append(f"## The {top} core metrics furthest from Fish ({'candidate' if has_c else 'control'})")
    L.append('')
    hdr = '| # | metric | section | Fish | ' + ('candidate | ' if has_c else '') + ('control | ' if has_k else '') + 'gap |'
    L.append(hdr); L.append('|' + ' --- |' * (hdr.count('|') - 1))
    for i, r in enumerate(ranked[:top], 1):
        m = r
        cells = [str(i), f"`{r['id']}` {r['label']}", r['section'], fmt(m, r['fish'])]
        if has_c:
            cells.append(fmt(m, r['cand']) + mark(r, 'cand'))
        if has_k:
            cells.append(fmt(m, r['ctrl']) + mark(r, 'ctrl'))
        cells.append(f"{r[f'gap_{lead}']:.2f}")
        L.append('| ' + ' | '.join(cells) + ' |')
    L.append('')
    L.append('## All metrics')
    L.append('')
    L.append('`ref`: FISH_MODEL.md\'s own figure, where it gives one (its definitions can differ slightly). '
             '`*`: beyond 2 bootstrap SE of Fish; `~`: within. gap: effect size against Fish.')
    sec = None
    for r in rows:
        if r['section'] != sec:
            sec = r['section']
            L += ['', f'### {sec}', '']
            h = '| metric | ref | Fish | n | ' + ('candidate | gap | ' if has_c else '') + ('control | gap | ' if has_k else '') + \
                ('ratio |' if has_c and has_k else '')
            L.append(h); L.append('|' + ' --- |' * (h.count('|') - 1))
        m = r
        cells = [f"`{r['id']}` {r['label']}", fmt(m, r['ref']) if r['ref'] is not None else '', fmt(m, r['fish']), str(r['n_fish'])]
        for col in ('cand', 'ctrl'):
            if col in meta:
                g = r.get(f'gap_{col}')
                cells += [fmt(m, r[col]) + mark(r, col), f'{g:.2f}' if g is not None else '']
        if has_c and has_k:
            cells.append(f"{r['ratio']:.2f}" if r.get('ratio') is not None else '')
        L.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fish', default='fish'); ap.add_argument('--candidate'); ap.add_argument('--control')
    ap.add_argument('--out', required=True); ap.add_argument('--jobs', type=int, default=8); ap.add_argument('--top', type=int, default=15)
    a = ap.parse_args()
    if not a.candidate and not a.control:
        raise SystemExit('give --candidate and/or --control')
    rows, meta = build(a.fish, a.candidate, a.control, a.jobs)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out + '.md').write_text(markdown(rows, meta, a.top))
    out = dict(meta=meta, fidelity={c: fidelity(rows, c)[0] for c in ('cand', 'ctrl') if c in meta}, rows=rows)
    Path(a.out + '.json').write_text(json.dumps(out, indent=1) + '\n')
    for c in ('cand', 'ctrl'):
        if c in meta:
            print(f"fidelity {c} ({meta[c]['dataset']}): {fidelity(rows, c)[0]}")
    print('wrote', a.out + '.md', a.out + '.json')


if __name__ == '__main__':
    main()
