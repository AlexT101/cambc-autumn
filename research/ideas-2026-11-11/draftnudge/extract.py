"""Ladder drafts from the big-arm per-day archive (selected columns copied to ARCH): one row per ranked game side.
    py extract.py ARCH OUT.jsonl   (rows: day, at, match, map, side, team, opp, rank, opp_rank, picks (pick order), win)"""
import numpy as np, json, sys
from pathlib import Path
from datetime import datetime, timezone
arch, out = Path(sys.argv[1]), sys.argv[2]
n = 0
with open(out, 'w') as fh:
    for d in sorted(arch.glob('*/data')):
        m = json.loads((d / 'meta.json').read_text()); a = {p.stem: np.load(p, mmap_mode='r') for p in d.glob('*.npy')}
        G = len(a['matches']); st = np.asarray(a['s_team']).reshape(-1, 2)
        ranked = np.asarray(a['g_kind']) == m['kinds'].index('ranked')
        ug, us, uslot, up = (np.asarray(a[k]) for k in ('u_game', 'u_side', 'u_slot', 'u_pick'))
        # picks per (game, side) in slot order; Cassi & Issac is one pick but two units sharing a slot's pick id
        picks = np.full((G, 2, 5), -1, np.int8)
        ok = uslot < 5
        picks[ug[ok], us[ok], uslot[ok]] = up[ok]
        names = [t['name'] for t in m['teams']]
        rank = np.asarray(a['g_rank']); win = np.asarray(a['g_winner']); cr = np.asarray(a['g_created']); mh = np.asarray(a['g_map_hash'])
        end = np.asarray(a['g_end'])
        for g in np.flatnonzero(ranked):
            for s in (0, 1):
                p = [m['picks'][x] for x in picks[g, s] if x >= 0]
                if len(p) < 3 or len(set(p)) != len(p): continue
                fh.write(json.dumps({'day': m['day'], 'at': float(cr[g]), 'match': a['matches'][g].decode(), 'map': m['maps'][int(mh[g])]['name'],
                                     'side': 'ab'[s], 'team': names[st[g, s]], 'opp': names[st[g, 1 - s]], 'rank': int(rank[g, s]),
                                     'opp_rank': int(rank[g, 1 - s]), 'picks': p, 'win': int(win[g] == s), 'end': m['ends'][int(end[g])]}) + '\n'); n += 1
print(n, 'rows')
