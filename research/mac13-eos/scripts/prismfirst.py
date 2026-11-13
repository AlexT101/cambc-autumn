"""First Prism death of each game: bags, Focus ratio, prior sight of the killer Prism, who approached, how fast it died."""
import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def cheb(c, d, i):
    if c['x'][i] is None or d['x'][i] is None: return 99
    return max(abs(c['x'][i]-d['x'][i]), abs(c['y'][i]-d['y'][i]))
def g(d):
    meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    names = {int(c['id']): c['name'] for c in meta['champions']}; team = {int(c['id']): int(c['team']) for c in meta['champions']}
    ch = {int(c['id']): c for c in R['champions']}; w = meta['result']['winner']
    pr = [i for i in ch if names[i] == 'Prism']
    if len(pr) != 2: return None
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'death' and e['v'] in pr:
            v = e['v']; o = pr[0] if pr[1] == v else pr[1]; r = e['r']; V, O = ch[v], ch[o]
            by = names.get(e.get('by'), 'camp') if e.get('by') is not None else 'camp'
            i = max(0, r-1)
            # rounds since the dead Prism last had full-ish hp (>=90%)
            k = i
            while k > 0 and V['hp'][k]/V['maxHp'][k] < 0.9: k -= 1
            j = max(0, k-1)
            seen = [any(o == x for x in (V['sees'][t] or [])) for t in range(max(0, k-15), k+1)]
            near = cheb(V, O, k)
            return dict(r=r, lost=team[v] != w, by=by, gv=V['gems'][k], go=O['gems'][k], fv=V['foc'][k], fo=O['foc'][k], kill_time=r-k,
                        seen_any=any(seen), seen_k=seen[-1] if seen else False, dist_k=near, oalive=bool(O['alive'][k]),
                        av=sum(1 for c in ch if team[c] == team[v] and c != v and ch[c]['alive'][k] and cheb(ch[c], V, k) <= 8),
                        ao=sum(1 for c in ch if team[c] == team[o] and c != o and ch[c]['alive'][k] and cheb(ch[c], V, k) <= 8))
    return None
if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: E = [x for x in ex.map(g, dirs, chunksize=8) if x]
    print('first Prism deaths', len(E), 'lost', round(sum(e['lost'] for e in E)/len(E), 3))
    P = [e for e in E if e['by'] == 'Prism']
    print('killed by enemy Prism', len(P), 'lost', round(sum(e['lost'] for e in P)/len(P), 3))
    m = lambda S, f: round(sum(f(e) for e in S)/len(S), 3)
    med = lambda S, f: sorted(f(e) for e in S)[len(S)//2]
    for lab, S in (('all', E), ('by Prism', P), ('by Prism r<600', [e for e in P if e['r'] < 600])):
        print(f'== {lab} n {len(S)}: round med {med(S, lambda e: e["r"])}  bag dead/killer med {med(S, lambda e: e["gv"])}/{med(S, lambda e: e["go"])}')
        print('   focus killer/dead med', round(med(S, lambda e: e['fo']/max(1, e['fv'])), 2), ' frac killer bigger', m(S, lambda e: e['fo'] > e['fv']), ' frac killer >1.5x', m(S, lambda e: e['fo'] > 1.5*e['fv']))
        print('   rounds from last >=90% hp to death med', med(S, lambda e: e['kill_time']), ' dist to enemy Prism then med', med(S, lambda e: e['dist_k']), ' saw it in prior 15r', m(S, lambda e: e['seen_any']), 'seeing then', m(S, lambda e: e['seen_k']))
        print('   allies within 8', m(S, lambda e: e['av']), ' enemies (non-Prism) within 8', m(S, lambda e: e['ao']))
