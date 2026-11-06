"""Bucket tables of the tune effect, slope agreement between independent A/Bs, and cross-validated choice policies."""
import json, sys
import numpy as np
sys.argv = ['x']; exec(open(__import__('pathlib').Path(__file__).resolve().parent / 'ab_het.py').read().split('rng = np.random')[0])
def arr(per):
    ms = sorted(m for m in per if m in F)
    return ms, np.array([np.mean(per[m]) for m in ms]), np.array([len(per[m]) for m in ms], float)
# buckets
def bucket(f, vals):
    if f == 'picks': return vals.astype(int).astype(str)
    if f == 'sym': return vals
    if f == 'altars': return np.where(vals <= 1, '1', np.where(vals == 2, '2', '3+'))
    if f == 'big_share': return np.where(vals == 0, '0', np.where(vals < np.median(vals[vals > 0]), 'lo', 'hi'))
    q = np.quantile(vals.astype(float), [1 / 3, 2 / 3]); return np.where(vals <= q[0], 'T1', np.where(vals <= q[1], 'T2', 'T3'))
BF = ['log_area', 'picks', 'sym', 'spawn_dist', 'camps_side', 'camp_density', 'log_gems', 'big_share', 'altars']
for name in ['oc2 direct (oct-a)', 'oc2 paired vs astraeus+proteus (oct-b)', 'oc3 direct (confirm)', 'oc3 direct (confirm2)', 'oc3 paired vs panel (pchk+p2)']:
    ms, y, w = arr(C[name]); print(f'\n== {name}: effect in pts by bucket (games), +- 1 SE')
    for f in BF:
        v = np.array([F[m][f] for m in ms]); b = bucket(f, v); cells = []
        for k in sorted(set(b)):
            s = b == k; e = np.average(y[s], weights=w[s]); se = np.sqrt(np.average((y[s] - e) ** 2, weights=w[s]) / w[s].sum() * (w[s].mean()))
            cells.append(f'{k} {100 * e:+.1f}+-{100 * se:.1f} ({int(w[s].sum())})')
        print(f'  {f:12s} ' + ' | '.join(cells))
# slope agreement
R = json.load(open(W / 'ab-het.json'))
def agree(a, b):
    ba, sa, bb, sb = (np.array(R[a]['b'][1:]), np.array(R[a]['se'][1:]), np.array(R[b]['b'][1:]), np.array(R[b]['se'][1:]))
    z = (ba - bb) / np.sqrt(sa ** 2 + sb ** 2)
    print(f'{a} vs {b}: slope corr {np.corrcoef(ba, bb)[0, 1]:+.2f}, heterogeneity of slopes chi2(9) {np.sum(z ** 2):.1f}')
print()
agree('oc2 direct (oct-a)', 'oc2 paired vs astraeus+proteus (oct-b)')
agree('oc3 direct (confirm)', 'oc3 direct (confirm2)')
agree('oc3 direct (confirm)', 'oc3 paired vs panel (pchk+p2)')
agree('oc2 direct (oct-a)', 'oc3 direct (confirm)')
# cross-validated policies: choose the tuned vector on a map iff the training set's model says it beats the other there
def policy_eval(train, test, kind, lam=0.0):
    mt, yt, wt = arr(C[train]); me, ye, we = arr(C[test])
    Zt = np.array([[F[m][f] for f in FEATS] for m in mt]); Ze = np.array([[F[m][f] for f in FEATS] for m in me])
    mu, sd = Zt.mean(0), Zt.std(0); Zt, Ze = (Zt - mu) / sd, (Ze - mu) / sd
    if kind == 'linear':
        X = np.column_stack([np.ones(len(yt)), Zt]); b = np.linalg.solve((X * wt[:, None]).T @ X + lam * np.diag([0] + [1] * len(FEATS)), (X * wt[:, None]).T @ yt)
        pick = np.column_stack([np.ones(len(ye)), Ze]) @ b > 0
    else:  # best single-feature bucket rule chosen on train
        best = None
        for f in BF:
            vt = np.array([F[m][f] for m in mt]); ve = np.array([F[m][f] for m in me])
            bt, be = bucket(f, vt), bucket(f, ve)
            sel = {k: np.average(yt[bt == k], weights=wt[bt == k]) > 0 for k in set(bt)}
            gain = sum(np.sum((yt * wt)[bt == k]) for k in sel if sel[k]) / wt.sum()
            if best is None or gain > best[0]: best = (gain, f, sel, be)
        _, f, sel, be = best; pick = np.array([sel.get(k, True) for k in be]); kind = f'bucket:{f}'
    g = np.sum((ye * we)[pick]) / we.sum(); allt = np.sum(ye * we) / we.sum()
    # SE of the held-out policy value minus always-tuned (games on maps where they differ)
    d = np.where(pick, 0, -ye); se = np.sqrt(np.sum(we * (d - np.average(d, weights=we)) ** 2)) / we.sum()
    print(f'  train {train} -> test {test}, {kind}: tuned on {100 * np.average(pick, weights=we):.0f}% of maps; '
          f'held-out effect vs untuned {100 * g:+.2f} pts (always tuned {100 * allt:+.2f}; policy - always-tuned {100 * (g - allt):+.2f} +- {100 * se:.2f})')
print('\ncross-validated choice between tuned and untuned by map features:')
for tr, te in [('oc2 direct (oct-a)', 'oc2 paired vs astraeus+proteus (oct-b)'), ('oc2 paired vs astraeus+proteus (oct-b)', 'oc2 direct (oct-a)'),
               ('oc3 direct (confirm)', 'oc3 direct (confirm2)'), ('oc3 direct (confirm2)', 'oc3 direct (confirm)'), ('oc3 direct (confirm)', 'oc3 paired vs panel (pchk+p2)')]:
    for kind in ['linear', 'bucket']: policy_eval(tr, te, kind)
