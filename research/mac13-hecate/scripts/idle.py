# idle.py BATCH EXTRACT: alive, non-channelling turns with no move/attack/cast, by branch (debug D lines)
import sys, re, json, gzip, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
AN = Path(sys.argv[2]); INDEX = {}
for dd in AN.iterdir():
    if (dd/'meta.json').exists(): INDEX[Path(json.loads((dd/'meta.json').read_text())['source']).name] = dd
def one(f):
    d = INDEX.get(f.name)
    if d is None: return None
    z = zipfile.ZipFile(f)
    R = json.load(gzip.open(d/'rounds.json.gz')); r0 = R['round'][0]; ch = {c['id']: c for c in R['champions']}
    act = set()
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e.get('k') in ('move', 'attack', 'cast', 'tribute_start', 'recall_start', 'lock_place') and 'a' in e: act.add((e['a'], e['r']))
    tot = collections.Counter(); idle = collections.Counter()
    for n in z.namelist():
        if not n.endswith('.stdout'): continue
        for m in D_RE.finditer(z.read(n)):
            r, i, b = int(m.group(1)), int(m.group(2)), m.group(3).decode()
            c = ch.get(i); k = r - r0
            if c is None or k < 0 or k >= len(c['x']) or not c['alive'][k]: continue
            if c['chan'][k]: continue
            tot[b] += 1
            if (i, r) not in act: idle[b] += 1
    return tot, idle
if __name__ == '__main__':
    fs = sorted(Path(sys.argv[1]).glob('*.repl26a')); T = collections.Counter(); I = collections.Counter()
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, fs, chunksize=4):
            if o: T.update(o[0]); I.update(o[1])
    s = sum(T.values()); si = sum(I.values())
    print('turns', s, 'idle', si, round(si / s, 3))
    for b, n in T.most_common(): print(b, n, 'share', round(n / s, 3), 'idle', I[b], round(I[b] / n, 2), 'of all idle', round(I[b] / si, 3))
