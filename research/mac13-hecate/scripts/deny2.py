"""For enemy holds with one of ours within 4 in the last 6 rounds: our nearest champion's D-line branches then, and its bag."""
import sys, re, json, gzip, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
AN = Path(sys.argv[2])
INDEX = {Path(json.loads((dd/'meta.json').read_text())['source']).name: dd for dd in AN.iterdir() if (dd/'meta.json').exists()}
def one(f):
    f = Path(f); d = INDEX.get(f.name)
    if d is None: return None
    z = zipfile.ZipFile(f)
    br = {}
    for side in ('team-a.stdout', 'team-b.stdout'):
        for m in D_RE.finditer(z.read(side)): br[(int(m[2]), int(m[1]))] = m[3].decode()
    meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    mp = json.loads((d/meta['mapFile']).read_text()); gt = {g['id']: g['tiles'] for g in mp['groups']}
    name = {c['id']: c['name'] for c in meta['champions']}; r0 = R['round'][0]; st = collections.Counter()
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e = json.loads(l)
        if e.get('k') != 'capture': continue
        g, t, r = e['g'], e['team'], e['r']
        best = (99, None, None)
        for c in R['champions']:
            if c['team'] == t: continue
            for rr in range(r - 6, r):
                i = rr - r0
                if i < 0 or not c['alive'][i] or c['x'][i] is None: continue
                dd = min(max(abs(c['x'][i]-x), abs(c['y'][i]-y)) for x, y in gt[g])
                if dd < best[0]: best = (dd, c, rr)
        if best[0] > 4: continue
        dd, c, rr = best
        b = br.get((c['id'], rr), '?'); gems = c['gems'][rr - r0]
        st['n'] += 1; st['br_' + b] += 1; st['bag>0'] += gems > 0; st['bag>=20'] += gems >= 20
        st['who_' + name[c['id']]] += 1
    return st
if __name__ == '__main__':
    files = sorted(Path(sys.argv[1]).glob('*.repl26a'))
    tot = collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, files, chunksize=8):
            if o: tot.update(o)
    for k, v in tot.most_common(): print(k, v, round(v / tot['n'], 3))
