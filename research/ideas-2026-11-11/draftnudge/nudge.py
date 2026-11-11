"""Fish/Mite draft nudges on ocean's draft10 F92 model.

A nudge adds lam * l_c(map) to every champion's value, where l_c is the log-odds that the team (Fish or Mite) holds
champion c: 'flat' = one number per champion over all maps and pick counts; 'cond' = a ridge logistic on the pick
count and the model's first 25 map features. lam = 0 is ocean's draft; lam -> inf drafts their likeliest team.

    py nudge.py fit WORK                      fit the four directions -> WORK/directions.json (+ CV report)
    py nudge.py sweep WORK FEAT.jsonl         per direction and lam: maps changed, model-predicted cost, pick rates
    py nudge.py levels WORK FEAT.jsonl 15 30 50   the lam per direction that changes that % of maps -> WORK/levels.json
    py nudge.py teams WORK FEAT.jsonl SPEC..  SPEC = dir:lam (e.g. Fc:0.02, base); writes WORK/teams-<spec>.txt
    py nudge.py model WORK SPEC OUTLAB        a lab dir whose model.json carries the nudge (for model.mjs cpp / teams)
"""
import json, sys, os, itertools, collections, math, numpy as np
LAB = '/home/ubuntu/cambc-autumn/replays/draftlab/draft10-f92'
LADDER_FEAT = '/home/ubuntu/tmp-offload/diverse/fresh/feat-ladder.jsonl'
CH = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi & Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'Heart of Ruin']
enum = lambda n: n.lower().replace(' & ', '_and_').replace(' ', '_')
EN = [enum(c) for c in CH]; NC = 12; KC = 25  # KC: the base features the conditional direction may use
TEAMS = {'F': 'Intercontinental Fish', 'M': 'Mite'}; WINDOW = '2026-11-09'
PAIRS = [(i, j) for i in range(NC) for j in range(i + 1, NC)]

_model = None
def model():
    global _model
    if _model is None:
        m = json.load(open(f'{LAB}/model.json')); K = len(m['features'])
        m['K'] = K; m['th'] = {int(p): np.array(v['theta']) for p, v in m['picks'].items()}
        _model = m
    return _model
def derived(f, name):  # derived.mjs, for rows that predate a feature: every row here carries all 92
    raise KeyError(name)
def zrow(f):
    m = model(); out = np.zeros(m['K'])
    for k, (name, tf) in enumerate(zip(m['features'], m['transforms'])):
        v = f.get(name)
        if isinstance(v, bool): v = float(v)
        if v is None or not isinstance(v, (int, float)) or not math.isfinite(v): continue
        v = math.log(max(v, 1)) if tf == 'log' else math.log1p(max(v, 0)) if tf == 'log1p' else v
        z = (v - m['mean'][k]) / m['sd'][k]
        out[k] = max(-4.0, min(4.0, z)) if math.isfinite(z) else 0.0
    return out
def load_maps(path):
    rows = [json.loads(l) for l in open(path)]; seen = set(); out = []
    for r in rows:
        if r['picks'] not in (3, 4, 5) or r['key'] in seen: continue
        seen.add(r['key']); r['z'] = zrow(r['f']); out.append(r)
    return out
COMBOS = {p: np.array(list(itertools.combinations(range(NC), p))) for p in (3, 4, 5)}
IND = {p: np.array([[c in T for c in range(NC)] for T in COMBOS[p]], float) for p in (3, 4, 5)}
PIND = {p: np.array([[(i in T and j in T) for (i, j) in PAIRS] for T in COMBOS[p]], float) for p in (3, 4, 5)}
def parts(p):
    m = model(); th = m['th'][p]; K = m['K']
    return th[:NC].copy(), th[NC:NC + NC * K].reshape(NC, K).copy(), th[NC + NC * K:NC + NC * K + len(PAIRS)].copy()
