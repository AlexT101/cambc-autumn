"""Game classes: Prisms per team, first Prism-on-Prism kill or none, first Prism death by anyone, and win rates.

    python3 gclass.py EXTRACT_DIR
"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def one(d):
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    team = {m['id']: m['team'] for m in meta['champions']}
    pr = {m['id'] for m in meta['champions'] if m['name'] == 'Prism'}
    np = len({team[i] for i in pr})
    w = meta['result']['winner']
    first = None
    for e in ev:
        if e['k'] == 'death' and e['v'] in pr:
            first = e
            break
    if np < 2:
        return ('prisms<2', None, meta['result']['rounds'])
    if first is None:
        return ('no Prism death', None, meta['result']['rounds'])
    by = 'Prism' if first.get('by') in pr else ('camp' if 'camp' in first else 'other')
    return ('first Prism death by ' + by, team[first['v']] != w, first['r'])


if __name__ == '__main__':
    dirs = [str(p.parent) for p in Path(sys.argv[1]).glob('*/meta.json')]
    with ProcessPoolExecutor(16) as ex:
        rs = [r for r in ex.map(one, dirs, chunksize=8) if r]
    c = Counter(r[0] for r in rs)
    wins = Counter(r[0] for r in rs if r[1])
    import statistics as S
    for k, v in c.most_common():
        print(f'{k:32s} {v:5d} ({100 * v / len(rs):4.1f}%)  survivor team wins {100 * wins[k] / v:5.1f}%  median round {S.median(r[2] for r in rs if r[0] == k)}')
