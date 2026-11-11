"""Live scrims as a draft experiment. Our draft changed three times (v80->81, v82->83, v114->115); on every other
version step the team in each (map, side) cell is unchanged. Cells whose team changed at a step are the treatment,
cells whose team did not are the control for the play changes shipped in the same step.
    py cells.py            (prints every table; no arguments)"""
import json, collections, sys, numpy as np
ROOT = '/home/ubuntu/cambc-autumn/research/ladder-scrims-2026-11-06/data/games.jsonl'
CH = ['Cassi & Issac', 'Prism', 'Willow', 'Vesper Vale', 'Heart of Ruin', 'Vendetta', 'Marcella', 'Ryth', 'Ren', 'Varg', 'Tavi', 'Stellar']
ERA = lambda v: 0 if v <= 80 else 1 if v <= 82 else 2 if v <= 114 else 3
rng = np.random.default_rng(1)

def load():
    seen, out = set(), []
    for l in open(ROOT):
        g = json.loads(l)
        if g.get('status') != 'finished' or not g.get('our_picks') or g.get('result') not in ('win', 'loss') or g.get('filler'): continue
        k = (g['version'], g['opp_name'], g['refset'], g['map'], g['side'])
        if k in seen: continue
        seen.add(k); g['team'] = tuple(sorted(g['our_picks'])); g['oteam'] = tuple(sorted(g['opp_picks'])); g['w'] = float(g['result'] == 'win'); out.append(g)
    return out

def boot(maps, f, n=2000):
    """95% interval of f(index array) resampling maps (both sides of a map move together)."""
    um = sorted(set(maps)); idx = {m: np.flatnonzero(maps == m) for m in um}; r = []
    for _ in range(n):
        s = np.concatenate([idx[um[j]] for j in rng.integers(0, len(um), len(um))])
        try: r.append(f(s))
        except Exception: pass
    r = np.array(r); return np.nanpercentile(r, 2.5, axis=0), np.nanpercentile(r, 97.5, axis=0)

def cellsof(G, opp, refs, vers):
    """(map, side) -> list of games of these versions against this opponent pin."""
    c = collections.defaultdict(list)
    for g in G:
        if g['opp_name'].startswith(opp) and g['refset'] in refs and g['version'] in vers: c[(g['map'], g['side'])].append(g)
    return c

def step(G, opp, refs_old, old, refs_new, new, label):
    """One draft step: per cell, old-draft win share over `old` versions and new-draft win share over `new`."""
    O, N = cellsof(G, opp, refs_old, old), cellsof(G, opp, refs_new, new)
    rows = []
    for k in sorted(set(O) & set(N)):
        to, tn = {g['team'] for g in O[k]}, {g['team'] for g in N[k]}
        if len(to) != 1 or len(tn) != 1: continue
        oo, on = {g['oteam'] for g in O[k]}, {g['oteam'] for g in N[k]}
        to, tn = to.pop(), tn.pop()
        rows.append(dict(map=k[0], side=k[1], old=to, new=tn, changed=to != tn, oppsame=oo == on and len(oo) == 1,
                         po=np.mean([g['w'] for g in O[k]]), pn=np.mean([g['w'] for g in N[k]]), no=len(O[k]), nn=len(N[k]),
                         oteam=sorted(on)[0], label=label, opp=opp,
                         ko=np.mean([g.get('opp_kills') or 0 for g in O[k]]), kn=np.mean([g.get('opp_kills') or 0 for g in N[k]])))
    return rows

def did(rows, name):
    m = np.array([r['map'] for r in rows]); ch = np.array([r['changed'] for r in rows]); d = np.array([r['pn'] - r['po'] for r in rows])
    f = lambda s: d[s][ch[s]].mean() - d[s][~ch[s]].mean()
    lo, hi = boot(m, f); l1, h1 = boot(m, lambda s: d[s][ch[s]].mean()); l0, h0 = boot(m, lambda s: d[s][~ch[s]].mean())
    po, pn = np.array([r['po'] for r in rows]), np.array([r['pn'] for r in rows])
    print(f'| {name} | {ch.sum()} | {100 * po[ch].mean():.1f} -> {100 * pn[ch].mean():.1f} ({100 * d[ch].mean():+.1f}, {100 * l1:+.1f} to {100 * h1:+.1f}) '
          f'| {(~ch).sum()} | {100 * po[~ch].mean():.1f} -> {100 * pn[~ch].mean():.1f} ({100 * d[~ch].mean():+.1f}, {100 * l0:+.1f} to {100 * h0:+.1f}) '
          f'| {100 * f(np.arange(len(d))):+.1f} ({100 * lo:+.1f} to {100 * hi:+.1f}) |')
    return f(np.arange(len(d))), (lo, hi)

