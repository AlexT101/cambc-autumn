"""Line F (stand keep): per game, CAND side vs REF side: STANDKEEP lines (CAND's stdout, debug builds), deaths by
victim type (Prism, Cassi/Issac counted once a pair death, others), champion kills, gems taken by kills, wins.

    py research/mx-tethys/scripts/stand_counts.py ANALYSIS_ROOT BATCH_NAME CAND_TEAM_NAME
"""
import gzip, json, re, sys, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

WT = Path('/home/ubuntu/wt/mx-tethys')
KEEP = re.compile(rb'STANDKEEP (\d+) (\d+)')


def one(args):
    dd, bname, cand = args
    try:
        m = json.loads((dd / 'meta.json').read_text())
        if bname not in (m.get('source') or ''): return None
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = [t['name'] for t in m['teams']]
    if cand not in names: return None
    ct = names.index(cand)
    side = lambda t: 'C' if t == ct else 'R'
    team = {c['id']: c['team'] for c in m['champions']}
    name = {c['id']: c['name'] for c in m['champions']}
    out = Counter()
    out['games'] = 1
    out['win_' + side(m['result']['winner'])] += 1
    for e in ev:
        if e['k'] != 'death' or e['v'] not in team: continue
        if e.get('linked') is not None and name[e['v']] in ('Cassi', 'Issac') and e['v'] > e['linked']: continue
        s = side(team[e['v']])
        n = name[e['v']]
        kind = 'prism' if n == 'Prism' else 'pair' if n in ('Cassi', 'Issac') else 'other'
        out[f'death_{kind}_{s}'] += 1
        if e.get('by') is not None and e['by'] in team:
            out['kills_' + side(team[e['by']])] += 1
            out['killgems_' + side(team[e['by']])] += e.get('gemsTo', 0) or 0
            if kind == 'prism': out['prismgems_lost_' + s] += e.get('gemsTo', 0) or 0
    try:
        z = zipfile.ZipFile(WT / m['source'])
        data = z.read('team-a.stdout' if ct == 0 else 'team-b.stdout')
        out['keep_lines'] += len(set(KEEP.findall(data)))
        out['keep_games'] += 1 if KEEP.search(data) else 0
    except Exception:
        pass
    return out


if __name__ == '__main__':
    root, bname, cand = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    tot = Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one, [(d, bname, cand) for d in root.iterdir()], chunksize=64):
            if r: tot.update(r)
    g = tot['games']
    print('games', g)
    for k in sorted(tot):
        if k != 'games': print(f'  {k:22s} {tot[k]:7d}  {tot[k] / max(1, g):.3f}/game')
