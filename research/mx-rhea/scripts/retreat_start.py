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
        if e['k'] != 'death' or e.get('linked') or 'by' not in e or e['v'] not in idx: continue
        cv = ch[idx[e['v']]]
        i1 = rix.get(e['r'] - 1)
        if i1 is None: continue
        team = cv['team']; other = 1 - team
        ender = any(c['team'] == other and c['alive'][i1] and R['gems'][other][i1] + c['gems'][i1] >= 1000 for c in ch)
        mine = any(c['team'] == team and c['alive'][i1] and R['gems'][team][i1] + c['gems'][i1] >= 1000 for c in ch)
        phase = 'enemy-ender' if ender else ('our-ender' if mine else ('early' if e['r'] < 400 else 'mid'))
        if phase not in ('early', 'mid'): continue
        k = e['by']
        if k not in idx: continue
        ck = ch[idx[k]]
        # rounds of continuous R before death and the distance at the round before R began
        b = 1
        while b < 30 and D.get((e['r'] - b, e['v'])) == 'R': b += 1
        nR = b - 1
        i0 = rix.get(e['r'] - b)
        dist0 = None
        if i0 is not None and cv['x'][i0] is not None and ck['x'][i0] is not None:
            dist0 = cheb((cv['x'][i0], cv['y'][i0]), (ck['x'][i0], ck['y'][i0]))
        hp0 = None if i0 is None else round(cv['hp'][i0] / max(1, cv['maxHp'][i0]), 1)
        before = D.get((e['r'] - b, e['v']), '?')
        out.append((names.get(e['v'], '?'), nR, dist0, hp0, before, names.get(k, '?')))
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
            for v, nR, d0, hp0, before, k in o:
                n += 1
                if nR == 0: B['noR:' + before] += 1; continue
                last[min(nR, 10)] += 1; chan[d0] += 1; B['before:' + before] += 1
                if hp0 is not None: B['hp0:%s' % hp0] += 1
    print('early/mid deaths to champions', n)
    print('deaths with no retreat in the last turn, by last branch:', sorted(((k, v) for k, v in B.items() if k.startswith('noR')), key=lambda x: -x[1])[:8])
    print('R run length before death (capped 10):', sorted(last.items()))
    print('killer distance the round before R began:', sorted(chan.items(), key=lambda x: (x[0] is None, x[0]))[:14])
    print('branch before R:', sorted(((k, v) for k, v in B.items() if k.startswith('before')), key=lambda x: -x[1])[:8])
    print('hp frac before R:', sorted(((k, v) for k, v in B.items() if k.startswith('hp0')), key=lambda x: x[0]))

if __name__ == '__main__':
    main()
