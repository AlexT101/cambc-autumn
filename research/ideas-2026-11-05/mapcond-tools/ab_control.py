"""Is the oc2 tune's map heterogeneity specific to its constants, or the same compression every A/B shows?
Normalised slopes (slope / mean effect) of unrelated A/Bs against the oc2 tune's."""
import json, sys
import numpy as np
src = open(__import__('pathlib').Path(__file__).resolve().parent / 'ab_het.py').read()
exec(src.split('C = {')[0])
def fitn(per):
    ms = sorted(m for m in per if m in F)
    y = np.array([np.mean(per[m]) for m in ms]); w = np.array([len(per[m]) for m in ms], float)
    Z = np.array([[F[m][f] for f in FEATS] for m in ms]); Z = (Z - Z.mean(0)) / Z.std(0)
    X = np.column_stack([np.ones(len(y)), Z]); Xw = X * w[:, None]; A = np.linalg.inv(X.T @ Xw); b = A @ (Xw.T @ y)
    r = y - X @ b; V = A @ ((X * (w * r)[:, None]).T @ (X * (w * r)[:, None])) @ A
    m0 = np.average(y, weights=w)
    return b[1:] / m0, np.sqrt(np.diag(V))[1:] / abs(m0), m0, int(w.sum()), len(ms) / max(1, len(per))
tests = {'oc2 tune (oct-a)': direct('oct-tuned-vs-base1'),
         'oc2 tune (oct-b paired)': merge(paired('oct-tuned-vs-astraeus', 'oct-base1-vs-astraeus'), paired('oct-tuned-vs-proteus', 'oct-base1-vs-proteus'))}
ctrl = {n: direct(n) for n in ['oct-base1-vs-astraeus', 'oct-base1-vs-proteus', 'ocean-d5-vs-ast', 'oport-fix', 'v2-conf-f5', 'v2-conf2-f5sf300mc',
                               'oc3-vs-astr-now-1105', 'oc3-vs-panel-astraeus', 'oc4-ast', 'ceil-5b66bde', 'gv-farm']}
print('normalised slope per SD (slope / mean effect); SE in brackets')
print(f'{"":30s} {"mean":>6s} {"games":>6s} ' + ' '.join(f'{f[:10]:>11s}' for f in FEATS))
rows = {}
for n, per in {**tests, **ctrl}.items():
    b, se, m0, g, cov = fitn(per); rows[n] = (b, se)
    print(f'{n:30s} {100 * m0:+6.2f} {g:6d} ' + ' '.join(f'{x:+5.2f}({s:.2f})' for x, s in zip(b, se)) + ('' if cov > .99 else f'  [{100 * cov:.0f}% maps featured]'))
cb = np.array([rows[n][0] for n in ctrl]); cs = np.array([rows[n][1] for n in ctrl])
wt = 1 / cs ** 2; pool = (cb * wt).sum(0) / wt.sum(0); pse = 1 / np.sqrt(wt.sum(0))
print(f'{"controls, inverse-variance pooled":30s} {"":6s} {"":6s} ' + ' '.join(f'{x:+5.2f}({s:.2f})' for x, s in zip(pool, pse)))
# between-control spread (do controls agree with each other?)
chi = (((cb - pool) / cs) ** 2).sum(0)
print('controls heterogeneity chi2 per feature (df %d): ' % (len(ctrl) - 1) + ' '.join(f'{f}={c:.0f}' for f, c in zip(FEATS, chi)))
for n in tests:
    b, se = rows[n]; z = (b - pool) / np.sqrt(se ** 2 + pse ** 2)
    print(f'{n}: corr with pooled controls {np.corrcoef(b, pool)[0, 1]:+.2f}; difference from controls chi2(9) {np.sum(z ** 2):.1f}; z by feature ' + ' '.join(f'{f}={x:+.1f}' for f, x in zip(FEATS, z)))