def scores(Z, p, db=None, dW=None):
    """Team scores (maps x combos) for pick count p under the model plus per-champion additions db (12) and dW (12 x KC)."""
    b, W, syn = parts(p)
    if db is not None: b = b + db
    if dW is not None: W[:, :KC] += dW
    V = b[None, :] + Z @ W.T
    return V @ IND[p].T + (PIND[p] @ syn)[None, :]

def direction(D, name, p):
    """(db, dW) of direction name at lam = 1 for pick count p."""
    d = D[name]
    if d['kind'] == 'flat': return np.array(d['l']), None
    return np.array(d['a'][str(p)]), np.array(d['s'])
def teams_for(maps, D, spec):
    """{key: tuple of champion ids} for spec 'base', 'Ff:0.02' or 'Ff:inf'."""
    out = {}
    for p in (3, 4, 5):
        mm = [m for m in maps if m['picks'] == p]
        if not mm: continue
        Z = np.array([m['z'] for m in mm])
        if spec == 'base': S = scores(Z, p)
        else:
            name, lam = spec.split(':'); db, dW = direction(D, name, p)
            if lam == 'inf':
                V = np.repeat(db[None, :], len(Z), 0) + (Z[:, :KC] @ dW.T if dW is not None else 0); S = V @ IND[p].T
            else: S = scores(Z, p, float(lam) * db, None if dW is None else float(lam) * dW)
        for m, i in zip(mm, S.argmax(1)): out[m['key']] = tuple(int(c) for c in COMBOS[p][i])
    return out

def ladder_cells(team):
    rows = json.load(open(f'{W}/ladder-top.json')); c = collections.defaultdict(list)
    for r in rows:
        if r['team'] == team and r['day'] >= WINDOW: c[(r['map'], r['side'])].append([CH.index(x) for x in r['picks']])
    return c
def logistic(X, y, w, pen, iters=60):
    """Weighted logistic regression, penalty 0.5 * sum(pen * beta^2), by Newton."""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        e = X @ b; pr = 1 / (1 + np.exp(-e)); g = X.T @ (w * (pr - y)) + pen * b
        H = (X * (w * pr * (1 - pr))[:, None]).T @ X + np.diag(pen)
        step = np.linalg.solve(H, g); b -= step
        if np.abs(step).max() < 1e-10: break
    return b
