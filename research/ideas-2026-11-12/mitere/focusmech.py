"""Vesper focus mechanism, local games against a body: per arm, our basic attacks with the enemy Vesper and another enemy
in reach (start-of-round positions) that hit her, her deaths, our deaths and those by her, and the paired win against
BASE. Usage: focusmech.py EXT_ROOT BASE ARM..."""
import sys, json, gzip, glob, os, re, collections
from multiprocessing import Pool
RANGED = {'Vesper Vale', 'Prism', 'Stellar', 'Tavi', 'Willow', 'Cassi'}
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(args):
    mp, bot = args
    g = os.path.dirname(mp); m = json.load(open(mp))
    src = m['source']; k = re.search(r'-k(\d)-ladder', src).group(1); stem = os.path.basename(src).split('-', 1)[1]
    t = [i for i, x in enumerate(m['teams']) if x['name'] == bot][0]
    name = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
    V = [c for c in name if team[c] != t and name[c] == 'Vesper Vale']
    s = collections.Counter()
    if V:
        v = V[0]
        C = {c['id']: c for c in json.load(gzip.open(f'{g}/rounds.json.gz', 'rt'))['champions']}
        def pos(c, r):
            i = max(0, r - 2)
            return (C[c]['x'][i], C[c]['y'][i]) if C[c]['alive'][i] and C[c]['x'][i] is not None else None
        for line in gzip.open(f'{g}/events.jsonl.gz', 'rt'):
            e = json.loads(line)
            if e['k'] == 'death' and e['v'] in team:
                if team[e['v']] == t: s['deaths'] += 1; s['deaths_v'] += e.get('by') == v
                elif e['v'] == v: s['v_deaths'] += 1
            if e['k'] != 'attack' or team.get(e.get('a')) != t or team.get(e.get('tgt'), t) == t: continue
            r = e['r']; f = tuple(e['f']); rg = 3 if name[e['a']] in RANGED else 1
            cands = [c for c in name if team[c] != t and pos(c, r) and cheb(pos(c, r), f) <= rg]
            if v in cands and len(cands) >= 2: s['choices'] += 1; s['hit_v'] += e['tgt'] == v
            if e['tgt'] == v: s['hits_v'] += 1
            s['hits'] += 1
    return (k, stem), bool(V), m['result']['winner'] == t, s
def load(root, bot):
    with Pool(8) as P:
        return {key: (hv, w, s) for key, hv, w, s in P.map(one, [(mp, bot) for mp in glob.glob(f'{root}/{bot}/*/meta.json')], chunksize=8)}
if __name__ == '__main__':
    root, base, arms = sys.argv[1], sys.argv[2], sys.argv[3:]
    B = load(root, base)
    for arm in [base] + arms:
        A = B if arm == base else load(root, arm)
        ks = [k for k in A if k in B and B[k][0]]
        S = collections.Counter()
        for k in ks: S.update(A[k][2])
        n = len(ks); wa = sum(A[k][1] for k in ks); wb = sum(B[k][1] for k in ks); fl = sum(A[k][1] != B[k][1] for k in ks)
        print(f'{arm}: {n} games with an enemy Vesper; win {wa/n:.1%} ({(wa-wb)/n*100:+.1f} vs {base}, flips {fl}); '
              f'hits on her when another is in reach {S["hit_v"]/max(1,S["choices"]):.0%} of {S["choices"]/n:.1f}/game; her share of our hits {S["hits_v"]/max(1,S["hits"]):.0%}; '
              f'her deaths {S["v_deaths"]/n:.2f}/game; our deaths {S["deaths"]/n:.2f} (by her {S["deaths_v"]/n:.2f})')
        others = [k for k in A if k in B and not B[k][0]]
        if arm != base and others:
            print(f'   games without an enemy Vesper: {len(others)}, flips {sum(A[k][1] != B[k][1] for k in others)}')
