"""Fish Vesper's kills of our Prism before and after her first Greed emblem: count and gems a game, Prism's bag at her
Greed round, and the gems Prism banks after it. py pgreed.py EXT ROWS.json"""
import json, os, sys, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
GREED = {12 * 6 + 2 * s + 1 for s in range(3)}
ext, rf = sys.argv[1:3]; rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
N = 0; pre = [0, 0]; post = [0, 0]; bags = []; banked = 0; G = 0; W = [0, 0]
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    typ = {c['id']: c['name'] for c in meta['champions']}
    P = [c for c in R['champions'] if c['team'] != fish and typ[c['id']] == 'Prism']
    V = [c for c in R['champions'] if c['team'] == fish and typ[c['id']] == 'Vesper Vale']
    if not P or not V: continue
    p, v = P[0], V[0]; N += 1; n = len(R['round'])
    gi = next((i for i in range(n) if any((v['items'][i] or [])[k] in GREED for k in range(0, len(v['items'][i] or []), 2))), None)
    gr = R['round'][gi] if gi is not None else 10 ** 9
    if gi is not None: G += 1; bags.append(p['gems'][gi]); W[0] += 1; W[1] += meta['result'].get('winner') != fish
    for e in ev:
        if e['k'] == 'death' and e['v'] == p['id'] and e.get('by') == v['id']:
            t = post if e['r'] >= gr else pre; t[0] += 1; t[1] += e.get('gems', 0)
        if e['k'] == 'tribute_end' and e.get('a') == p['id'] and e['r'] >= gr: banked += e.get('gems', 0)
print(f'{N} games with our Prism and their Vesper; Greed in {G}; Prism bag at her Greed median {st.median(bags) if bags else None}; our win in Greed games {W[1]/max(1,W[0]):.3f}')
print(f'  Vesper kills of Prism a game before Greed {pre[0]/N:.2f} ({pre[1]/N:.0f} gems), after {post[0]/N:.2f} ({post[1]/N:.0f} gems); Prism banked after Greed {banked/N:.0f} a game')
