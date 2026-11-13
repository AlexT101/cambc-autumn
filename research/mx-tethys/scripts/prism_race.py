"""Prism Focus race: at round R (default 200), the two Prisms' Focus ratio, bag and health; which Prism dies first, and
who wins the game. Also the first-death split when neither Prism died by R.

    py research/mx-tethys/scripts/prism_race.py ANALYSIS_ROOT BATCH_NAME [ROUND]
"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
RR = int(sys.argv[3]) if len(sys.argv) > 3 else 200


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    pr = {team[i]: i for i in names if names[i] == 'Prism'}
    if len(pr) != 2: return None
    rix = {r: i for i, r in enumerate(R['round'])}
    i = rix.get(RR)
    if i is None: return None
    C = {c['id']: c for c in R['champions']}
    if any(e['k'] == 'death' and e['v'] in pr.values() and e['r'] <= RR for e in ev): return None
    f = [C[pr[t]]['foc'][i] or 0 for t in (0, 1)]
    first = next((team[e['v']] for e in ev if e['k'] == 'death' and e['v'] in pr.values()), None)
    return {'f': f, 'first': first, 'winner': m['result']['winner']}


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]
    dirs = [dd for dd in sorted(root.iterdir()) if (dd / 'meta.json').exists() and bname in (json.loads((dd / 'meta.json').read_text()).get('source') or '')]
    rows = []
    with ProcessPoolExecutor(40) as ex:
        for x in ex.map(one, dirs, chunksize=4):
            if x: rows.append(x)
    print(f'games with both Prisms alive at r{RR}: {len(rows)}')
    b = defaultdict(lambda: [0, 0, 0, 0])
    for x in rows:
        hi = 0 if x['f'][0] >= x['f'][1] else 1
        r = x['f'][hi] / max(1, x['f'][1 - hi])
        k = '1.0-1.1' if r < 1.1 else '1.1-1.3' if r < 1.3 else '1.3-1.6' if r < 1.6 else '1.6+'
        b[k][0] += 1
        b[k][1] += x['first'] == 1 - hi
        b[k][2] += x['first'] == hi
        b[k][3] += x['winner'] == hi
    for k in sorted(b):
        n, lo_dies, hi_dies, hi_wins = b[k]
        print(f'Focus ratio {k}: {n} games; first Prism death: lower-Focus {lo_dies / n * 100:.0f}%, higher {hi_dies / n * 100:.0f}%, none {(n - lo_dies - hi_dies) / n * 100:.0f}%; higher-Focus team wins {hi_wins / n * 100:.0f}%')


if __name__ == '__main__':
    main()
