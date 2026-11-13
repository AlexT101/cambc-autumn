"""Split cells: the same cell (map, side) played by two of our versions with different results. Fish plays the
same until our play differs, so the first round where the two games' states part, and the events around it, show
what decided the game.   py split.py"""
import json, os, sys, collections, gzip
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
ext = os.path.expanduser('~/tmp-offload/fwin/ours/ext')
idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(os.path.expanduser('~/tmp-offload/fwin/ours/frows.json')))
by = collections.defaultdict(list)
for g in idx:
    m = os.path.basename(g['source'])[:-8]
    if m in rows: by[(rows[m]['map'], rows[m]['fish'])].append((g['dir'], rows[m]))
out = []
for cell, L in by.items():
    W = [x for x in L if x[1]['result_o'] == 'win']; Ls = [x for x in L if x[1]['result_o'] == 'loss']
    if not W or not Ls: continue
    (dw, rw), (dl, rl) = W[0], Ls[0]
    mw, Rw, ew, mp = load(ext, dw); ml, Rl, el, _ = load(ext, dl)
    fish = rw['fish']; typ = {c['id']: c['name'] for c in mw['champions']}; team = {c['id']: c['team'] for c in mw['champions']}
    n = min(len(Rw['round']), len(Rl['round']))
    # first round where Fish's units' positions differ (our play reached Fish)
    fdiv = next((i + 1 for i in range(n) if any((a['x'][i], a['y'][i]) != (b['x'][i], b['y'][i]) for a, b in zip(Rw['champions'], Rl['champions']) if a['team'] == fish)), None)
    odiv = next((i + 1 for i in range(n) if any((a['x'][i], a['y'][i]) != (b['x'][i], b['y'][i]) for a, b in zip(Rw['champions'], Rl['champions']) if a['team'] != fish)), None)
    # first round where the score gap between the games (our gems - fish gems) differs by 100+
    def gap(R, i): return R['gems'][1 - fish][i] - R['gems'][fish][i]
    sdiv = next((i + 1 for i in range(n) if abs(gap(Rw, i) - gap(Rl, i)) >= 100), None)
    def deaths(ev, lo, hi):
        return [(e['r'], typ[e['v']][:4], 'F' if team[e['v']] == fish else 'U', e.get('gems', 0), typ.get(e.get('by'), 'camp')[:4]) for e in ev if e['k'] == 'death' and lo <= e['r'] <= hi]
    out.append((cell, rw['version'], rl['version'], odiv, fdiv, sdiv, Rw['round'][-1] if False else len(Rw['round']), len(Rl['round'])))
    hi = sdiv or n
    dw_ = [d for d in deaths(ew, fdiv or 0, hi)]; dl_ = [d for d in deaths(el, fdiv or 0, hi)]
    print(f"{cell[0]:22s} f{cell[1]} win v{rw['version']} loss v{rl['version']} | ours differ r{odiv} fish differ r{fdiv} score gap 100 r{sdiv} | len {len(Rw['round'])}/{len(Rl['round'])}")
    print('    win deaths :', dw_[:10]); print('    loss deaths:', dl_[:10])
