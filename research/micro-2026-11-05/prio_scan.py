"""Scan bit fields of a team's priority for tile encodings (y*W+x, +0/+1; x*H+y) that sit on the setter, a foe or an
ally now, or that the setter reaches within 30 rounds.

    python3 -I research/micro-2026-11-05/prio_scan.py DIR TEAM [games]
"""
import collections, glob, gzip, json, os, sys
d0, team = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 30
C = collections.Counter(); T = collections.Counter(); n = 0
for p in sorted(glob.glob(os.path.join(d0, '*.json.gz'))):
    d = json.load(gzip.open(p))
    if team not in d['teams']: continue
    side = d['teams'].index(team); W, H = d['map']['w'], d['map']['h']
    roster = {c['id']: c for c in d['roster']}
    st = {(row[0], row[1]): row for rows in d['rounds'] for row in rows}
    for a in d['acts']:
        if a['k'] != 9 or roster[a['a']]['team'] != side: continue
        v = a['pr'] & 0xFFFFFFFF
        r = a['r']
        now = {o: (st[(r, o)][2], st[(r, o)][3]) for o in roster if (r, o) in st and st[(r, o)][2] >= 0}
        me = (a['b'][0], a['b'][1])
        fut = [(st[(q, a['a'])][2], st[(q, a['a'])][3]) for q in range(r + 1, r + 30) if (q, a['a']) in st]
        for lo in range(0, 20):
            for w in (12, 13, 14, 15, 16):
                f = (v >> lo) & ((1 << w) - 1)
                for enc in ('yW+x', 'yW+x+1', 'xH+y'):
                    T[(lo, w, enc)] += 1
                    g = f - 1 if enc == 'yW+x+1' else f
                    if g < 0: continue
                    x, y = (g % W, g // W) if enc != 'xH+y' else (g // H, g % H)
                    if y >= H or x >= W: continue
                    t = (x, y)
                    if t == me: C[(lo, w, enc, 'self')] += 1
                    elif any(now.get(o) == t for o in roster if roster[o]['team'] != side): C[(lo, w, enc, 'foe')] += 1
                    elif any(now.get(o) == t for o in roster if roster[o]['team'] == side): C[(lo, w, enc, 'ally')] += 1
                    if any(max(abs(q[0] - x), abs(q[1] - y)) <= 1 for q in fut): C[(lo, w, enc, 'reach')] += 1
    n += 1
    if n >= N: break
print(team, n, 'games')
for k, c in sorted(C.items(), key=lambda kv: -kv[1] / T[kv[0][:3]])[:10]:
    print(' ', k, f'{c / T[k[:3]]:.3f}')
