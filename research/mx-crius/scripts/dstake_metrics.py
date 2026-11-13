"""Per bot (team name) of an extract: champion deaths a game by victim type, gems handed over by those deaths, the killers'
types, Prism deaths with 100+ bags, and kills by our Prism. usage: py dstake_metrics.py EXTRACT_DIR"""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
A = sys.argv[1]
CH = json.load(open(A + '/enums.json'))['champions']


def one(d):
    m = json.load(open(d + '/meta.json'))
    names = [t['name'] for t in m['teams']]
    typ = {c['id']: CH[c['type']] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    out = {n: collections.Counter() for n in names}
    w = m['result']['winner']
    for t, n in enumerate(names):
        out[n]['games'] += 1
        out[n]['wins'] += w == t
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] != 'death': continue
        v = e['v']; vt = team[v]; by = e.get('by'); g = e.get('gems', 0) or 0
        n = names[vt]
        champ = by is not None and by in team and team[by] != vt
        if e.get('linked') is None:
            out[n]['deaths'] += 1
            out[n]['deaths ' + typ[v]] += 1
            out[n]['deaths to champs' if champ else 'deaths to camps/other'] += 1
        if champ:
            k = names[team[by]]
            out[n]['gems lost to kills'] += g
            out[k]['gems won by kills'] += g
            out[k]['kills by ' + typ[by]] += e.get('linked') is None
            if typ[by] == 'Prism': out[k]['gems won by Prism kills'] += g
            if typ[v] == 'Prism':
                out[n]['Prism deaths to champs'] += 1
                if g >= 100: out[n]['Prism deaths bag100+'] += 1; out[n]['Prism deaths bag100+ won'] += w == vt
            if g >= 100: out[n]['deaths bag100+'] += 1
    return out


if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(A + '/*/meta.json')]
    T = collections.defaultdict(collections.Counter)
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, ds, chunksize=16):
            for n, c in o.items(): T[n].update(c)
    keys = sorted(set(k for c in T.values() for k in c) - {'games'})
    names = sorted(T)
    print('%-28s' % 'per game', ' '.join('%12s' % n for n in names))
    for k in keys:
        if k == 'Prism deaths bag100+ won':
            print('%-28s' % 'Prism bag100+ death: won %', ' '.join('%12.1f' % (100 * T[n][k] / max(1, T[n]['Prism deaths bag100+'])) for n in names))
            continue
        print('%-28s' % k, ' '.join('%12.3f' % (T[n][k] / max(1, T[n]['games'])) for n in names))
    print('%-28s' % 'games', ' '.join('%12d' % T[n]['games'] for n in names))
