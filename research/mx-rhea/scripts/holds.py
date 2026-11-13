"""Capture holds: rounds from hold start to payout, holders, and whether the holder hit camps during the hold.
Per group type class. Usage: py holds.py DIR"""
import gzip, json, sys
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        mp = json.loads((d/meta['mapFile']).resolve().read_text())
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = {c['id']: c['name'] for c in meta['champions']}
    gtypes = {g['id']: '+'.join(sorted(set(g['types']))) for g in mp['groups']}
    hits = defaultdict(set)
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'camp' in e: hits[e['a']].add(e['r'])
    start = {}; clear = {}
    out = []
    for e in ev:
        k = e['k']
        if k == 'group_clear': clear[e['g']] = e['r']
        elif k == 'capture_hold': start.setdefault((e['g'], e['team']), e['r'])
        elif k == 'capture_reset': start.pop((e['g'], e['team']), None)
        elif k == 'capture':
            r0 = start.pop((e['g'], e['team']), None)
            c0 = clear.pop(e['g'], None)
            for cid, gems, gold in e['shares']:
                busy = sum(1 for r in range(r0, e['r']) if r in hits[cid]) if r0 else 0
                out.append((gtypes.get(e['g'], '?'), names.get(cid, '?'), (e['r'] - r0) if r0 else None,
                            (r0 - c0) if (r0 and c0) else None, busy, gems))
    return out

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    T = defaultdict(lambda: [0, 0, 0, 0, 0, 0]); NT = defaultdict(lambda: [0, 0, 0])
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if not o: continue
            for gt, n, hold, wait, busy, gems in o:
                t = T[gt]; t[0] += 1; t[1] += hold or 0; t[2] += busy; t[3] += gems; t[4] += (wait or 0); t[5] += 1 if wait is not None else 0
                nt = NT[n]; nt[0] += 1; nt[1] += hold or 0; nt[2] += busy
    print('group type: captures, mean hold rounds, hold rounds with a camp hit, gems/capture, mean clear->hold gap')
    for k, t in sorted(T.items(), key=lambda x: -x[1][0])[:14]:
        print(f'{k:40s} {t[0]:6d} hold {t[1]/t[0]:4.1f} busy {t[2]/t[0]:4.2f} gems {t[3]/t[0]:5.1f} gap {t[4]/max(1,t[5]):4.1f}')
    print('by holder: captures, mean hold, busy')
    for k, t in sorted(NT.items(), key=lambda x: -x[1][0]):
        print(f'{k:14s} {t[0]:6d} hold {t[1]/t[0]:4.1f} busy {t[2]/t[0]:4.2f}')

if __name__ == '__main__':
    main()
