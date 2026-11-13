# pduel2.py BATCH_DIR EXTRACT_DIR: Prism-on-Prism kills: when the victim first saw the killer, the Focus ratio then, the
# victim's branches from first sight to death (debug D lines)
import sys, re, json, gzip, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
AN = Path(sys.argv[2]); INDEX = {}
for dd in AN.iterdir():
    if (dd/'meta.json').exists(): INDEX[Path(json.loads((dd/'meta.json').read_text())['source']).name] = dd
def one(f):
    f = Path(f); d = INDEX.get(f.name)
    if d is None: return None
    try: z = zipfile.ZipFile(f)
    except Exception: return None
    meta = json.loads((d/'meta.json').read_text()); name = {c['id']: c['name'] for c in meta['champions']}
    R = json.load(gzip.open(d/'rounds.json.gz')); r0 = R['round'][0]; ch = {c['id']: c for c in R['champions']}
    br = {}
    for n in z.namelist():
        if n.endswith('.stdout'):
            for m in D_RE.finditer(z.read(n)): br[(int(m.group(2)), int(m.group(1)))] = m.group(3).decode()
    out = []
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e.get('k') != 'death' or name.get(e['v']) != 'Prism' or name.get(e.get('by')) != 'Prism': continue
        v, k = e['v'], e['by']; i = e['r'] - r0; V, K = ch[v], ch[k]
        first = None
        for j in range(max(0, i - 40), i + 1):
            if k in V['seenBy'][j] or v in K['seenBy'][j]: pass
            if V['x'][j] is not None and K['x'][j] is not None and (k in ch[v].get('sees', [[]]*0) if False else True):
                # victim sees killer: killer seen by victim's team member == victim
                if v in K['seenBy'][j]:
                    first = j; break
        if first is None: continue
        dd = max(abs(V['x'][first]-K['x'][first]), abs(V['y'][first]-K['y'][first]))
        ratio = K['foc'][first] / max(1, V['foc'][first])
        bs = ''.join(br.get((v, r0 + j), '?') for j in range(first, i + 1))
        out.append(dict(gems=e['gems'], lead=i - first, d0=dd, ratio=ratio, br=bs))
    return out
if __name__ == '__main__':
    fs = sorted(Path(sys.argv[1]).glob('*.repl26a')); rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, fs, chunksize=4):
            if o: rows += o
    print('kills with a first sighting', len(rows))
    big = [x for x in rows if x['gems'] >= 50]
    for lab, s in (('victim smaller (ratio>1.1)', [x for x in big if x['ratio'] > 1.1]), ('even', [x for x in big if 0.9 <= x['ratio'] <= 1.1]), ('victim bigger', [x for x in big if x['ratio'] < 0.9])):
        if not s: continue
        import statistics as S
        c = collections.Counter(ch for x in s for ch in x['br'])
        tot = sum(c.values())
        print(lab, len(s), 'gems med', S.median(x['gems'] for x in s), 'lead med', S.median(x['lead'] for x in s), 'd0 med', S.median(x['d0'] for x in s),
              'branches', {a: round(b/tot, 2) for a, b in c.most_common(8)})
    for x in big[:25]: print(round(x['ratio'], 2), x['gems'], x['lead'], x['d0'], x['br'])
