"""Who clears camp groups: distinct attackers per clear (wake -> clear), and the capturer's type (r7 live)."""
import ml, collections
from multiprocessing import Pool
def one(sd):
    g = ml.load(sd, rounds=False)
    if g is None: return None
    team = {c['id']: c['team'] for c in g['meta']['champions']}; name = {c['id']: c['name'] for c in g['meta']['champions']}
    camp2g = {c['id']: c['group'] for c in g['map']['camps']}; gty = {q['id']: q['types'] for q in g['map']['groups']}
    att = collections.defaultdict(set); out = []
    for e in g['ev']:
        if e['k'] in ('attack', 'cast') and e.get('camp') is not None:
            gr = camp2g.get(e['camp'])
            if gr is not None: att[gr].add(e['a'])
        elif e['k'] == 'group_clear':
            a = att.pop(e['g'], set())
            for t in (0, 1):
                s = [x for x in a if team[x] == t]
                if s: out.append(('M' if t == g['mite'] else 'O', e['r'], len(s), tuple(sorted(name[x] for x in s)), tuple(gty[e['g']])))
    return out
if __name__ == '__main__':
    import fl
    R = []
    with Pool(8) as P:
        for o in P.imap_unordered(one, ml.dirs('live'), chunksize=4):
            if o: R += o
    for who in ('M', 'O'):
        rs = [x for x in R if x[0] == who]
        for lab, f in (('all', lambda x: True), ('<r200', lambda x: x[1] < 200), ('Elk+', lambda x: fl.gtype(x[4]).startswith('Elk')), ('Wolf+', lambda x: fl.gtype(x[4]).startswith('Wolf')), ('clusters', lambda x: fl.gtype(x[4]) in ('Gem cl', 'Gold cl')), ('Golem+', lambda x: fl.gtype(x[4]).startswith('Golem'))):
            s = [x for x in rs if f(x)]
            c = collections.Counter(min(x[2], 4) for x in s)
            print(f'{who} {lab}: n={len(s)} attackers mean {fl.mean(x[2] for x in s):.2f}; 1/2/3/4+: ' + ' '.join(f'{c[i]/len(s):.2f}' for i in (1, 2, 3, 4)))
        cc = collections.Counter(x[3] for x in rs if x[2] >= 2 and x[1] < 300)
        print('   common multi-body clearers <r300: ' + '; '.join(f'{"+".join(k)} {v}' for k, v in cc.most_common(8)))
