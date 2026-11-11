"""Per-opponent draft nudges on charybdis's draft18 model (chy-draft18's draft_model.h = replays/draftlab/draft18-start).

A nudge adds lam x direction to every champion's value. Directions (work/directions.json, from `dirs`):
  TF, TM   toward Fish's / Mite's own picks: the flat log-odds that the team holds the champion (this morning's Ff, Mf)
  RF, RM   what draft18's lab games say beats that body beyond the model: fit.py's residual on charybdis's games
           against the Fish / Mite body (our champion + our champion x 25 map features); lam 1 is the fitted size
  RB       the same residual fitted on the Fish and Mite games together: needs no knowledge of the opponent at the draft
  RP       ... on the Fish, Mite and ocean games together; RFo, RMo: RF - RP, RM - RP (not played)

    py nudge.py dirs                          build directions.json (fits RF, RM, RP)
    py nudge.py sweep FEAT.jsonl              per direction and lam: maps changed, swaps, pick rates
    py nudge.py levels FEAT.jsonl DIR:PCT..   the lam that changes PCT% of the maps -> stdout
    py nudge.py model SPEC OUTLAB             a link lab whose model.json carries the nudge (SPEC = DIR:lam)
"""
import json, sys, os, itertools, collections, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import load, fit as F
LAB = load.LAB; W = F.W; NC = 12; KC = 25; CH = F.CH
PAIRS = load.PAIRS
COMBOS = {p: np.array(list(itertools.combinations(range(NC), p))) for p in (3, 4, 5)}
IND = {p: np.array([[c in T for c in range(NC)] for T in COMBOS[p]], float) for p in (3, 4, 5)}
PIND = {p: np.array([[(i in T and j in T) for (i, j) in PAIRS] for T in COMBOS[p]], float) for p in (3, 4, 5)}
_m = None
def model():
    global _m
    if _m is None: _m = load.model()
    return _m
def load_maps(path):
    m = model(); seen = set(); out = []
    for l in open(path):
        r = json.loads(l)
        if r['picks'] not in (3, 4, 5) or r['key'] in seen: continue
        assert all(n in r['f'] for n in m['features'])
        seen.add(r['key']); r['z'] = load.zrow(m, r['f']); out.append(r)
    return out
def scores(Z, p, db=None, dW=None):
    b, Wt, syn, *_ = load.parts(model(), p); b = b.copy(); Wt = Wt.copy()
    if db is not None: b += db
    if dW is not None: Wt[:, :KC] += dW
    return (b[None, :] + Z @ Wt.T) @ IND[p].T + (PIND[p] @ syn)[None, :]
def direction(D, name):
    d = D[name]; return np.array(d['b']), (np.array(d['w']) if d.get('w') is not None else None)
def teams_for(maps, D, spec):
    out = {}
    for p in (3, 4, 5):
        mm = [m for m in maps if m['picks'] == p]
        if not mm: continue
        Z = np.array([m['z'] for m in mm])
        if spec == 'base': S = scores(Z, p)
        else:
            name, lam = spec.split(':'); db, dW = direction(D, name); lam = float(lam)
            S = scores(Z, p, lam * db, None if dW is None else lam * dW)
        for m, i in zip(mm, S.argmax(1)): out[m['key']] = tuple(int(c) for c in COMBOS[p][i])
    return out

def dirs(_):
    morning = json.load(open(os.path.expanduser('~/tmp-offload/draftnudge/work/directions.json')))
    D = {'TF': {'b': morning['Ff']['l'], 'w': None, 'note': "flat log-odds Fish holds the champion (draftnudge Ff)"},
         'TM': {'b': morning['Mf']['l'], 'w': None, 'note': "flat log-odds Mite holds the champion (draftnudge Mf)"}}
    G = np.load(f'{W}/games.npz'); Z = G['Z']; spec = {'u': 16, 'w': RIDGE}; F.KW = KC
    import cv2
    R = {n: F.rows(G, o) for n, o in F.BOT.items()}; X = {}
    for n in R: X[n], pen, _ = F.design(R[n], Z, spec)
    def fitted(ns):
        b = cv2.newton(np.vstack([X[n] for n in ns]), np.concatenate([R[n]['y'] for n in ns]), np.concatenate([R[n]['off'] for n in ns]), pen)
        u = b[1:1 + NC]; return {'b': (u - u.mean()).tolist(), 'w': b[1 + NC:].reshape(NC, KC).tolist(), 'games': int(sum(len(R[n]['y']) for n in ns))}
    D['RF'] = fitted(['fish']); D['RM'] = fitted(['mite']); D['RB'] = fitted(['fish', 'mite']); D['RP'] = fitted(['fish', 'mite', 'ocean'])
    for o in 'FM':
        D[f'R{o}o'] = {'b': (np.array(D[f'R{o}']['b']) - np.array(D['RP']['b'])).tolist(), 'w': (np.array(D[f'R{o}']['w']) - np.array(D['RP']['w'])).tolist()}
    json.dump(D, open(f'{W}/directions.json', 'w'))
    for n in ('RF', 'RM', 'RB', 'RP'):
        b = np.array(D[n]['b']); w = np.array(D[n]['w'])
        print(f'{n}: champion offsets ' + ' '.join(f'{CH[c][:5]} {b[c]:+.3f}' for c in np.argsort(-b)) + f'; map-weight rms per champion ' + ' '.join(f'{CH[c][:5]} {np.sqrt((w[c] ** 2).sum()):.3f}' for c in range(NC)))
    print('correlation of the map weights: RF-RM %.2f, RF-RB %.2f, RM-RB %.2f' % tuple(np.corrcoef(np.array(D[a]['w']).ravel(), np.array(D[b]['w']).ravel())[0, 1] for a, b in (('RF', 'RM'), ('RF', 'RB'), ('RM', 'RB'))))

