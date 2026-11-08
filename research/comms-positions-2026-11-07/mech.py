"""Told records against replay truth. py mech.py BATCH EXTRACT_DIR"""
import zipfile, glob, json, gzip, os, collections, sys
B, X = sys.argv[1], sys.argv[2]
idx = json.load(open(X + '/index.json'))['games']
src = {os.path.basename(g['source']): g['dir'] for g in idx}
c = collections.Counter()
for z in glob.glob(B + '/*.repl26a'):
    d = src.get(os.path.basename(z))
    if not d: continue
    zf = zipfile.ZipFile(z); R = None
    for nm in zf.namelist():
        if not nm.endswith('.stdout'): continue
        side = 0 if 'team-a' in nm else 1
        for line in zf.read(nm).decode(errors='replace').splitlines():
            p = line.split()
            if not p: continue
            if p[0] == 'CLP': c['clp'] += 1; c['clp-on'] += int(p[2]); c['clp-cell%s' % p[4]] += 1; continue
            if p[0] == 'WF': c['wf-' + p[4]] += 1; continue
            if p[0] != 'TOLD': continue
            if R is None:
                R = json.load(gzip.open(os.path.join(X, d, 'rounds.json.gz'))); ri = {r: i for i, r in enumerate(R['round'])}
                teams = [sorted([ch for ch in R['champions'] if ch['team'] == t], key=lambda ch: ch['id']) for t in (0, 1)]
            r, kind, who, x, y, age = int(p[1]), int(p[3]), int(p[4]), int(p[5]), int(p[6]), int(p[7])
            grp = teams[1 - side] if kind == 0 else teams[side]
            k = 'sight' if kind == 0 else 'ally'
            c[k] += 1; c[k + '-age%d' % age] += 1
            i = ri.get(r - age - 1)  # state at the end of the round before the seen round ~ its start
            if i is None or who >= len(grp) or not grp[who]['alive'][i]: c[k + '-dead'] += 1; continue
            e = max(abs(grp[who]['x'][i] - x), abs(grp[who]['y'][i] - y))
            c[k + '-err%d' % min(e, 6)] += 1
            if kind == 0:
                j = ri.get(r)
                if j is not None and grp[who]['alive'][j]:
                    me = teams[side][int(p[2])]
                    c['sight-reader-saw-already'] += (grp[who]['id'] in (me['sees'][j] or []))
for k in sorted(c): print(k, c[k])