def swaps(rows, name, pr=True):
    """d = a + sum_c beta_c * (c in new - c in old); the deltas sum to 0 in a cell, so beta is centred to mean 0."""
    m = np.array([r['map'] for r in rows]); d = np.array([r['pn'] - r['po'] for r in rows])
    X = np.array([[float(c in r['new']) - float(c in r['old']) for c in CH] for r in rows])
    lab = sorted({r['label'] for r in rows}); I = np.array([[float(r['label'] == l) for l in lab] for r in rows])
    use = [j for j in range(len(CH)) if np.abs(X[:, j]).sum() >= 12]
    def fit(s):
        A = np.column_stack([I[s], X[s][:, use]]); b = np.linalg.lstsq(A, d[s], rcond=None)[0][len(lab):]
        return b - b.mean()
    b = fit(np.arange(len(d))); lo, hi = boot(m, fit, 1000)
    if pr:
        print(f'| {name} | ' + ' | '.join(f'{100 * b[i]:+.0f} ({100 * lo[i]:+.0f} to {100 * hi[i]:+.0f}); {int((X[:, j] > 0).sum())} in, {int((X[:, j] < 0).sum())} out'
                                             for i, j in enumerate(use)) + ' |')
    return [CH[j] for j in use], b, lo, hi

if __name__ == '__main__':
    G = load()
    D2 = set(range(83, 115)); F = 'Inte'; M = 'Mite'
    S = {
        'Fish 502 (v83-114 -> v115)': step(G, F, {'r1', 'r2'}, D2, {'r2'}, {115}, 'F3'),
        'Fish 502, old = v105-114 only': step(G, F, {'r2'}, set(range(105, 115)), {'r2'}, {115}, 'F3'),
        'Fish 502, old = v113 only': step(G, F, {'r2'}, {113}, {'r2'}, {115}, 'F3'),
        'Mite r6 502 (v113 -> v115)': step(G, M, {'r6'}, {113}, {'r6'}, {115}, 'M3'),
        'Fish v82 -> v83-86 (r1)': step(G, F, {'r1'}, {81, 82}, {'r1'}, {83, 84, 85, 86}, 'F2'),
        'Mite v82 -> v83-86 (r1)': step(G, M, {'r1'}, {81, 82}, {'r1'}, {83, 84, 85, 86}, 'M2'),
        'Fish v80 -> v81-82 (r1)': step(G, F, {'r1'}, {78, 80}, {'r1'}, {81, 82}, 'F1'),
        'Mite v80 -> v81-82 (r1)': step(G, M, {'r1'}, {78, 80}, {'r1'}, {81, 82}, 'M1'),
    }
    # the nine other teams of the 113/115 panel: the same draft step, opponents that are not Fish or Mite
    P = []
    for g in G:
        if (g['refset'] or '').startswith('cmp113-506'): g['opp_name'] = 'PANEL' + g['refset'][-6:] + g['opp_name']
    for ref in sorted({g['refset'] for g in G if (g['refset'] or '').startswith('cmp113-506')}):
        P += step([g for g in G if g['refset'] == ref], 'PANEL', {ref}, {113}, {ref}, {115}, 'P3')
    S['Other nine teams 502 (v113 -> v115)'] = P
    print('## A. Draft steps: changed cells against unchanged cells (win% old -> new; difference of differences)\n')
    print('| step | cells changed | their win% | cells unchanged | their win% | draft effect on a changed cell |\n|---|---:|---|---:|---|---|')
    for k, r in S.items(): did(r, k)
    # Mite with a longer old record: any D2 version on a pin where Mite's team in the cell equals r6's
    mr = []
    N = cellsof(G, M, {'r6'}, {115})
    Oall = collections.defaultdict(list)
    for g in G:
        if g['opp_name'].startswith(M) and g['version'] in D2 and g['refset'] in ('r3', 'r5', 'r6', 'r4'): Oall[(g['map'], g['side'])].append(g)
    for k in sorted(N):
        n = N[k][0]; o = [g for g in Oall[k] if g['oteam'] == n['oteam']]
        if not o: continue
        mr.append(dict(map=k[0], side=k[1], old=o[0]['team'], new=n['team'], changed=o[0]['team'] != n['team'], po=np.mean([g['w'] for g in o]), pn=n['w'], no=len(o), nn=1, label='M3', opp=M, oteam=n['oteam']))
    did(mr, 'Mite 502, old = v97-114 on any pin with the same Mite team')
    S['Mite 502 long'] = mr

    print('\n## B. Champion swaps inside the changed cells (win points for holding the champion, centred; 95% over maps; cells in / out)\n')
    for nm, keys in (('Fish, 502 step', ['Fish 502 (v83-114 -> v115)']), ('Mite, 502 step (long old record)', ['Mite 502 long']),
                     ('Other nine, 502 step', ['Other nine teams 502 (v113 -> v115)']),
                     ('Fish, all three steps', ['Fish 502 (v83-114 -> v115)', 'Fish v82 -> v83-86 (r1)', 'Fish v80 -> v81-82 (r1)']),
                     ('Mite, all three steps', ['Mite 502 long', 'Mite v82 -> v83-86 (r1)', 'Mite v80 -> v81-82 (r1)'])):
        rows = [r for k in keys for r in S[k]]
        names, b, lo, hi = swaps(rows, nm, pr=False)
        print(f'**{nm}** ({sum(r["changed"] for r in rows)} changed cells)')
        for i, c in sorted(enumerate(names), key=lambda t: -b[t[0]]):
            X = [(c in r['new']) - (c in r['old']) for r in rows]
            print(f'  {c:14s} {100 * b[i]:+6.1f} ({100 * lo[i]:+6.1f} to {100 * hi[i]:+6.1f})   in {X.count(1):3d} out {X.count(-1):3d}')
    # Fish minus Mite on the same cells: the opponent-specific part
    print('\n**Fish minus Mite, 502 step, same cells** (the play step and the map cancel)')
    fr = {(r['map'], r['side']): r for r in S['Fish 502 (v83-114 -> v115)']}; rows = []
    for r in S['Mite 502 long']:
        f = fr.get((r['map'], r['side']))
        if f and f['old'] == r['old'] and f['new'] == r['new']:
            rows.append(dict(r, po=f['po'] - r['po'], pn=f['pn'] - r['pn']))
    did(rows, 'Fish - Mite, 502')
    names, b, lo, hi = swaps(rows, 'x', pr=False)
    for i, c in sorted(enumerate(names), key=lambda t: -b[t[0]]): print(f'  {c:14s} {100 * b[i]:+6.1f} ({100 * lo[i]:+6.1f} to {100 * hi[i]:+6.1f})')

    print('\n## D. The pair: cells where it entered or left the team at a step\n')
    for k in ('Fish 502 (v83-114 -> v115)', 'Mite 502 long', 'Fish v82 -> v83-86 (r1)', 'Mite v82 -> v83-86 (r1)', 'Fish v80 -> v81-82 (r1)', 'Mite v80 -> v81-82 (r1)', 'Other nine teams 502 (v113 -> v115)'):
        for sgn, nm in ((1, 'pair in'), (-1, 'pair out')):
            rr = [r for r in S[k] if ('Cassi & Issac' in r['new']) - ('Cassi & Issac' in r['old']) == sgn]
            if rr: print(f'  {k}: {nm} in {len(rr)} cells: win {100 * np.mean([r["po"] for r in rr]):.0f}% -> {100 * np.mean([r["pn"] for r in rr]):.0f}%   '
                         + '; '.join(sorted({r['map'] for r in rr}))[:150])
    json.dump({k: [dict(r, old=list(r['old']), new=list(r['new']), changed=bool(r['changed']), oteam=list(r['oteam']), oppsame=bool(r.get('oppsame', True))) for r in v] for k, v in S.items()},
              open('/home/ubuntu/tmp-offload/livedraft/steps.json', 'w'))
