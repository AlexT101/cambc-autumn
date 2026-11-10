import json, gzip, glob, os, sys, collections
def load(root, name):
    out = {}
    for d in glob.glob(root + '/*/'):
        if not os.path.exists(d + 'meta.json'): continue
        m = json.load(open(d + 'meta.json')); tn = [t['name'] for t in m['teams']]
        team = tn.index(name); src = os.path.basename(m['source'])
        key = (os.path.basename(os.path.dirname(m['source']))[-7:], src)
        ev = [json.loads(l) for l in gzip.open(d + 'events.jsonl.gz', 'rt')]
        ours = {c['id'] for c in m['champions'] if c['team'] == team}
        canc = [e for e in ev if e['k'] == 'tribute_cancel' and e['a'] not in ours and e.get('cause') in ('lock', 'stun')]
        big = [e for e in ev if e['k'] == 'tribute_start' and e['a'] not in ours and e['gems'] >= 100]
        deaths = sum(1 for e in ev if e['k'] == 'death' and e['v'] in ours)
        out[key] = dict(won=m['result']['winner'] == team, canc=len(canc), cbig=sum(e['gems'] >= 100 for e in canc), big=len(big),
                        gems=m['result']['gems'][1 - team], deaths=deaths)
    return out
A = load(sys.argv[1], sys.argv[2]); B = load(sys.argv[3], sys.argv[4])
keys = A.keys() & B.keys()
fired = [k for k in keys if A[k]['cbig'] > B[k]['cbig']]
print('paired', len(keys), 'games where cand cancels more big tributes', len(fired))
print('  cand wins', sum(A[k]['won'] for k in fired), 'base wins', sum(B[k]['won'] for k in fired))
print('  enemy gems cand', sum(A[k]['gems'] for k in fired), 'base', sum(B[k]['gems'] for k in fired), 'our deaths cand', sum(A[k]['deaths'] for k in fired), 'base', sum(B[k]['deaths'] for k in fired))
print('all: cand wins', sum(A[k]['won'] for k in keys), 'base', sum(B[k]['won'] for k in keys), 'big enemy tributes started cand', sum(A[k]['big'] for k in keys), 'base', sum(B[k]['big'] for k in keys))
