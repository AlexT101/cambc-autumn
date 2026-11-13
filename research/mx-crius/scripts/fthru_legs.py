"""Walk legs between jobs in solo extracts, rounds <= END (non-idle team): a leg runs from a champion's last camp hit on
one group to its first hit on another, with no recall, tribute or death in between. Its rounds minus the static BFS
walk between the two hit tiles (walls, holes, altars block) is its excess: detours, waits, abandoned walks, holds.
Hold rounds (on a capturing group's tile) are counted apart. Excess is split by whether the champion's distance to the
next job's tile rose at some step (turned back: an abandoned or changed target).
usage: py fthru_legs.py EXTRACT [END]"""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from fthru_common import bfs
A = sys.argv[1]; END = int(sys.argv[2]) if len(sys.argv) > 2 else 600
E = json.load(open(A + '/enums.json')); CH = E['champions']


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
    cg = {c['id']: c['group'] for c in mp['camps']}
    tile_group = {}
    for g in mp['groups']:
        for t in g['tiles']: tile_group[tuple(t)] = g['id']
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = R['round']; ri = {r: i for i, r in enumerate(rr)}
    ch = {c['id']: c for c in R['champions'] if c['team'] == team}
    marks = collections.defaultdict(list)  # (r, kind, group, tile)
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > END: break
        a = e.get('a')
        if a not in ch: continue
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            marks[a].append((e['r'], 'hit', cg.get(e['cdmg'][0][0]), tuple(e['f'])))
        elif k in ('recall_end', 'tribute_start', 'death', 'teleport_start'):
            marks[a].append((e['r'], 'break', None, None))
    out = collections.Counter()
    cache = {}
    for a, mk in marks.items():
        c = ch[a]; ty = typ[a]
        prev = None
        for x in mk:
            if x[1] == 'break': prev = None; continue
            if prev is None or prev[2] == x[2]: prev = x; continue
            r0, r1 = prev[0], x[0]
            t = x[3]
            if t not in cache: cache[t] = bfs(W, H, block, [t])
            f = cache[t]
            s = prev[3]
            walk = f[s[1] * W + s[0]]
            if walk >= 10 ** 8: prev = x; continue
            rounds = r1 - r0
            # hold rounds and turn-backs inside the leg
            hold = 0; back = False; last = walk
            for r in range(r0 + 1, r1 + 1):
                i = ri.get(r)
                if i is None or not c['alive'][i] or c['x'][i] is None: continue
                p = (c['x'][i], c['y'][i])
                g = tile_group.get(p)
                if g is not None and g != x[2]:
                    hold += 1
                dd = f[p[1] * W + p[0]]
                if dd < 10 ** 8:
                    if dd > last: back = True
                    last = dd
            ex = max(0, rounds - walk - hold)
            out[(ty, 'legs')] += 1; out[(ty, 'rounds')] += rounds; out[(ty, 'walk')] += walk; out[(ty, 'hold')] += hold
            out[(ty, 'excess')] += ex; out[(ty, 'excess-back' if back else 'excess-fwd')] += ex
            out[('all', 'legs')] += 1; out[('all', 'rounds')] += rounds; out[('all', 'walk')] += walk; out[('all', 'hold')] += hold
            out[('all', 'excess')] += ex; out[('all', 'excess-back' if back else 'excess-fwd')] += ex
            b = min(walk // 5 * 5, 40)
            out[('bucket', b, 'n')] += 1; out[('bucket', b, 'ex')] += ex; out[('bucket', b, 'walk')] += walk
            prev = x
    out[('all', 'champ_rounds')] += sum(1 for c in ch.values() for i, r in enumerate(rr) if r <= END)
    return out


if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(A + '/*/meta.json')]
    tot = collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, ds, chunksize=8): tot.update(o)
    T = tot[('all', 'champ_rounds')]
    print('champion-rounds', T)
    for ty in ['all', 'Prism', 'Vesper Vale', 'Cassi', 'Issac', 'Willow', 'Ryth', 'Vendetta', 'Marcella', 'Varg']:
        n = tot[(ty, 'legs')]
        if not n: continue
        print('%-12s legs %6d  rounds/leg %.1f walk/leg %.1f hold/leg %.1f excess/leg %.1f (back %.1f fwd %.1f)  excess %.1f%% of all champion time' % (
            ty, n, tot[(ty, 'rounds')] / n, tot[(ty, 'walk')] / n, tot[(ty, 'hold')] / n, tot[(ty, 'excess')] / n,
            tot[(ty, 'excess-back')] / n, tot[(ty, 'excess-fwd')] / n, 100 * tot[(ty, 'excess')] / T))
    for b in range(0, 45, 5):
        n = tot[('bucket', b, 'n')]
        if n: print('walk %2d-%2d legs %6d excess/leg %.1f' % (b, b + 4, n, tot[('bucket', b, 'ex')] / n))
