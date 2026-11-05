"""Check per-team priority layouts against the setter's own state at the moment of the set.

    python3 -I research/micro-2026-11-05/prio_decode.py DIR TEAM [games]
"""
import collections, glob, gzip, json, os, sys
d0, team = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 200
ok = collections.Counter(); tot = 0; n = 0
mode = collections.defaultdict(collections.Counter)
for p in sorted(glob.glob(os.path.join(d0, '*.json.gz'))):
    d = json.load(gzip.open(p))
    if team not in d['teams']: continue
    side = d['teams'].index(team); W, H = d['map']['w'], d['map']['h']
    roster = {c['id']: c for c in d['roster']}
    st = {(row[0], row[1]): row for rows in d['rounds'] for row in rows}
    for a in d['acts']:
        if a['k'] != 9 or roster[a['a']]['team'] != side: continue
        v = a['pr'] & 0xFFFFFFFF; x, y = a['b'][0], a['b'][1]
        s = st.get((a['r'], a['a']))
        tot += 1
        for name, val in [('lo16=yW+x+1', y * W + x + 1), ('lo16=yW+x', y * W + x), ('lo16=xH+y+1', x * H + y + 1)]:
            if v & 0xFFFF == val: ok[name] += 1
        if s:
            m = (v >> 16) & 7
            mode[m]['n'] += 1; mode[m]['gems'] += s[8]; mode[m]['hpfrac%'] += 100 * s[4] / max(1, s[5]); mode[m]['chan_' + str(s[14])] += 1
            mode[m]['lo0'] += (v & 0xFFFF) == 0
    n += 1
    if n >= N: break
print(team, n, 'games', tot, 'sets', {k: f'{v / tot:.3f}' for k, v in ok.items()})
for m in sorted(mode):
    c = mode[m]; k = c['n']
    print(f"  mode {m}: n={k} mean gems {c['gems'] / k:.1f} hp {c['hpfrac%'] / k:.0f}% lo16=0 {c['lo0'] / k:.2f} chan {[(q, c[q]) for q in c if q.startswith('chan_')]}")
