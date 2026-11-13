"""Deaths on branch E per game, by bot (0 = CAND in an ab batch): all deaths to champions or camps, those whose victim
was on E in its last 10 turns (and of those, 200+ gems), and those whose last D line was E. Also the URG wait/go lines
on a debug batch. Usage: py edeaths.py ANALYSIS_DIR BATCH"""
import gzip, json, sys, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path('/home/ubuntu/wt/mx-rhea')


def game(args):
    d, src = args
    try:
        meta = json.loads((d/'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(src)
    except Exception:
        return None
    team = {c['id']: c['team'] for c in meta['champions']}
    bot = {0: meta['teams'][0]['bot'], 1: meta['teams'][1]['bot']}
    D = {}; urg = Counter()
    for side, t in (('a', 0), ('b', 1)):
        try: lines = z.read(f'team-{side}.stdout').decode(errors='replace').splitlines()
        except KeyError: continue
        for l in lines:
            l = l.lstrip('\x00')
            if l.startswith('D '):
                p = l.split()
                if len(p) >= 4: D[(int(p[1]), int(p[2]))] = p[3]
            elif l.startswith('URG '):
                urg[(bot[t], l.split()[-1])] += 1
    c = Counter()
    for e in ev:
        if e['k'] != 'death': continue
        v = e['v']; b = bot[team[v]]
        c[(b, 'deaths')] += 1
        last10 = [D.get((e['r'] - k, v)) for k in range(0, 11)]
        if 'E' in last10:
            c[(b, 'E10')] += 1
            if e.get('gems', 0) >= 200: c[(b, 'E10_200')] += 1
        prev = next((x for x in last10 if x is not None), None)
        if prev == 'E': c[(b, 'lastE')] += 1
        c[(b, 'Eturns')] += 0
    for (b, t), n in Counter((bot[team[cid]], br) for (r, cid), br in D.items()).items():
        if t == 'E': c[(b, 'Eturns')] += n
    for k, n in urg.items(): c[(k[0], 'urg_' + k[1])] += n
    return c


def main():
    ana, batch = Path(sys.argv[1]), sys.argv[2]
    idx = json.load(open(ana/'index.json'))['games']
    jobs, seen = [], set()
    for g in idx:
        if g['dir'] in seen or batch not in g['source']: continue
        seen.add(g['dir']); jobs.append((ana/g['dir'], ROOT/g['source']))
    tot = Counter(); n = 0
    with ProcessPoolExecutor(32) as ex:
        for c in ex.map(game, jobs, chunksize=4):
            if c is None: continue
            n += 1; tot.update(c)
    print(n, 'games')
    for b in (0, 1):
        row = {k: tot[(b, k)] for k in ('deaths', 'E10', 'E10_200', 'lastE', 'Eturns', 'urg_wait', 'urg_go')}
        print(f'bot {b}:', ' '.join(f'{k} {v} ({v/n:.2f}/g)' for k, v in row.items()))


if __name__ == '__main__':
    main()
