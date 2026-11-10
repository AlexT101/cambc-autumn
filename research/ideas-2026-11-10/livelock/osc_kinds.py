import json, gzip, glob, os, sys, collections
root = sys.argv[1]
rows = json.load(open(root + '/osc_rows.json'))
K = collections.Counter(); T = collections.Counter(); types = collections.Counter()
for r in rows:
    d = r['dir']; m = json.load(open(d + 'meta.json'))
    mp = json.load(open(glob.glob(root + '/maps/' + m['map']['hash'] + '.json')[0]))
    capt = {tuple(t) for g in mp['groups'] for t in g['tiles']}
    R = json.load(gzip.open(d + 'rounds.json.gz')); idx = {c['id']: c for c in R['champions']}
    names = {c['id']: c['type'] for c in m['champions']}
    for e in r['eps']:
        c = idx[e['id']]; i0 = R['round'].index(e['r0']); i1 = i0 + e['len']
        cap = any(tuple(t) in capt for t in e['tiles'])
        seen = any(c['sees'][i] for i in range(i0, min(i1, len(R['round']))))
        bag = max(c['gems'][i] for i in range(i0, min(i1, len(R['round']))))
        k = ('capture-tile' if cap else 'other') + ('/enemy-seen' if seen else '/no-enemy') + ('/bag20+' if bag >= 20 else '')
        K[k] += e['len']; types[names[e['id']]] += e['len']
tot = sum(K.values())
for k, v in K.most_common(): print(f'{k:35s} {v:6d} {100*v/tot:5.1f}%')
print(types.most_common())
