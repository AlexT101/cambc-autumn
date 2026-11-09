"""Accuracy by round on held-out (newest) games, plus leave-one-team-out for the 'other' class.

usage: evaluate.py SPLIT_ISO [--tau T] [--eps E] [--no-draft] [--observer]
"""
import pickle, sys, collections
import numpy as np
from model import Model, cls_of, CLASSES, US

ROUNDS = [1, 10, 25, 50, 75, 100, 150, 200, 300, 500, 1000]

def load():
    seen = set(); rows = []
    for f in ('ds_others.pkl', 'ds_fish.pkl', 'ds_mite.pkl'):
        try: rs = pickle.load(open(f, 'rb'))
        except FileNotFoundError: continue
        for s in rs:
            k = (s['mid'], s['side'])
            if k in seen or s['team'] == US: continue
            if s['created'] < '2026-11-08': continue
            seen.add(k); rows.append(s)
    return rows

def report(model, test, observer=False, use_draft=True, label='', remap=None, cls_remap=None):
    acc = collections.defaultdict(lambda: np.zeros((3, 3)))  # round -> [true, pred]
    ll = collections.defaultdict(list)
    conf = collections.defaultdict(lambda: np.zeros(3))
    sure = collections.defaultdict(lambda: np.zeros(3))
    for s in test:
        c = cls_of(s['team'])
        obs = [None] if not observer else [o for o in range(len(s['opp_roster']))]
        for o in obs:
            tr = model.trajectory(s, ROUNDS, o, use_draft, remap if (cls_remap is None or cls_remap == c) else None)
            for R, p in zip(ROUNDS, tr):
                if R > s['rounds']: continue
                acc[R][c, int(np.argmax(p))] += 1
                conf[R][c] += max(p[k] for k in range(3) if k != c) > 0.9
                sure[R][c] += p[c] > 0.8
                ll[R].append(-np.log(max(p[c], 1e-9)))
    print(f'== {label}')
    print('round  n     acc    fish-recall mite-recall other-recall  fish-prec mite-prec  logloss  wrong>0.9: fish mite other   right>0.8: fish mite other')
    for R in ROUNDS:
        m = acc[R]; n = m.sum()
        rec = [m[i, i] / max(1, m[i].sum()) for i in range(3)]
        prec = [m[i, i] / max(1, m[:, i].sum()) for i in range(2)]
        print(f'{R:5d} {int(n):5d} {np.trace(m)/n:.4f}   {rec[0]:.3f}       {rec[1]:.3f}       {rec[2]:.3f}        {prec[0]:.3f}     {prec[1]:.3f}    {np.mean(ll[R]):.3f}    {conf[R][0]/max(1,m[0].sum()):.3f} {conf[R][1]/max(1,m[1].sum()):.3f} {conf[R][2]/max(1,m[2].sum()):.3f}    {sure[R][0]/max(1,m[0].sum()):.3f} {sure[R][1]/max(1,m[1].sum()):.3f} {sure[R][2]/max(1,m[2].sum()):.3f}')
    return acc

def main():
    split = sys.argv[1]
    kw = {}
    for k in ('tau', 'eps', 'draft_cap'):
        if f'--{k}' in sys.argv: kw[k] = float(sys.argv[sys.argv.index(f'--{k}') + 1])
    use_draft = '--no-draft' not in sys.argv
    if '--subs' in sys.argv:
        from model import SUB_SETS
        kw['subs'] = SUB_SETS[sys.argv[sys.argv.index('--subs') + 1]]
    rows = load()
    train = [s for s in rows if s['created'] < split]
    test = [s for s in rows if s['created'] >= split]
    cnt = lambda rs: collections.Counter(CLASSES[cls_of(s['team'])] for s in rs)
    print('train', dict(cnt(train)), 'test', dict(cnt(test)))
    m = Model(**kw).fit(train)
    np.set_printoptions(precision=3, suppress=True)
    from tokens import TOK
    print('tokens', TOK); print(np.exp(m.logP))
    from tokens import T
    if '--ablate' in sys.argv:
        K = len(TOK); idm = list(range(K))
        def mk(d):
            r = idm[:]
            for a, b in d.items(): r[T[a]] = T[b]
            return r
        fishL = {'fish_level': False}
        fishR = {'fish_rank': False}
        fishX = mk({'fish_quiet': 'other', 'fish_contact': 'other', 'fish_mod': 'other'})
        miteQ = {'mite_quiet': False}
        miteV = mk({k: 'other' for k in TOK if k.startswith('mite')})
        cfg = sys.argv[sys.argv.index('--ablate') + 1]
        if cfg == 'fishL': report(m, test, observer=True, label='ablation: Fish changes its level encoding', remap=fishL, cls_remap=0)
        if cfg == 'fishR': report(m, test, observer=True, label='ablation: Fish changes its rank order', remap=fishR, cls_remap=0)
        if cfg == 'fishX': report(m, test, observer=True, label='ablation: Fish changes everything (fish tokens read as other)', remap=fishX, cls_remap=0)
        if cfg == 'miteQ': report(m, test, observer=True, label='ablation: Mite drops its quiet/channel constants', remap=miteQ, cls_remap=1)
        if cfg == 'miteV': report(m, test, observer=True, label='ablation: Mite changes every encoding (mite tokens read as other)', remap=miteV, cls_remap=1)
        if cfg == 'nodraft': report(m, test, observer=True, use_draft=False, label='no draft, per instance')
        return
    report(m, test, use_draft=use_draft, label='time split, team view')
    report(m, test, observer=True, use_draft=use_draft, label='time split, per champion instance')
    # leave one other team out: fit without it (all times), test on its newest sides
    print('== leave-one-team-out (other teams), per instance, misclassified share by round')
    teams = collections.Counter(s['team'] for s in rows if cls_of(s['team']) == 2)
    for t, n in teams.most_common():
        if n < 30: continue
        mt = Model(**kw).fit([s for s in train if s['team'] != t])
        ts = [s for s in rows if s['team'] == t]
        bad = collections.defaultdict(lambda: [0, 0])
        for s in ts:
            for o in range(len(s['opp_roster'])):
                for R, p in zip(ROUNDS, mt.trajectory(s, ROUNDS, o, use_draft)):
                    if R > s['rounds']: continue
                    bad[R][0] += int(np.argmax(p)) != 2; bad[R][1] += 1
                    bad[R].append(int(p[0] > 0.9 or p[1] > 0.9))
        print(f'{t[:24]:24s} n={n:4d} ' + ' '.join(f'r{R}:{b[0]/max(1,b[1]):.3f}' for R, b in sorted(bad.items()) if R in (25, 100, 300, 1000))
              + '  fish|mite>0.9 at r25/100/300: ' + ' '.join(f'{sum(bad[R][2:])/max(1,bad[R][1]):.3f}' for R in (25, 100, 300)))

if __name__ == '__main__':
    main()
