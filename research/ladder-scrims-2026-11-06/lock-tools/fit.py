#!/usr/bin/env python3
"""fit.py NORMAL.jsonl [HOLD.jsonl ...]: P(win | state) logistics from states.py rows.

The first file is normal play (knobs off): its model is P(win | normal). Each further file is a hold policy's
games: its model, fit on its leading states (L >= 1), is P(win | that policy), and the report compares the two on
the policy's own states by round, lead and enemy composition. Game-grouped 5-fold CV for the scores."""
import collections, json, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import log_loss, roc_auc_score

NAMES = ['L', 'Lt', 'ct', 'ctt', 'bt', 'cu', 'gu', 'gt', 'earn', 'alive', 'hp', 'str', 'kills', 'lock_u', 'lock_t', 'du', 'dt', 'locks_u', 'one']

def feats(r):
    t = r['R'] / 2000
    return [r['L'] / 100, r['L'] / 100 * t, r['ct'] / 100, r['ct'] / 100 * t, r['bt'] / 100, r['cu'] / 100,
            r['gu'] / 1000, r['gt'] / 1000, (r['earn_u'] - r['earn_t']) / 1000, (r['au'] - r['at']) / r['n'],
            r['hp_u'] / r['mhp_u'] - r['hp_t'] / r['mhp_t'], (r['str_u'] - r['str_t']) / 100, (r['kills_u'] - r['kills_t']) / 10,
            float(r['lock_u']), float(r['lock_t']), min(r['du'][:2]) / 10, min(r['dt'][:2]) / 10, min(r['locks_u'], 4) / 4]

# What the bot can read (perma_lock.cc model_score), the intercept last.
OBS = ['L', 'Lt', 'ct', 'ctt', 'bt', 'cu', 'gu', 'gt', 'alive', 'lock_u', 'lock_t', 't', 'one']
if '--obs' in sys.argv:
    sys.argv.remove('--obs'); NAMES = OBS
    def feats(r):
        t = r['R'] / 2000
        return [r['L'] / 100, r['L'] / 100 * t, r['ct'] / 100, r['ct'] / 100 * t, r['bt'] / 100, r['cu'] / 100, r['gu'] / 1000, r['gt'] / 1000,
                (r['au'] - r['at']) / r['n'], float(r['lock_u']), float(r['lock_t']), t]

def load(p, lead_only=False):
    rows = [json.loads(l) for l in open(p)]
    return [r for r in rows if r['R'] >= 100 and (not lead_only or r['L'] >= 1)]

def fit(rows, C=1.0):
    X = np.array([feats(r) for r in rows]); y = np.array([r['won'] for r in rows]); g = [r['game'] for r in rows]
    oof = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, g):
        m = LogisticRegression(C=C, max_iter=2000).fit(X[tr], y[tr]); oof[te] = m.predict_proba(X[te])[:, 1]
    m = LogisticRegression(C=C, max_iter=2000).fit(X, y)
    return m, X, y, oof

def report(name, m, y, oof):
    print(f'{name}: {len(y)} states, win {y.mean():.3f}, CV logloss {log_loss(y, oof):.4f} (const {log_loss(y, np.full(len(y), y.mean())):.4f}), AUC {roc_auc_score(y, oof):.3f}')
    print('  coef', ' '.join(f'{n}={c:+.2f}' for n, c in zip(NAMES, list(m.coef_[0]) + [m.intercept_[0]])))

normal = load(sys.argv[1])
mn, Xn, yn, oofn = fit(normal)
report('normal', mn, yn, oofn)
lead = [r for r in normal if r['L'] >= 1]
print(f'  normal leading states: {len(lead)}, win {np.mean([r["won"] for r in lead]):.3f}')
for p in sys.argv[2:]:
    hold = load(p, lead_only=True)
    mh, Xh, yh, oofh = fit(hold)
    report(p, mh, yh, oofh)
    pn = mn.predict_proba(Xh)[:, 1]
    print(f'  on its states: actual win {yh.mean():.3f}, normal model predicts {pn.mean():.3f} (hold - normal {yh.mean() - pn.mean():+.3f})')
    # Where the policy beats normal play: actual outcome minus the normal model, by round and lead.
    tab = collections.defaultdict(list)
    for r, y, q in zip(hold, yh, pn):
        rb = min(r['R'] // 250 * 250, 1750); lb = '1-49' if r['L'] < 50 else '50-199' if r['L'] < 200 else '200+'
        tab[(rb, lb)].append(y - q)
    print('  | round | lead 1-49 | lead 50-199 | lead 200+ |  (actual - normal model, states)')
    for rb in range(0, 2000, 250):
        cells = [tab.get((rb, lb)) for lb in ('1-49', '50-199', '200+')]
        print(f'  | {rb} | ' + ' | '.join(f'{np.mean(c):+.3f} ({len(c)})' if c else '-' for c in cells) + ' |')
    w = list(mh.coef_[0] - mn.coef_[0]) + [mh.intercept_[0] - mn.intercept_[0]]
    print('  EV weights (hold - normal logit) for params::plock::model_w:', '{' + ', '.join(f'{x:.4f}f' for x in w) + '}')
    print(f'  hold > normal on {np.mean(mh.predict_proba(Xh)[:, 1] > pn):.3f} of its states')
    comp = collections.defaultdict(list)
    for r, y, q in zip(hold, yh, pn):
        for c in r['comp']: comp[c].append(y - q)
    print('  by enemy champion:', ', '.join(f'{c} {np.mean(v):+.3f} ({len(v)})' for c, v in sorted(comp.items(), key=lambda x: -len(x[1]))))
