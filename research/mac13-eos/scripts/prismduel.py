"""Prism-vs-Prism encounters in a mirror: who has the bigger bag, who dies, who wins.
An encounter starts when the two Prisms come within RANGE (Chebyshev) and ends when they part (> RANGE+3) or one dies."""
import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
RANGE = 6

def g(d):
    meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    names = {int(c['id']): c['name'] for c in meta['champions']}; team = {int(c['id']): int(c['team']) for c in meta['champions']}
    w = meta['result']['winner']; ch = {int(c['id']): c for c in R['champions']}
    pr = [i for i in ch if names[i] == 'Prism']
    if len(pr) != 2: return None
    a, b = pr
    n = len(ch[a]['x'])
    deaths = []
    killer = {}
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'death' and e['v'] in (a, b):
            deaths.append((e['r'], e['v'], names.get(e.get('by'), 'camp') if e.get('by') is not None else 'camp', e['gems']))
    firstdeath = deaths[0] if deaths else None
    encs = []
    cur = None
    for i in range(n):
        al = ch[a]['alive'][i] and ch[b]['alive'][i]
        dist = max(abs(ch[a]['x'][i]-ch[b]['x'][i]), abs(ch[a]['y'][i]-ch[b]['y'][i])) if al and ch[a]['x'][i] is not None and ch[b]['x'][i] is not None else 99
        if cur is None and al and dist <= RANGE:
            cur = dict(r0=i, ga=ch[a]['gems'][i], gb=ch[b]['gems'][i], ha=ch[a]['hp'][i]/max(1,ch[a]['maxHp'][i]), hb=ch[b]['hp'][i]/max(1,ch[b]['maxHp'][i]))
        elif cur is not None and (not al or dist > RANGE+3):
            cur['r1'] = i
            dead = [x for x in deaths if cur['r0'] <= x[0] <= i+2]
            cur['dead'] = [(names[v] if False else ('a' if v == a else 'b'), by) for (_, v, by, _) in dead]
            encs.append(cur); cur = None
    return dict(w=w, ta=team[a], tb=team[b], encs=encs, first=(firstdeath[0], 'a' if firstdeath[1] == a else 'b', firstdeath[2], firstdeath[3]) if firstdeath else None,
                ndeaths=collections.Counter('a' if v == a else 'b' for (_, v, _, _) in deaths), n=n)

if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res = [x for x in ex.map(g, dirs, chunksize=8) if x]
    print('games', len(res))
    fd = [r for r in res if r['first']]
    lw = sum((r['ta'] if r['first'][1] == 'a' else r['tb']) != r['w'] for r in fd)
    print('first Prism death in', len(fd), 'games; its team loses', round(lw/len(fd), 3), 'median round', sorted(r['first'][0] for r in fd)[len(fd)//2])
    print('first Prism death killers', collections.Counter(r['first'][2] for r in fd).most_common())
    E = [(r, e) for r in res for e in r['encs']]
    print('encounters', len(E), 'per game', round(len(E)/len(res), 2))
    tot = collections.Counter()
    for r, e in E:
        big = 'a' if e['ga'] > e['gb'] else 'b' if e['gb'] > e['ga'] else None
        dead = [x for x, _ in e['dead']]
        if not dead: tot['none'] += 1; continue
        if len(set(dead)) == 2: tot['both'] += 1; continue
        if big is None: tot['equal-bag death'] += 1; continue
        tot['bigger dies' if dead[0] == big else 'smaller dies'] += 1
    print('encounter outcomes', tot.most_common())
    # by bag ratio bins
    bins = collections.defaultdict(lambda: [0, 0, 0])
    for r, e in E:
        big, sm = max(e['ga'], e['gb']), min(e['ga'], e['gb'])
        ratio = (big+20)/(sm+20)
        k = '1-1.25' if ratio < 1.25 else '1.25-1.6' if ratio < 1.6 else '1.6-2.5' if ratio < 2.5 else '2.5+'
        bigk = 'a' if e['ga'] >= e['gb'] else 'b'
        dead = set(x for x, _ in e['dead'])
        bins[k][0] += 1; bins[k][1] += (bigk in dead); bins[k][2] += ((('b' if bigk == 'a' else 'a')) in dead)
    for k in sorted(bins): print(' ratio', k, 'n', bins[k][0], 'bigger dies', bins[k][1], 'smaller dies', bins[k][2])
    # gem gap -> win
    print('mean enc len', round(sum(e['r1']-e['r0'] for _, e in E)/max(1, len(E)), 1))
