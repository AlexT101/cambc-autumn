#!/usr/bin/env python3
"""The chase builds' share of CAND's out-of-fuel turns, from cg_instrument.py traces (cg_parse.py's rows).

usage: cg_excess.py BATCH_DIR [BATCH_DIR ...]
The aim's builds are split by whether the strike search read the aim (its walk ranked by it; traces with that
field). For each kind of build (aim: chase_aim's, before the strike search; prey: chase's and continue_tribute's), the
hazard P(X) of running out after it by X, the fuel left after the turn's last build of that kind, and the excess
sum over its turns of P(X) - P(X + c), c the turn's builds of that kind: the turns that ran out only for the build's
fuel, if the work after it does not depend on it (fuel-gate.md found this for the retreat's plan)."""
import sys, glob, zipfile, importlib.util, pathlib
from collections import defaultdict, Counter

spec = importlib.util.spec_from_file_location('cgp', pathlib.Path(__file__).with_name('cg_parse.py'))
AIM = {4, 5}
B = 2000


def rows(out):
    for l in out.replace('\x00', '').splitlines():
        if l.startswith('CG ') or l.startswith('CGO '):
            p = l.split()
            try:
                n = int(p[10])
                b = [tuple(map(int, x.split(':'))) for x in p[11:11 + n]]
                yield dict(oof=p[0] == 'CGO', ck=int(p[3]), aim=int(p[5]), b=b, gated=int(p[11 + n]), gated_at=int(p[12 + n]),
                           used=int(p[13 + n]) if len(p) > 13 + n else -1)
            except (IndexError, ValueError):
                continue


turns = {'aim': [], 'aim used': [], 'aim unused': [], 'prey': []}
nbuilds = Counter()
games = 0
for d in sys.argv[1:]:
    for f in glob.glob(f'{d}/*.repl26a'):
        order = f.rsplit('-', 1)[1][:2]
        try:
            z = zipfile.ZipFile(f)
        except zipfile.BadZipFile:
            continue
        team = 'a' if order == '12' else 'b'  # CAND is bot 1
        games += 1
        for r in rows(z.read(f'team-{team}.stdout').decode(errors='replace')):
            for kind, sel, after in (('aim', lambda c: c in AIM, 3), ('aim used', lambda c: c in AIM, 3),
                                     ('aim unused', lambda c: c in AIM, 3), ('prey', lambda c: c not in AIM, 6)):
                bs = [x for x in r['b'] if sel(x[0])]
                if not bs: continue
                if kind == 'aim used' and r['used'] != 1 or kind == 'aim unused' and r['used'] != 0: continue
                nbuilds[(kind, len(bs))] += 1
                cost = sum(x[2] for x in bs)
                x = bs[-1][1] - bs[-1][2]
                turns[kind].append((x, cost, bs[0][1], r['oof'] and r['ck'] >= after, r['ck']))

print(f'{games} CAND team-games')
for kind, ts in turns.items():
    t, o = defaultdict(int), defaultdict(int)
    for x, c, f0, oof, ck in ts:
        t[x // B] += 1
        o[x // B] += oof
    # P(x): the bucket's rate, buckets with few turns pooled with neighbours until 200 turns.
    def P(x):
        k = x // B
        n = m = 0
        lo = hi = k
        n, m = t.get(k, 0), o.get(k, 0)
        while n < 200 and (lo > 0 or hi < 60):
            lo -= 1; hi += 1
            n += t.get(lo, 0) + t.get(hi, 0)
            m += o.get(lo, 0) + o.get(hi, 0)
        return m / n if n else 0.0
    ex = sum(P(x) - P(x + c) for x, c, *_ in ts)
    ran = sum(oof for *_, oof, ck in ts)
    xs = sorted(x for x, *_ in ts)
    cs = sorted(c for _, c, *_ in ts)
    print(f'{kind}: {len(ts) / games:.1f} build turns a team-game, builds a turn {dict(sorted((k[1], v) for k, v in nbuilds.items() if k[0] == kind))}')
    print(f'  fuel left after: p10 {xs[len(xs) // 10]} p50 {xs[len(xs) // 2]} p90 {xs[len(xs) * 9 // 10]}; builds a turn cost mean {sum(cs) / len(cs):.0f}')
    print(f'  ran out after it: {100 * ran / games:.1f} per 100 team-games; excess from its fuel: {100 * ex / games:.1f} per 100')
    by = Counter()
    for x, c, f0, oof, ck in ts:
        if oof: by[ck] += 1
    print('  their checkpoints:', {k: round(100 * v / games, 1) for k, v in sorted(by.items())})
    print('  hazard by X (k): ' + ' '.join(f'{k * 2}:{100 * o[k] / t[k]:.1f}%' for k in sorted(t) if t[k] >= 300))