def fit(_):
    lf = {x['name'].replace('-', '_'): x for x in map(json.loads, open(LADDER_FEAT))}  # archive names use '_'
    D = {}; rep = []
    for t, team in TEAMS.items():
        cells = ladder_cells(team); keys = sorted(k for k in cells if k[0] in lf)
        assert len(keys) == len(cells), 'a ladder map without features'
        # one row per (cell, distinct comp), weight = that comp's share of the cell: every map/side cell weighs 1
        R = []
        for k in keys:
            cnt = collections.Counter(tuple(sorted(x)) for x in cells[k])
            for comp, n in cnt.items(): R.append((k[0], comp, n / len(cells[k])))
        n = len(keys); inc = np.zeros(NC)
        for _, comp, w in R:
            for c in comp: inc[c] += w
        flat = np.log((inc + 0.5) / (n - inc + 0.5))  # Jeffreys
        D[t + 'f'] = {'kind': 'flat', 'team': team, 'cells': n, 'rate': list(inc / n), 'l': list(flat)}
        # conditional: per champion, pick-count intercepts (Jeffreys pseudo-cells keep them finite) + ridge slopes on 25 features
        Z = np.array([zrow(lf[m]['f'])[:KC] for m, _, _ in R]); P = np.array([len(comp) for _, comp, _ in R])
        Xd = np.array([[float(len(comp) == p) for p in (3, 4, 5)] for _, comp, _ in R]); X = np.hstack([Xd, Z])
        Y = np.array([[float(c in comp) for c in range(NC)] for _, comp, _ in R]); w = np.array([x for *_, x in R])
        pseudoX = np.vstack([np.hstack([np.eye(3)[i], np.zeros(KC)]) for i in range(3) for _ in (0, 1)])
        pseudoY = np.array([0.0, 1.0] * 3); pseudoW = np.full(6, 0.5)
        def fit_all(rows, ridge):
            B = np.zeros((NC, 3 + KC)); pen = np.array([1e-6] * 3 + [ridge] * KC)
            for c in range(NC):
                B[c] = logistic(np.vstack([X[rows], pseudoX]), np.concatenate([Y[rows, c], pseudoY]), np.concatenate([w[rows], pseudoW]), pen)
            return B
        mapsU = sorted({m for m, _, _ in R}); fold = {m: i % 5 for i, m in enumerate(sorted(mapsU, key=lambda m: hash_(m)))}
        F = np.array([fold[m] for m, _, _ in R]); best = None
        for ridge in (1, 4, 16, 64, 256, 1e9):
            ll = 0.0; hit = 0.0
            for f in range(5):
                tr, te = np.flatnonzero(F != f), np.flatnonzero(F == f); B = fit_all(tr, ridge)
                pr = 1 / (1 + np.exp(-(X[te] @ B.T))); pr = np.clip(pr, 1e-9, 1 - 1e-9)
                ll += -(w[te, None] * (Y[te] * np.log(pr) + (1 - Y[te]) * np.log(1 - pr))).sum()
                # champion overlap of the likeliest team under the fit with the observed comp
                for i in te:
                    top = np.argsort(-(X[i] @ B.T))[:P[i]]; hit += w[i] * Y[i, top].sum() / P[i]
            rep.append((t, ridge, ll / w.sum(), hit / w.sum()))
            if best is None or ll < best[0] - 1e-9: best = (ll, ridge)
        ridge = best[1]; B = fit_all(np.arange(len(R)), ridge)
        D[t + 'c'] = {'kind': 'cond', 'team': team, 'cells': n, 'ridge': ridge, 'a': {str(p): list(B[:, i]) for i, p in enumerate((3, 4, 5))}, 's': B[:, 3:].tolist()}
    json.dump(D, open(f'{W}/directions.json', 'w'))
    print('held-out (5 map folds) per direction: ridge, log-loss per cell (12 champions), champion overlap of the likeliest team')
    for t, ridge, ll, hit in rep: print(f'  {TEAMS[t][:5]:5s} ridge {ridge:<6g} loss {ll:.3f} overlap {hit:.3f}' + ('  <- chosen' if D[t + "c"]['ridge'] == ridge else ''))
    for t in TEAMS:
        print(f'\n{TEAMS[t]} flat log-odds: ' + ', '.join(f'{EN[c]} {D[t + "f"]["l"][c]:+.2f}' for c in np.argsort(-np.array(D[t + 'f']['l']))))
def hash_(s):
    h = 2166136261
    for ch in s.encode(): h = ((h ^ ch) * 16777619) & 0xffffffff
    return h

