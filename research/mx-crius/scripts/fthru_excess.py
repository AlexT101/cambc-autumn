"""Where leg excess goes (fthru_legs' legs, with FT traces): each round of a camp-to-camp leg is classed as
fwd (the BFS walk to the next job's hit tile fell), hold (on another group's tile), and otherwise by the turn's
FT line: none (another branch ran: crew, retreat, shop, bank...), other-target (farm aimed elsewhere), same-target
(farm aimed at the next job but did not close in: blocked, waiting, a detour). Rounds the walk fell count as fwd
whatever the target. usage: py fthru_excess.py BATCH_DIR EXTRACT [END]"""
import json, gzip, glob, os, sys, collections, zipfile, re
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from fthru_common import bfs
B = sys.argv[1]; A = sys.argv[2]; END = int(sys.argv[3]) if len(sys.argv) > 3 else 600
FT = re.compile(r'^FT (\d+) (\d+) (-?\d+),(-?\d+) g(-?\d+) (\S) v(\S+) s(-?\d+)')
src_of = {}
for p in glob.glob(A + '/*/meta.json'):
    m = json.load(open(p))
    for s in m['sources']:
        if '-cand' in s['source']: src_of[os.path.basename(s['source'])] = os.path.dirname(p)


def one(path):
    d = src_of.get(os.path.basename(path))
    if not d: return None
    m = json.load(open(d + '/meta.json'))
    mp = json.load(open(os.path.join(d, m['mapFile'])))
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
    marks = collections.defaultdict(list)
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > END: break
        a = e.get('a')
        if a not in ch: continue
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'): marks[a].append((e['r'], 'hit', cg.get(e['cdmg'][0][0]), tuple(e['f'])))
        elif k in ('recall_end', 'tribute_start', 'death', 'teleport_start'): marks[a].append((e['r'], 'break', None, None))
    txt = zipfile.ZipFile(path).read('team-%s.stdout' % 'ab'[team]).decode(errors='replace')
    ft = {}
    for line in txt.splitlines():
        mt = FT.match(line)
        if mt: ft[(int(mt.group(2)), int(mt.group(1)))] = (int(mt.group(5)), mt.group(6))
    out = collections.Counter(); cache = {}
    for a, mk in marks.items():
        c = ch[a]; prev = None
        for x in mk:
            if x[1] == 'break': prev = None; continue
            if prev is None or prev[2] == x[2]: prev = x; continue
            r0, r1, t, g = prev[0], x[0], x[3], x[2]
            if t not in cache: cache[t] = bfs(W, H, block, [t])
            f = cache[t]
            last = f[prev[3][1] * W + prev[3][0]]
            if last >= 10 ** 8: prev = x; continue
            for r in range(r0 + 1, r1):  # rounds before the hit round
                i = ri.get(r)
                if i is None or c['x'][i] is None: continue
                p = (c['x'][i], c['y'][i]); dd = f[p[1] * W + p[0]]
                tg = tile_group.get(p)
                if dd < last: k = 'fwd'
                elif tg is not None and tg != g: k = 'hold'
                else:
                    q = ft.get((a, r))
                    k = 'none' if q is None else 'same-target' if q[0] == g else 'other-target:' + q[1]
                    if q is not None and q[0] != g: out['other-target'] += 1
                out[k] += 1
                if dd < 10 ** 8: last = dd
            prev = x
    out['champ_rounds'] = sum(1 for c in ch.values() for r in rr if r <= END)
    return out


if __name__ == '__main__':
    ps = sorted(glob.glob(B + '/*.repl26a'))
    tot = collections.Counter(); n = 0
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, ps, chunksize=4):
            if o: tot.update(o); n += 1
    T = tot.pop('champ_rounds')
    print('games', n, 'champion-rounds', T)
    for k, v in sorted(tot.items(), key=lambda kv: -kv[1]): print('  %-18s %8d  %.2f%% of champion time' % (k, v, 100 * v / T))
