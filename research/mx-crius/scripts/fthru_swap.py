"""Crossing paths from FT traces: at each new solo pick (mode S or K) by a champion, for each ally whose latest FT pick
(within 2 rounds) is another solo pick, the static walk saved if the two swapped targets (BFS to each group's tiles).
Reports picks, those with a swap saving >= 3 / >= 6 steps, and the total saved steps a game (each pair counted once,
at the later pick). usage: py fthru_swap.py BATCH_DIR EXTRACT [END]"""
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
    fields = {}
    def steps(g, p):
        if g not in fields:
            tiles = [tuple(t) for t in mp['groups'][g]['tiles']]
            for t in tiles: block[t[1] * W + t[0]] = False
            fields[g] = bfs(W, H, block, tiles)
        v = fields[g][p[1] * W + p[0]]
        return v if v < 10 ** 8 else None
    txt = zipfile.ZipFile(path).read('team-%s.stdout' % 'ab'[team]).decode(errors='replace')
    last = {}  # champion -> (round, pos, g, mode)
    out = collections.Counter()
    for line in txt.splitlines():
        mt = FT.match(line)
        if not mt: continue
        r = int(mt.group(1))
        if r > END: break
        h = int(mt.group(2)); p = (int(mt.group(3)), int(mt.group(4))); g = int(mt.group(5)); mode = mt.group(6)
        prev = last.get(h)
        last[h] = (r, p, g, mode)
        if g < 0 or mode not in 'SK' or (prev and prev[2] == g): continue
        out['picks'] += 1
        best = 0
        for o, (r2, p2, g2, m2) in last.items():
            if o == h or r - r2 > 2 or g2 < 0 or g2 == g or m2 not in "SK" or (os.environ.get("NEAR") and max(abs(p[0]-p2[0]), abs(p[1]-p2[1])) > 8): continue
            a, b, c, e = steps(g, p), steps(g2, p2), steps(g2, p), steps(g, p2)
            if None in (a, b, c, e): continue
            best = max(best, (a + b) - (c + e))
        if best >= 3: out['save3'] += 1
        if best >= 6: out['save6'] += 1
        out['saved'] += best
    return out


if __name__ == '__main__':
    ps = sorted(glob.glob(B + '/*.repl26a'))
    tot = collections.Counter(); n = 0
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, ps, chunksize=4):
            if o: tot.update(o); n += 1
    print('games', n, 'solo picks %.1f a game' % (tot['picks'] / n), 'swap saving >=3: %.1f%%  >=6: %.1f%%' % (100 * tot['save3'] / tot['picks'], 100 * tot['save6'] / tot['picks']),
          'steps saved a game (best partner per pick) %.1f' % (tot['saved'] / n))
