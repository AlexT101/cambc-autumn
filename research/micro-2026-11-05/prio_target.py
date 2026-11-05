"""Is a team's low-16 priority payload (tile y*W+x+1) where the setter goes, or where an enemy is?

    python3 -I research/micro-2026-11-05/prio_target.py DIR TEAM [games]
"""
import collections, glob, gzip, json, os, sys
d0, team = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 100
C = collections.Counter(); n = 0
for p in sorted(glob.glob(os.path.join(d0, '*.json.gz'))):
    d = json.load(gzip.open(p))
    if team not in d['teams']: continue
    side = d['teams'].index(team); W = d['map']['w']
    roster = {c['id']: c for c in d['roster']}
    st = {(row[0], row[1]): row for rows in d['rounds'] for row in rows}
    alt = set(map(tuple, d['map']['altars']))
    for a in d['acts']:
        if a['k'] != 9 or roster[a['a']]['team'] != side: continue
        v = (a['pr'] & 0xFFFF) - 1
        if v < 0: continue
        tx, ty = v % W, v // W
        m = (a['pr'] >> 16) & 7
        C[('n', m)] += 1
        reach = min((max(abs(st[(r, a['a'])][2] - tx), abs(st[(r, a['a'])][3] - ty)) for r in range(a['r'] + 1, a['r'] + 30)
                     if (r, a['a']) in st and st[(r, a['a'])][2] >= 0), default=99)
        if reach <= 1: C[('reach<=1 in 30r', m)] += 1
        foe = min((max(abs(st[(a['r'], o)][2] - tx), abs(st[(a['r'], o)][3] - ty)) for o, c in roster.items()
                   if c['team'] != side and (a['r'], o) in st and st[(a['r'], o)][2] >= 0), default=99)
        if foe <= 0: C[('on a foe now', m)] += 1
        if min((max(abs(x - tx), abs(y - ty)) for x, y in alt), default=99) <= 1: C[('altar adj', m)] += 1
    n += 1
    if n >= N: break
print(team, n, 'games')
for m in range(8):
    k = C[('n', m)]
    if k: print(f"  mode {m}: n={k} " + ' '.join(f"{lab} {C[(lab, m)] / k:.2f}" for lab in ('reach<=1 in 30r', 'on a foe now', 'altar adj')))
