"""Branch letters (D lines) of the victim in its last 4 rounds, for deaths to an enemy Prism that walked in
(distance at the ends of r-1..r-3 strictly decreasing to <= 4). Usage: py approach_branch.py ANA BATCH [Victim]"""
import gzip, json, sys, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
ANA = Path(sys.argv[1]); BATCH = Path(sys.argv[2]); WHO = sys.argv[3] if len(sys.argv) > 3 else 'Cassi'

def game(args):
    d, src = args
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(src)
    except Exception:
        return None
    names = {c['id']: c['name'] for c in meta['champions']}
    ch = R['champions']; idx = {c['id']: i for i, c in enumerate(ch)}
    rix = {r: i for i, r in enumerate(R['round'])}
    D = {}
    for side, team in (('a', 0), ('b', 1)):
        try: lines = z.read(f'team-{side}.stdout').decode(errors='replace').splitlines()
        except KeyError: continue
        for l in lines:
            l = l.lstrip('\x00')
            if l.startswith('D '):
                p = l.split()
                if len(p) >= 4: D[(int(p[1]), int(p[2]))] = p[3]
    out = []
    for e in ev:
        if e['k'] != 'death' or e.get('linked') or names.get(e.get('by')) != 'Prism' or names.get(e['v']) != WHO: continue
        cv, ck = ch[idx[e['v']]], ch[idx[e['by']]]
        ds = []
        for back in range(1, 4):
            i = rix.get(e['r'] - back)
            if i is None or cv['x'][i] is None or ck['x'][i] is None: ds = None; break
            ds.append(cheb((cv['x'][i], cv['y'][i]), (ck['x'][i], ck['y'][i])))
        if not ds or not (ds[0] <= 4 and ds[0] < ds[1] < ds[2]): continue
        br = ''.join(D.get((e['r'] - b, e['v']), '?') for b in (3, 2, 1, 0))
        i1 = rix[e['r'] - 1]
        out.append((br, cv['chan'][i1], cv['gems'][i1]))
    return out

def main():
    idx = json.load(open(ANA/'index.json'))['games']
    jobs = []; seen = set()
    for g in idx:
        if g['dir'] in seen or not g['source'].startswith(str(BATCH)): continue
        seen.add(g['dir']); jobs.append((ANA/g['dir'], Path(g['source'])))
    B = Counter(); last = Counter(); chan = Counter(); n = 0
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, jobs, chunksize=4):
            if not o: continue
            for br, ch_, gems in o:
                n += 1; B[br] += 1; last[br[2]] += 1; chan[ch_] += 1
    print(WHO, 'walk-in deaths', n)
    print('branch at r-1 (its last full turn):', last.most_common())
    print('channel at end of r-1 (0 none, 1 recall, 2 tribute, 3 teleport):', chan.most_common())
    print('branch strings r-3 r-2 r-1 r:', B.most_common(15))

if __name__ == '__main__':
    main()
