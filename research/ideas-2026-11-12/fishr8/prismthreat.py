"""Our Prism against Fish's Vesper, per game with both: the first round her turn's two hits (attack + reset) reach our
Prism's max health ('lethal'), Prism's bag then, its gems lost to Vesper / to anyone and banked after it, and our win.
py prismthreat.py EXT ROWS.json"""
import json, os, sys, collections, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
ext, rf = sys.argv[1:3]; rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
out = []
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    typ = {c['id']: c['name'] for c in meta['champions']}; ch = {c['id']: c for c in R['champions']}
    P = [c for c in R['champions'] if c['team'] != fish and typ[c['id']] == 'Prism']
    V = [c for c in R['champions'] if c['team'] == fish and typ[c['id']] == 'Vesper Vale']
    if not P or not V: continue
    p, v = P[0], V[0]; n = len(R['round'])
    L = next((i for i in range(n) if 2 * v['str'][i] >= p['maxHp'][i]), None)
    win = meta['result'].get('winner') != fish
    rL = R['round'][L] if L is not None else None
    lostV = lostA = banked = 0
    for e in ev:
        if rL is None or e['r'] < rL: continue
        if e['k'] == 'death' and e['v'] == p['id']:
            lostA += e.get('gems', 0); lostV += e.get('gems', 0) * (e.get('by') == v['id'])
        if e['k'] == 'tribute_end' and e.get('a') == p['id']: banked += e.get('gems', 0)
    out.append(dict(win=win, L=rL, bag=p['gems'][L] if L is not None else None, lostV=lostV, lostA=lostA, banked=banked, rounds=n))
N = len(out); H = [o for o in out if o['L'] is not None]
print(f'{N} games with our Prism and their Vesper; win {sum(o["win"] for o in out)/N:.3f}; Vesper becomes lethal in {len(H)} ({len(H)/N:.2f})')
if H:
    print(f'  lethal round median {st.median(o["L"] for o in H)}, Prism bag then median {st.median(o["bag"] for o in H)}')
    print(f'  after it, a game: Prism gems lost to Vesper {sum(o["lostV"] for o in H)/len(H):.0f}, to anyone {sum(o["lostA"] for o in H)/len(H):.0f}, Prism banked {sum(o["banked"] for o in H)/len(H):.0f}')
    print(f'  win, lethal games {sum(o["win"] for o in H)/len(H):.3f}; not lethal {sum(o["win"] for o in out if o["L"] is None)/max(1,N-len(H)):.3f}')
    for a, b in ((0, 300), (300, 450), (450, 600), (600, 9999)):
        s = [o for o in H if a <= o['L'] < b]
        if s: print(f'  lethal at r{a}-{b}: {len(s)} games, win {sum(o["win"] for o in s)/len(s):.2f}, lost to V after {sum(o["lostV"] for o in s)/len(s):.0f}, banked after {sum(o["banked"] for o in s)/len(s):.0f}')