def sweep(args):
    maps = load_maps(args[0]); D = json.load(open(f'{W}/directions.json')); base = teams_for(maps, D, 'base')
    Zp = {p: np.array([m['z'] for m in maps if m['picks'] == p]) for p in (3, 4, 5)}
    bs = {}
    for p in (3, 4, 5):
        S = scores(Zp[p], p)
        for m, row in zip([m for m in maps if m['picks'] == p], S): bs[m['key']] = row
    idx = {p: {tuple(T): i for i, T in enumerate(COMBOS[p].tolist())} for p in (3, 4, 5)}
    def rate(tm):
        r = np.zeros(NC)
        for T in tm.values():
            for c in T: r[c] += 1
        return 100 * r / len(tm)
    print(f'{len(maps)} maps; pick counts {dict(collections.Counter(m["picks"] for m in maps))}')
    print('base pick rates %: ' + ' '.join(f'{EN[c][:6]} {v:.0f}' for c, v in enumerate(rate(base))))
    for name in D:
        print(f'\n== {name} ({D[name]["team"]}, {D[name]["kind"]}) ==')
        print(f'{"lam":>7s} {"changed%":>8s} {"3/4/5 picks":>14s} {"swaps/chg":>9s} {"model cost/chg (logit)":>22s} {"model cost overall (pts)":>24s}   pick rates %')
        for lam in ('0.002', '0.005', '0.01', '0.02', '0.03', '0.05', '0.08', '0.12', '0.2', '0.4', '1', 'inf'):
            tm = teams_for(maps, D, f'{name}:{lam}'); ch = [m for m in maps if tm[m['key']] != base[m['key']]]
            by = {p: np.mean([tm[m['key']] != base[m['key']] for m in maps if m['picks'] == p]) for p in (3, 4, 5)}
            cost = [bs[m['key']][idx[m['picks']][base[m['key']]]] - bs[m['key']][idx[m['picks']][tm[m['key']]]] for m in ch]
            sw = [len(set(tm[m['key']]) - set(base[m['key']])) for m in ch]
            # points: a logit difference d against an even opponent is about 25 * d points
            print(f'{lam:>7s} {100 * len(ch) / len(maps):8.1f} {"/".join(f"{100 * by[p]:.0f}" for p in (3, 4, 5)):>14s} {np.mean(sw) if sw else 0:9.2f} {np.mean(cost) if cost else 0:22.4f} '
                  f'{25 * np.sum(cost) / len(maps):24.2f}   ' + ' '.join(f'{EN[c][:4]} {v:.0f}' for c, v in enumerate(rate(tm))))

def levels(args):
    """For each direction, the lam that changes TARGET% of the maps' teams (bisection; changed% rises with lam)."""
    maps = load_maps(args[0]); D = json.load(open(f'{W}/directions.json')); base = teams_for(maps, D, 'base'); out = {}
    for name in D:
        for target in map(float, args[1:]):
            lo, hi = 0.0, 1.0
            for _ in range(30):
                mid = (lo + hi) / 2; tm = teams_for(maps, D, f'{name}:{mid!r}')
                if 100 * np.mean([tm[k] != base[k] for k in base]) < target: lo = mid
                else: hi = mid
            lam = float(f'{hi:.4g}'); tm = teams_for(maps, D, f'{name}:{lam!r}')
            out[f'{name}{target:.0f}'] = {'dir': name, 'lam': lam, 'changed': round(100 * float(np.mean([tm[k] != base[k] for k in base])), 2)}
            print(f'{name}{target:.0f}: lam {lam} changes {out[f"{name}{target:.0f}"]["changed"]}%')
    json.dump(out, open(f'{W}/levels.json', 'w'), indent=1)

def teams_cmd(args):
    maps = load_maps(args[0]); D = json.load(open(f'{W}/directions.json'))
    for spec in args[1:]:
        tm = teams_for(maps, D, spec)
        with open(f'{W}/teams-{spec.replace(":", "-")}.txt', 'w') as fh:
            for m in maps: fh.write(f'{m["key"]} {m["picks"]} {m["name"]} {",".join(EN[c] for c in tm[m["key"]])}\n')

def model_cmd(args):
    spec, out = args; D = json.load(open(f'{W}/directions.json')); name, lam = spec.split(':'); lam = float(lam)
    m = json.load(open(f'{LAB}/model.json')); K = len(m['features'])
    for p in (3, 4, 5):
        th = m['picks'][str(p)]['theta']; db, dW = direction(D, name, p)
        for c in range(NC):
            th[c] += lam * db[c]
            if dW is not None:
                for k in range(KC): th[NC + c * K + k] += lam * dW[c][k]
    os.makedirs(out, exist_ok=True)
    json.dump(m, open(f'{out}/model.json', 'w'))
    for f in ('config.json', 'prior.json', 'maps.jsonl'):
        if not os.path.lexists(f'{out}/{f}'): os.symlink(os.path.realpath(f'{LAB}/{f}'), f'{out}/{f}')
    print('wrote', out)

if __name__ == '__main__':
    cmd, W = sys.argv[1], sys.argv[2]
    {'fit': fit, 'sweep': sweep, 'levels': levels, 'teams': teams_cmd, 'model': model_cmd}[cmd](sys.argv[3:])
