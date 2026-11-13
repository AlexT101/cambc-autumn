# pduel3.py BATCH EXTRACT: rounds before a Prism-on-Prism kill (bag 50+) with the killer >1.1x the victim's Focus:
# victim's branch by distance and whether it saw the killer
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
    meta = json.loads((d/'meta.json').read_text()); name = {c['id']: c['name'] for c in meta['champions']}
    R = json.load(gzip.open(d/'rounds.json.gz')); r0 = R['round'][0]; ch = {c['id']: c for c in R['champions']}
    br = {}
    for n in z.namelist():
        if n.endswith('.stdout'):
            for m in D_RE.finditer(z.read(n)): br[(int(m.group(2)), int(m.group(1)))] = m.group(3).decode()
    rows = []
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e.get('k') != 'death' or name.get(e['v']) != 'Prism' or name.get(e.get('by')) != 'Prism' or e['gems'] < 50: continue
        v, k = e['v'], e['by']; i = e['r'] - r0; V, K = ch[v], ch[k]
        for j in range(max(0, i - 30), i + 1):
            if V['x'][j] is None or K['x'][j] is None: continue
            if K['foc'][j] / max(1, V['foc'][j]) <= 1.1: continue
            dd = max(abs(V['x'][j]-K['x'][j]), abs(V['y'][j]-K['y'][j]))
            rows.append((i - j, dd, v in K['seenBy'][j], br.get((v, r0 + j), '?')))
    return rows
if __name__ == '__main__':
    fs = sorted(Path(sys.argv[1]).glob('*.repl26a')); rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, fs, chunksize=4):
            if o: rows += o
    for lo, hi in ((0, 5), (5, 7), (7, 9), (9, 12), (12, 99)):
        s = [r for r in rows if lo <= r[1] < hi]
        c = collections.Counter(r[3] for r in s); seen = sum(r[2] for r in s)
        print(lo, hi, len(s), 'seen', round(seen/len(s), 2), {a: round(b/len(s), 2) for a, b in c.most_common(5)})
    s = [r for r in rows if r[3] == 'F' and 5 <= r[1] < 12]
    print('F turns at 5-11: killer seen', sum(r[2] for r in s), 'unseen', sum(not r[2] for r in s))
