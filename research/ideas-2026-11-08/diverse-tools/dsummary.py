"""Per-body calibration and a live-consistency score per design (diverse-panel.md).   python3 dsummary.py"""
import os, sys, io, contextlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import dcalib as D
IND = [('base23', 'base25'), ('base25', 'base26'), ('base26', 'base27'), ('base27', 'base29'), ('base27', 's2-soupk27')]
LIVE_SE = {}
for a, b in IND + [('base23', 'base29')]:
    va, vb = D.VER[a], D.VER[b]
    e = np.array([D.C[(vb, m, s, o)] - D.C[(va, m, s, o)] for (v, m, s, o) in D.C if v == va and (vb, m, s, o) in D.C])
    LIVE_SE[(a, b)] = (100 * e.mean(), 100 * e.std() / np.sqrt(len(e)))
print('per body (pooled F/M where live drafts):')
bodies = {}
for key in ('tuneL', 'noiseL', 'tuneTD', 'cur'):
    for m in D.DESIGNS[key][1]:
        bodies.setdefault((key, m[0] if key != 'tuneTD' and key != 'cur' else m[1]), []).append(m)
for (key, b), ms in bodies.items():
    D.DESIGNS['_b'] = ('', ms)
    with contextlib.redirect_stdout(io.StringIO()) as f: D.evaluate('_b')
    line = [l for l in f.getvalue().splitlines() if 'per-map r' in l][0]
    print(f'  {key:7s} {b:10s} {line.strip()[:110]}')
print('\ndesign      r     sign agree (5 indep. + 86->91)  chi2 vs live (5 indep., df 5)  z(86->91)  games per A/B')
for key in ('cur', 'spar', 'tuneL', 'noiseL', 'noise5-8', 'noise8', 'tuneTD', 'divL', 'all-L'):
    with contextlib.redirect_stdout(io.StringIO()): o = D.evaluate(key)
    chi = 0; agree = 0
    for p in IND + [('base23', 'base29')]:
        d, ci, lv = o[p]; lse = LIVE_SE[p][1]; se = ci / 1.96
        agree += np.sign(d) == np.sign(lv)
        if p in IND: chi += (d - lv) ** 2 / (se ** 2 + lse ** 2)
    d, ci, lv = o[('base23', 'base29')]; z = (d - lv) / np.hypot(ci / 1.96, LIVE_SE[('base23', 'base29')][1])
    print(f'{key:8s} {o["r"]:+.2f}   {agree}/6   {chi:5.1f}   {z:+.2f}   {o["members"] * 512}')
