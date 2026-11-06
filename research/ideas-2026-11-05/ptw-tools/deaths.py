"""Deaths by side: by round bucket, gems carried, killed by champion or camp. python3 deaths.py GAMES.jsonl"""
import json, sys, gzip, collections
from concurrent.futures import ProcessPoolExecutor
def game(g):
    m = json.load(open(g['dir'] + '/meta.json')); team = {c['id']: c['team'] for c in m['champions']}
    out = []
    for l in gzip.open(g['dir'] + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] != 'death': continue
        out.append((team[e['v']] == g['us'], e['r'], e.get('gems', 0), e.get('by') in team, m['result']['winner'] == g['us']))
    return out
if __name__ == '__main__':
    gs = [json.loads(l) for l in open(sys.argv[1])]
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(game, gs, chunksize=16): rows += o
    n = len(gs)
    for side in (True, False):
        xs = [x for x in rows if x[0] == side]
        b = collections.Counter(min(x[1] // 250, 4) for x in xs)
        print(f"{'cand' if side else 'ref '}: deaths/game {len(xs)/n:.2f} (by champion {sum(x[3] for x in xs)/n:.2f}); gems lost/game {sum(x[2] for x in xs)/n:.1f}; by round "
              + ' '.join(f"{k*250}-: {b[k]/n:.2f}" for k in sorted(b)) + f"; in cand's wins {sum(1 for x in xs if x[4])/n:.2f}, losses {sum(1 for x in xs if not x[4])/n:.2f}")
