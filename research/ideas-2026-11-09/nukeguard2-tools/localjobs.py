# localjobs.py OUT.pkl EXTRACT_DIR BATCH... : (analysis dir, game info) for local ab batches, CAND = bot 0.
import json, sys, os, pickle
out, X = sys.argv[1], sys.argv[2]
idx = {os.path.realpath(g['source'] if g['source'].startswith('/') else os.path.join('/home/ubuntu/cambc-autumn', g['source'])): g['dir']
       for g in json.load(open(X + '/index.json'))['games'] if g.get('ok', True)}
jobs = []
for b in sys.argv[3:]:
    opp = 'Inte' if b.rstrip('/').split('-')[-2].endswith('F') else 'Mite'
    for m in json.load(open(b + '/results.json'))['matches']:
        p = m.get('replay')
        if not p or m.get('winner') is None: continue
        d = idx.get(os.path.realpath(p))
        if not d: continue
        side = 'a' if m['order'][0] == 0 else 'b'
        jobs.append((X + '/' + d, dict(version=0, opp=opp, bot=b.rstrip('/').split('ab-ng2-mech-')[-1].rsplit('-', 2)[0] if 'mech' in b else '', side=side, result='win' if m['winner'] == 0 else 'loss', replay=p)))
pickle.dump(jobs, open(out, 'wb')); print(len(jobs))
