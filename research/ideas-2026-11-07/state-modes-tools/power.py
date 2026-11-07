"""Which state the bot can read predicts the result: tributed lead, carried lead, spent gold (items: visible on
sight) and unspent gold (hidden). Samples every 50 rounds from 100, game-weighted, logistic, held out by game.
usage: power.py ANALYSIS_DIR SET"""
import gzip, json, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import log_loss

SET = sys.argv[2]


def one(d):
    try:
        m = json.load(open(os.path.join(d, 'meta.json')))
        names = [t.get('name') for t in m['teams']]
        if SET == 'ladder':
            if 'stellar best girl' not in names: return None
            us = names.index('stellar best girl')
        elif SET == 'oa':
            if sorted(names) != ['astraeus', 'ocean']: return None
            us = names.index('ocean')
        else:
            if names != ['ocean', 'ocean']: return None
            us = int(os.path.basename(d)[-1], 16) % 2
        r = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        last = m['result']['rounds']
        out = []
        for i, rd in enumerate(r['round']):
            if rd < 100 or rd % 50 or rd >= last: continue
            v = [[0.0] * 4 for _ in range(2)]
            for c in r['champions']:
                t = c['team']
                v[t][0] += 0; v[t][1] += c['gems'][i]; v[t][2] += c['earned'][i] - c['gold'][i]; v[t][3] += c['gold'][i]
            for t in (0, 1): v[t][0] = r['gems'][t][i]
            th = 1 - us
            out.append([rd] + [v[us][k] - v[th][k] for k in range(4)])
        return {'g': os.path.basename(d), 'opp': names[1 - us], 'win': int(m['result']['winner'] == us), 'x': out}
    except Exception as e:
        print('skip', d, e, file=sys.stderr)


def main():
    dirs = [os.path.join(sys.argv[1], x) for x in os.listdir(sys.argv[1]) if os.path.exists(os.path.join(sys.argv[1], x, 'meta.json'))]
    with ProcessPoolExecutor(16) as p:
        games = [g for g in p.map(one, dirs, chunksize=4) if g and g['x']]
    X, y, grp, w, rd = [], [], [], [], []
    opps = sorted(set(g['opp'] for g in games))
    for gi, g in enumerate(games):
        for s in g['x']:
            X.append(s[1:] + [1.0 if g['opp'] == o else 0.0 for o in opps]); y.append(g['win']); grp.append(gi); w.append(1 / len(g['x'])); rd.append(s[0])
    X = np.array(X); y = np.array(y); w = np.array(w); rd = np.array(rd)
    X[:, 0:2] /= 100; X[:, 2:4] /= 500
    nf = len(opps) if SET == 'ladder' else 0
    names = ['trib/100', 'carried/100', 'spent/500', 'unspent/500']
    print(f'## {SET}: {len(games)} games, {len(y)} samples')
    for label, cols in [('trib', [0]), ('trib+carried', [0, 1]), ('trib+carried+spent', [0, 1, 2]), ('+unspent (all)', [0, 1, 2, 3]),
                        ('trib+spent', [0, 2])]:
        cc = cols + list(range(4, 4 + nf))
        pred = np.zeros(len(y))
        for tr, te in GroupKFold(5).split(X, y, grp):
            mdl = LogisticRegression(C=10, max_iter=2000, fit_intercept=(nf == 0)).fit(X[tr][:, cc], y[tr], sample_weight=w[tr])
            pred[te] = mdl.predict_proba(X[te][:, cc])[:, 1]
        mdl = LogisticRegression(C=10, max_iter=2000, fit_intercept=(nf == 0)).fit(X[:, cc], y, sample_weight=w)
        print(f'  {label:22} held-out log loss {log_loss(y, pred, sample_weight=w):.4f}   coefs ' +
              ', '.join(f'{names[c]} {mdl.coef_[0][i]:+.2f}' for i, c in enumerate(cols)))
    # Same, by round band.
    for lo, hi in [(100, 400), (400, 800), (800, 2000)]:
        sel = (rd >= lo) & (rd < hi)
        cc = [0, 1, 2, 3] + list(range(4, 4 + nf))
        mdl = LogisticRegression(C=10, max_iter=2000, fit_intercept=(nf == 0)).fit(X[sel][:, cc], y[sel], sample_weight=w[sel])
        print(f'  rounds {lo}-{hi}: ' + ', '.join(f'{names[i]} {mdl.coef_[0][i]:+.2f}' for i in range(4)))
    c = np.corrcoef(X[:, 2], X[:, 3])[0, 1]
    print(f'  corr(spent, unspent) {c:+.2f}; corr(spent, carried) {np.corrcoef(X[:,2], X[:,1])[0,1]:+.2f}; corr(trib, carried) {np.corrcoef(X[:,0], X[:,1])[0,1]:+.2f}')


if __name__ == '__main__':
    main()
