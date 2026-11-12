"""Paired read (all games, then by our comp) of arms against mf-c2 (same map, side and noise member): win difference by our comp, plus capture gems by
holder, gem-cluster captures by r100, deaths and gems lost. Usage: paired.py EXT_ROOT BASE ARM..."""
import sys, json, gzip, glob, os, re, collections
root, base, arms = sys.argv[1], sys.argv[2], sys.argv[3:]
def load(bot):
    out = {}
    for mp in glob.glob(f'{root}/{bot}/*/meta.json'):
        g = os.path.dirname(mp); m = json.load(open(mp))
        src = m['source']; k = re.search(r'-k(\d)-ladder', src).group(1); stem = os.path.basename(src).split('-', 1)[1]
        t = [i for i, x in enumerate(m['teams']) if x['name'] == bot][0]
        name = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
        ours = {name[c] for c in name if team[c] == t}
        mapf = os.path.normpath(os.path.join(g, m['mapFile']))
        gm = {q['id']: q for q in json.load(open(mapf))['groups']}
        s = collections.Counter()
        for line in gzip.open(f'{g}/events.jsonl.gz', 'rt'):
            e = json.loads(line)
            if e['k'] == 'capture' and e['team'] == t:
                q = gm[e['g']]
                if e['r'] <= 100 and q['gold'] == 0 and q['gems'] > 0 and not any(x in ('Wolf', 'Elk', 'Golem', 'Monolith') for x in q.get('types', [])): s['gemcl100'] += 1
                for sh in e['shares']: s['gems_' + name[sh[0]]] += sh[1]
            elif e['k'] == 'death' and team.get(e['v']) == t:
                s['deaths'] += 1; s['gemslost'] += e.get('gems', 0)
        comp = 'V+P' if {'Vesper Vale', 'Prism'} <= ours else ('V' if 'Vesper Vale' in ours else 'noV')
        out[(k, stem)] = (comp, m['result']['winner'] == t, s, {c['name']: c['stats'] for c in m['champions'] if c['team'] == t})
    return out
B = load(base)
for arm in arms:
    A = load(arm)
    for comp in ('all', 'V+P', 'V', 'noV'):
        ks = [k for k in A if k in B and comp in ('all', B[k][0])]
        if not ks: continue
        wa = sum(A[k][1] for k in ks); wb = sum(B[k][1] for k in ks); flips = sum(A[k][1] != B[k][1] for k in ks)
        print(f'{arm} {comp}: {len(ks)} pairs, win {wa/len(ks):.1%} vs {wb/len(ks):.1%} ({(wa-wb)/len(ks)*100:+.1f}, flips {flips})')
        if comp not in ('all', 'V+P'): continue
        def avg(D, f): return sum(f(D[k]) for k in ks) / len(ks)
        for lab, f in (('gems lost on deaths', lambda d: d[2]['gemslost']), ('gem-cluster captures by r100', lambda d: d[2]['gemcl100']), ('deaths', lambda d: d[2]['deaths']),
                       ('Prism capture gems', lambda d: d[2]['gems_Prism']), ('Vesper capture gems', lambda d: d[2]['gems_Vesper Vale']),
                       ('Prism deaths', lambda d: d[3].get('Prism', {}).get('deaths', 0)), ('Vesper deaths', lambda d: d[3].get('Vesper Vale', {}).get('deaths', 0)),
                       ('Prism submitted gems', lambda d: d[3].get('Prism', {}).get('submittedGems', 0)), ('Vesper submitted gems', lambda d: d[3].get('Vesper Vale', {}).get('submittedGems', 0)),
                       ('team submitted gems', lambda d: sum(v.get('submittedGems', 0) for v in d[3].values())),
                       ('team collected gems', lambda d: sum(v.get('collectedGems', 0) for v in d[3].values()))):
            print(f'    {lab}: {avg(A, f):.1f} vs {avg(B, f):.1f}')
