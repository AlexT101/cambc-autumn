"""draft18's lab games as arrays, with the deployed model's logit for each: py load.py -> ~/tmp-offload/chynudge/work/games.npz

Columns: key index, picks, A and B as 12-bit champion masks, bot of A and B (0 self, 1 ocean, 2 fish, 3 mite), source of
A and B, win of A, eta (the model's logit that A wins, opponent terms included)."""
import json, math, os, sys, numpy as np
LAB = '/home/ubuntu/cambc-autumn/replays/draftlab/draft18-start'
OUT = os.path.expanduser('~/tmp-offload/chynudge/work')
NC = 12; PAIRS = [(i, j) for i in range(NC) for j in range(i + 1, NC)]
BOTS = ['self', 'ocean', 'fish', 'mite']; SRC = ['explore', 'ladder', 'current', 'thompson', 'probe']

def model():
    m = json.load(open(f'{LAB}/model.json')); m['K'] = len(m['features'])
    m['th'] = {int(p): np.array(v['theta']) for p, v in m['picks'].items()}
    for v in m['picks'].values(): v.pop('chol', None)
    return m
def zrow(m, f):
    out = np.zeros(m['K'])
    for k, (name, tf) in enumerate(zip(m['features'], m['transforms'])):
        v = f.get(name)
        if isinstance(v, bool): v = float(v)
        if v is None or not isinstance(v, (int, float)) or not math.isfinite(v): continue
        v = math.log(max(v, 1)) if tf == 'log' else math.log1p(max(v, 0)) if tf == 'log1p' else v
        z = (v - m['mean'][k]) / m['sd'][k]
        out[k] = max(-4.0, min(4.0, z)) if math.isfinite(z) else 0.0
    return out
def parts(m, p):
    L = m['layout']; th = m['th'][p]; K = m['K']
    return (th[L['B']:L['B'] + NC], th[L['W']:L['SYN']].reshape(NC, K), th[L['SYN']:L['CTR']], th[L['SIDE']],
            th[L['OPP']:L['DEV']], th[L['DEV']:L['P']].reshape(-1, NC))
def bits(mask): return np.array([[(x >> c) & 1 for c in range(NC)] for x in mask], float) if False else ((mask[:, None] >> np.arange(NC)) & 1).astype(float)
def pairs(I): return np.stack([I[:, i] * I[:, j] for i, j in PAIRS], 1)

if __name__ == '__main__':
    m = model(); names = m['champions']; cid = {n: i for i, n in enumerate(names)}
    assert m['opponents'] == BOTS[1:], m['opponents']
    keys = {}; Z = []
    for l in open(f'{LAB}/maps.jsonl'):
        r = json.loads(l)
        if r['picks'] not in (3, 4, 5) or r['key'] in keys: continue
        missing = [n for n in m['features'] if n not in r['f']]
        assert not missing, missing[:3]
        keys[r['key']] = len(Z); Z.append(zrow(m, r['f']))
    Z = np.array(Z); print(len(Z), 'maps', flush=True)
    cols = {k: [] for k in ('key', 'picks', 'A', 'B', 'botA', 'botB', 'srcA', 'srcB', 'win')}; skipped = 0
    for l in open(f'{LAB}/games.slim.jsonl'):
        g = json.loads(l)
        if g.get('error') or g.get('winner') is None or g.get('draft_ok') is False or g['key'] not in keys: skipped += 1; continue
        cols['key'].append(keys[g['key']]); cols['picks'].append(g['picks'])
        cols['A'].append(sum(1 << cid[c] for c in g['A'])); cols['B'].append(sum(1 << cid[c] for c in g['B']))
        cols['botA'].append(BOTS.index(g.get('botA', 'self'))); cols['botB'].append(BOTS.index(g.get('botB', 'self')))
        cols['srcA'].append(SRC.index(g['srcA'])); cols['srcB'].append(SRC.index(g['srcB'])); cols['win'].append(int(g['winner'] == 0))
    G = {k: np.array(v) for k, v in cols.items()}; n = len(G['win']); print(n, 'games,', skipped, 'skipped', flush=True)
    eta = np.zeros(n)
    for p in (3, 4, 5):
        b, W, syn, side, opp, dev = parts(m, p); s = np.flatnonzero(G['picks'] == p)
        V = b[None, :] + Z @ W.T; IA, IB = bits(G['A'][s]), bits(G['B'][s]); Vm = V[G['key'][s]]
        e = ((IA - IB) * Vm).sum(1) + (pairs(IA) - pairs(IB)) @ syn + side
        for I, bot, sg in ((IA, G['botA'][s], 1), (IB, G['botB'][s], -1)):
            o = bot - 1; on = o >= 0
            e[on] += sg * (opp[o[on]] + (I[on] * dev[o[on]]).sum(1))
        eta[s] = e
    pr = 1 / (1 + np.exp(-eta)); ll = -(G['win'] * np.log(pr) + (1 - G['win']) * np.log(1 - pr)).mean()
    print(f'model log loss on its own games {ll:.5f}; mean predicted {pr.mean():.4f}, observed {G["win"].mean():.4f}')
    np.savez(f'{OUT}/games.npz', Z=Z, eta=eta, keys=np.array(list(keys)), **G)
