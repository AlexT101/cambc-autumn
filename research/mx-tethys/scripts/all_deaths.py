"""All champion-killed deaths by victim type (mirror): outnumbered within 8 five rounds before, allies within 16 that
could have matched, killer type, and the hazard of being outnumbered (death within 15) per type.

    py research/mx-tethys/scripts/all_deaths.py ANALYSIS_ROOT BATCH_NAME [MAX]
"""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    rix = {r: i for i, r in enumerate(R['round'])}
    C = R['champions']
    rows = []
    for e in ev:
        if e['k'] != 'death' or e.get('by') not in names: continue
        v = e['v']; t = team[v]
        i = rix.get(e['r'] - 5)
        if i is None: continue
        cv = next(c for c in C if c['id'] == v)
        if not cv['alive'][i] or cv['x'][i] is None: continue
        p = (cv['x'][i], cv['y'][i])
        na = ne = a16 = 0
        for c in C:
            if c['id'] == v or not c['alive'][i] or c['x'][i] is None: continue
            d = cheb(p, (c['x'][i], c['y'][i]))
            if team[c['id']] == t:
                na += d <= 8; a16 += d <= 16
            else:
                ne += d <= 8
        rows.append({'type': names[v], 'killer': names[e['by']], 'r': e['r'], 'out': ne > na + 1, 'match': a16 + 1 >= ne,
                     'won': m['result']['winner'] == t, 'gems': e.get('gems') or 0})
    return rows


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    dirs = []
    for dd in sorted(root.iterdir()):
        mf = dd / 'meta.json'
        if mf.exists() and bname in (json.loads(mf.read_text()).get('source') or ''): dirs.append(dd)
        if len(dirs) >= mx: break
    rows = []; g = 0
    with ProcessPoolExecutor(40) as ex:
        for x in ex.map(one, dirs, chunksize=4):
            if x is not None: g += 1; rows += x
    print('games', g, 'champion-killed deaths', len(rows), f'({len(rows) / g:.2f} a game)')
    by = defaultdict(list)
    for x in rows: by[x['type']].append(x)
    print('type  deaths/game  outnumbered@-5  matchable(allies<=16+1>=enemies<=8 | out)  gems lost/death  top killers')
    for ty, s in sorted(by.items(), key=lambda kv: -len(kv[1])):
        out = [x for x in s if x['out']]
        kc = Counter(x['killer'] for x in s).most_common(3)
        print(f"{ty:14s} {len(s) / g:5.2f}  {len(out) / len(s) * 100:4.0f}%  {sum(x['match'] for x in out) / max(1, len(out)) * 100:4.0f}%  "
              f"{sum(x['gems'] for x in s) / len(s):6.1f}  {kc}")
    out = [x for x in rows if x['out']]
    print(f"all: outnumbered 5 rounds before {len(out) / len(rows) * 100:.0f}%, of those matchable {sum(x['match'] for x in out) / max(1, len(out)) * 100:.0f}%")


if __name__ == '__main__':
    main()
