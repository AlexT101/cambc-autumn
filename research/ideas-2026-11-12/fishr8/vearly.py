"""Fish's Vesper deaths before round R (default 450) against our win, and her gold and Strength at R by that.
py vearly.py EXT ROWS.json [R]"""
import json, os, sys, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
ext, rf = sys.argv[1:3]; RR = int(sys.argv[3]) if len(sys.argv) > 3 else 450
rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']; out = []
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    typ = {c['id']: c['name'] for c in meta['champions']}
    V = [c for c in R['champions'] if c['team'] == fish and typ[c['id']] == 'Vesper Vale']
    if not V: continue
    v = V[0]; n = len(R['round']); i = min(RR, n) - 1
    out.append((meta['result'].get('winner') != fish, v['deaths'][i], v['earned'][i], v['str'][i], v['kills'][i]))
N = len(out); print(f'{N} games with their Vesper; our win {sum(o[0] for o in out)/N:.3f}')
for k in (0, 1, 2):
    s = [o for o in out if (o[1] == k if k < 2 else o[1] >= 2)]
    if s: print(f'  Vesper deaths by r{RR} {k}{"+" if k == 2 else ""}: {len(s)} ({len(s)/N:.2f}), our win {sum(o[0] for o in s)/len(s):.3f}, her earned {st.mean(o[2] for o in s):.0f}, Strength {st.mean(o[3] for o in s):.0f}, kills {st.mean(o[4] for o in s):.2f}')
