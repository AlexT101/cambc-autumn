"""Uncontested Elk/Golem crew clears (2+ same-team strikers, >=10% each): per striker, rounds from its last hit to the
clear (0-1: stayed to the end; more: left early), as shares. Usage: crewleave.py EXTRACT_DIR [team_name]"""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT = sys.argv[1]; ONLY = sys.argv[2] if len(sys.argv) > 2 else None
def one(d):
    meta = json.load(open(d + '/meta.json')); mp = json.load(open(os.path.join(d, meta['mapFile']))); camps = {c['id']: c for c in mp['camps']}
    team = {c['id']: c['team'] for c in meta['champions']}; cg = {c['id']: c['group'] for c in mp['camps']}; names = [t['name'] for t in meta['teams']]
    big = {g['id'] for g in mp['groups'] if any(camps[c]['type'] in ('Elk', 'Golem') for c in g['camps'])}
    o = {}; out = []
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            for cid, amt in e['cdmg']:
                g = cg.get(cid)
                if g in big:
                    x = o.setdefault(g, {'d': collections.Counter(), 'last': {}}); x['d'][e['a']] += amt; x['last'][e['a']] = e['r']
        elif e['k'] == 'group_clear' and e['g'] in o:
            x = o.pop(e['g']); tot = sum(x['d'].values()); t = team[max(x['d'], key=x['d'].get)]
            if any(team[a] != t for a in x['d']) or (ONLY and names[t] != ONLY): continue
            sts = [a for a, v in x['d'].items() if v >= 0.1 * tot]
            if len(sts) < 2: continue
            out += [e['r'] - x['last'][a] for a in sts]
    return out
if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(ROOT + '/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S = [y for r in ex.map(one, ds, chunksize=8) for y in r]
    n = len(S); c = collections.Counter(min(s, 10) for s in S)
    print(n, 'strikers; rounds last hit -> clear:', {k: round(v / n, 3) for k, v in sorted(c.items())})
