"""Prism deaths to champions: the victim's Focus over its killer's (when the killer is a Prism), what it was doing the
round before (macro.py class), its nearest living ally, who dealt the first champion damage between the two within the
10 rounds before, and whether the victim had seen the killer approach (sees in r-5..r-1). py pdeath.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, '/home/ubuntu/wt/mac13-argo/tools/replay')
from analysis import Game, macro
def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return []
    C = R['champions']; idx = {c['id']: i for i, c in enumerate(C)}; team = {c['id']: c['team'] for c in C}
    name = {c['id']: c['name'] for c in meta['champions']}; rid = {r: i for i, r in enumerate(R['round'])}
    w = meta['result']['winner']
    try:
        cls = macro.classify(Game(d))
    except Exception:
        cls = None
    out = []
    for e in ev:
        if e['k'] != 'death' or name.get(e['v']) != 'Prism' or e.get('by') is None or team.get(e['by']) == team.get(e['v']): continue
        v, k = e['v'], e['by']; i = rid.get(e['r'] - 1)
        if i is None or not C[idx[v]]['alive'][i]: continue
        V, K = C[idx[v]], C[idx[k]]
        p = (V['x'][i], V['y'][i])
        ratio = V['foc'][i] / K['foc'][i] if name[k] == 'Prism' and K['foc'][i] else None
        near = min((cheb(p, (c['x'][i], c['y'][i])) for c in C if c['team'] == team[v] and c['id'] != v and c['alive'][i] and c['x'][i] is not None), default=99)
        first = None
        for f in ev:
            if f['r'] < e['r'] - 10 or f['r'] > e['r']: continue
            if f['k'] in ('attack', 'cast') and f.get('dmg'):
                ids = [x[0] for x in f['dmg']]
                if f.get('a') == v and k in ids: first = 'victim'; break
                if f.get('a') == k and v in ids: first = 'killer'; break
        saw = any(k in (V['sees'][j] or []) for j in range(max(0, i - 5), i))
        doing = None
        if cls is not None:
            try: doing = cls[idx[v]][i]
            except Exception: doing = None
        kt = team[k]; kw = R['gems'][kt][i] + sum(c['gems'][i] for c in C if c['team'] == kt and c['alive'][i])
        kch = any(K['chan'][j] == 2 for j in range(max(0, i - 3), i + 1))
        out.append(dict(kw=kw, kch=kch, ratio=ratio, near=near, first=first, saw=saw, gems=e.get('gems', 0), r=e['r'], doing=doing, vwon=team[v] == w, killer=name[k]))
    return out
if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=8): rows += r
    print('Prism deaths to champions', len(rows), 'killers', Counter(r['killer'] for r in rows).most_common(5))
    rr = [r['ratio'] for r in rows if r['ratio'] is not None]
    print('Focus ratio victim/killer (killer Prism): quartiles', [round(x, 2) for x in st.quantiles(rr, n=4)], ' <0.7:', sum(x < 0.7 for x in rr), 'of', len(rr))
    print('first damage between them in the 10 rounds before:', Counter(r['first'] for r in rows))
    low = [r for r in rows if r['ratio'] is not None and r['ratio'] < 0.7]
    print('  weaker Prism (<0.7): first dmg', Counter(r['first'] for r in low), 'saw killer before', sum(r['saw'] for r in low), 'of', len(low))
    print('nearest ally', sorted(Counter(min(r['near'], 12) // 3 * 3 for r in rows).items()))
    print('weaker-Prism deaths with killer team rich (1000+ wealth):', sum(r['kw'] >= 1000 for r in low), '; killer channelled a tribute in r-3..r:', sum(r['kch'] for r in low))
    print('  by round', sorted(Counter(min(r['r'], 1200) // 200 * 200 for r in low).items()), ' victim bag median', st.median(r['gems'] for r in low))
    eq = [r for r in rows if r['ratio'] is not None and r['ratio'] >= 0.7]
    print('  even-ish (>=0.7):', len(eq), 'first dmg', Counter(r['first'] for r in eq), 'killer rich', sum(r['kw'] >= 1000 for r in eq), 'bag median', st.median(r['gems'] for r in eq))
    print('doing the round before', Counter(r['doing'] for r in rows).most_common(8))
