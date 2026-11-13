"""Home trips (real recalls) in solo extracts, rounds <= END: for each recall_end of the non-idle team, the champion's
health fraction and carried gems at the start, gold spent on arrival, whether it tributes before its next camp hit,
and the trip's excess: channel rounds + walk from spawn to its next camp hit's tile - walk from the recall tile to
that tile (static BFS: walls, holes and altars block). Also walks home (camp -> spawn on foot, no recall).
usage: py fthru_trips.py EXTRACT [END]"""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
A = sys.argv[1]; END = int(sys.argv[2]) if len(sys.argv) > 2 else 600
E = json.load(open(A + '/enums.json')); CH = E['champions']


sys.path.insert(0, os.path.dirname(__file__))
from fthru_common import bfs


def one(d):
    m = json.load(open(d + '/meta.json'))
    mp = json.load(open(os.path.join(d, m['mapFile'])))
    typ = {c['id']: CH[c['type']] for c in m['champions']}
    team = 0 if m['teams'][0]['name'] != 'idle' else 1
    W, H = mp['width'], mp['height']
    block = [False] * (W * H)
    for k in ('walls', 'holes'):
        for x, y in mp[k]: block[y * W + x] = True
    for x, y in mp['altars']: block[y * W + x] = True
    sp = mp['spawn'][team]
    spawn = [(x, y) for x in range(sp['minX'], sp['maxX'] + 1) for y in range(sp['minY'], sp['maxY'] + 1)]
    from_spawn = bfs(W, H, block, spawn)
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = R['round']; ri = {r: i for i, r in enumerate(rr)}
    ch = {c['id']: c for c in R['champions'] if c['team'] == team}
    evs = collections.defaultdict(list)
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > END + 200: break
        a = e.get('a')
        if a in ch: evs[a].append(e)
    out = []
    cache = {}
    for a, es in evs.items():
        ty = typ[a]; c = ch[a]
        for j, e in enumerate(es):
            if e['k'] != 'recall_end' or e['r'] > END: continue
            r = e['r']; f = tuple(e['f'])
            i0 = ri.get(r - 5)
            hp = c['hp'][i0] / c['maxHp'][i0] if i0 is not None and c['maxHp'][i0] else None
            gold0 = c['gold'][i0] if i0 is not None else None
            spent = -sum(x['gold'] for x in es[j + 1:j + 6] if x['k'] == 'shop' and x['r'] == r and x.get('gold', 0) < 0)
            nxt = None; trib = False
            for x in es[j + 1:]:
                if x['k'] == 'tribute_start': trib = True
                if x['k'] in ('attack', 'cast') and x.get('cdmg'):
                    nxt = x; break
            excess = None; out_walk = None
            if nxt:
                t = tuple(nxt['f'])
                out_walk = nxt['r'] - r
                if f not in cache: cache[f] = bfs(W, H, block, [f])
                direct = cache[f][t[1] * W + t[0]]
                via = from_spawn[t[1] * W + t[0]]
                if direct < 10 ** 8 and via < 10 ** 8: excess = 5 + via - direct
            out.append((ty, hp, e['gems'], gold0, spent, trib, out_walk, excess, from_spawn[f[1] * W + f[0]], r))
    return out


if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(A + '/*/meta.json')]
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, ds, chunksize=8): rows.extend(o)
    n = len(ds)
    print('games', n, 'recalls', len(rows), 'per game %.1f' % (len(rows) / n))
    by = collections.defaultdict(list)
    for x in rows: by[x[0]].append(x)
    def summ(xs, label):
        ex = [x[7] for x in xs if x[7] is not None]
        print('%-14s n %6d /game %.2f  hp %.2f  gems %.1f  gold0 %.0f spent %.0f  trib %.0f%%  excess mean %.1f sum/game %.1f  home-dist %.1f' % (
            label, len(xs), len(xs) / n, sum(x[1] or 0 for x in xs) / max(1, len(xs)), sum(x[2] for x in xs) / max(1, len(xs)),
            sum(x[3] or 0 for x in xs) / max(1, len(xs)), sum(x[4] for x in xs) / max(1, len(xs)), 100 * sum(x[5] for x in xs) / max(1, len(xs)),
            sum(ex) / max(1, len(ex)), sum(ex) / n, sum(x[8] for x in xs if x[8] < 10 ** 8) / max(1, len(xs))))
    summ(rows, 'all')
    for ty in sorted(by, key=lambda t: -len(by[t])): summ(by[ty], ty)
    # by reason
    print('-- by reason')
    def reason(x):
        if x[1] is not None and x[1] < 0.5: return 'heal<0.5'
        if x[5]: return 'tribute-after'
        if x[4] > 0: return 'shop'
        return 'other'
    rb = collections.defaultdict(list)
    for x in rows: rb[reason(x)].append(x)
    for k, xs in rb.items(): summ(xs, k)
    print('-- by round')
    for lo in range(0, END, 100):
        summ([x for x in rows if lo < x[9] <= lo + 100], 'r%d-%d' % (lo, lo + 100))
