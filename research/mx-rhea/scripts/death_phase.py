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
        br = D.get((e['r'] - 1, e['v']), '?')
        out.append((phase + ':' + names.get(e['v'], '?'), br, e.get('gems', 0)))
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
            for key, br, gems in o:
                n += 1; B[(key.split(':')[0], br)] += 1; last[key.split(':')[0]] += 1; chan[(key.split(':')[0], key.split(':')[1])] += 1
    print('deaths to champions', n, 'by phase', last.most_common())
    for ph in ('early', 'mid', 'our-ender', 'enemy-ender'):
        row = sorted(((b, v) for (p_, b), v in B.items() if p_ == ph), key=lambda x: -x[1])
        print(ph, ' '.join(f'{b}:{v}' for b, v in row[:10]))
        print('   victims', ' '.join(f'{t}:{v}' for (p_, t), v in sorted(chan.items(), key=lambda x: -x[1]) if p_ == ph)[:300])

if __name__ == '__main__':
    main()
