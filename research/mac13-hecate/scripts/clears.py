"""Clear -> capture flow: who clears, who captures, delay, steals."""
import sys, json, gzip, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    except Exception:
        return None
    team = {c['id']: c['team'] for c in meta['champions']}
    name = {c['id']: c['name'] for c in meta['champions']}
    last_clear = {}
    out = []
    for e in ev:
        k = e.get('k')
        if k == 'group_clear':
            last_clear[e['g']] = (e['r'], e.get('by', -1))
        elif k == 'capture':
            g = e['g']
            lc = last_clear.pop(g, None)
            gems = sum(s[1] for s in e['shares']); gold = sum(s[2] for s in e['shares'])
            holders = [name[s[0]] for s in e['shares']]
            if lc:
                out.append(dict(delay=e['r']-lc[0], steal=team.get(lc[1]) != e['team'], clearer=name.get(lc[1]), holders=holders, gems=gems, gold=gold, r=e['r']))
    return out

if __name__ == '__main__':
    dirs = [p for a in sys.argv[1:] for p in Path(a).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if o: rows += o
    n = len(dirs)
    print('captures/game', len(rows)/n)
    st = [x for x in rows if x['steal']]
    print('steals/game', len(st)/n, 'gems', sum(x['gems'] for x in st)/n, 'gold', sum(x['gold'] for x in st)/n)
    print('gems/game captured', sum(x['gems'] for x in rows)/n, 'gold', sum(x['gold'] for x in rows)/n)
    dl = collections.Counter(min(x['delay']//5*5, 60) for x in rows)
    print('clear->capture delay (5-bins):', sorted(dl.items()))
    pr = [x for x in rows if 'Prism' in x['holders'] and x['clearer'] != 'Prism']
    print('Prism holds on others clears/game', len(pr)/n, 'mean delay', sum(x['delay'] for x in pr)/max(1,len(pr)), 'gems', sum(x['gems'] for x in pr)/n)
    long = [x for x in rows if x['delay'] >= 15]
    print('delay>=15: /game', len(long)/n, 'gems', sum(x['gems'] for x in long)/n, 'holders', collections.Counter(h for x in long for h in x['holders']).most_common(5))
    hc = collections.Counter(len(x['holders']) for x in rows); print('holders count', sorted(hc.items()))
    gh = collections.defaultdict(float)
    for x in rows:
        for h in x['holders']: gh[h] += x['gems']/len(x['holders'])
    print('capture gems by holder type /game:', {k: round(v/n,1) for k,v in sorted(gh.items(), key=lambda t:-t[1])})