def rate(tm):
    r = np.zeros(NC)
    for T in tm.values():
        for c in T: r[c] += 1
    return 100 * r / len(tm)
def sweep(args):
    maps = load_maps(args[0]); D = json.load(open(f'{W}/directions.json')); base = teams_for(maps, D, 'base')
    print(f'{len(maps)} maps; picks {dict(collections.Counter(m["picks"] for m in maps))}')
    print('base pick rates %: ' + ' '.join(f'{CH[c][:5]} {v:.0f}' for c, v in enumerate(rate(base))))
    for name in D:
        lams = ('0.003', '0.006', '0.012', '0.03', '0.06') if name[0] == 'T' else ('0.25', '0.5', '1', '2', '4')
        print(f'\n== {name} ==\n{"lam":>6s} {"changed%":>8s} {"3/4/5 picks":>12s} {"swaps/chg":>9s}   pick rates %')
        for lam in lams:
            tm = teams_for(maps, D, f'{name}:{lam}'); ch = [m for m in maps if tm[m['key']] != base[m['key']]]
            by = {p: np.mean([tm[m['key']] != base[m['key']] for m in maps if m['picks'] == p]) for p in (3, 4, 5)}
            sw = [len(set(tm[m['key']]) - set(base[m['key']])) for m in ch]
            print(f'{lam:>6s} {100 * len(ch) / len(maps):8.1f} {"/".join(f"{100 * by[p]:.0f}" for p in (3, 4, 5)):>12s} {np.mean(sw) if sw else 0:9.2f}   ' + ' '.join(f'{CH[c][:4]} {v:.0f}' for c, v in enumerate(rate(tm))))
def levels(args):
    maps = load_maps(args[0]); D = json.load(open(f'{W}/directions.json')); base = teams_for(maps, D, 'base')
    for a in args[1:]:
        name, target = a.split(':'); target = float(target); lo, hi = 0.0, 64.0
        for _ in range(40):
            mid = (lo + hi) / 2; tm = teams_for(maps, D, f'{name}:{mid!r}')
            if 100 * np.mean([tm[k] != base[k] for k in base]) < target: lo = mid
            else: hi = mid
        lam = float(f'{hi:.4g}'); tm = teams_for(maps, D, f'{name}:{lam!r}')
        print(f'{name}:{target:.0f} lam {lam} changes {100 * float(np.mean([tm[k] != base[k] for k in base])):.2f}%')
def model_cmd(args):
    spec, out = args; D = json.load(open(f'{W}/directions.json')); name, lam = spec.split(':'); lam = float(lam)
    m = json.load(open(f'{LAB}/model.json')); K = len(m['features']); L = m['layout']; db, dW = direction(D, name)
    for p in (3, 4, 5):
        th = m['picks'][str(p)]['theta']
        for c in range(NC):
            th[L['B'] + c] += lam * db[c]
            if dW is not None:
                for k in range(KC): th[L['W'] + c * K + k] += lam * dW[c][k]
    os.makedirs(out, exist_ok=True); json.dump(m, open(f'{out}/model.json', 'w'))
    for f in ('config.json', 'prior.json', 'maps.jsonl'):
        if not os.path.lexists(f'{out}/{f}'): os.symlink(os.path.realpath(f'{LAB}/{f}'), f'{out}/{f}')
    print('wrote', out)

RIDGE = 4096
if __name__ == '__main__':
    {'dirs': dirs, 'sweep': sweep, 'levels': levels, 'model': model_cmd}[sys.argv[1]](sys.argv[2:])
