"""Winning bags: the first round each team has a champion whose carried gems plus its team's tributed gems reach 1000,
who held it, and how it resolved (won without losing it, holder died with it, lost to the other side's tribute).
Usage: py winbag.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def game(d):
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
    except Exception:
        return None
    names = {c['id']: c['name'] for c in meta['champions']}
    w = meta['result']['winner']; n = meta['result']['rounds']
    out = []
    first = {}
    for t in (0, 1):
        sc = R['gems'][t]
        for c in R['champions']:
            if c['team'] != t: continue
            for i, g in enumerate(c['gems']):
                if g is not None and c['alive'][i] and g + sc[i] >= 1000:
                    if t not in first or i < first[t][0]: first[t] = (i, c['id'])
                    break
    for t, (i, cid) in first.items():
        c = next(x for x in R['champions'] if x['id'] == cid)
        # held until: tributed (gems drop while alive), died, or game end
        died = None
        for j in range(i, len(c['gems'])):
            if not c['alive'][j]: died = j; break
            if c['gems'][j] is not None and c['gems'][j] + R['gems'][t][j] < 1000: break
        other = first.get(1 - t)
        both = other is not None and other[0] <= (died if died is not None else n)
        out.append(dict(team=t, r=i + 1, holder=names[cid], won=w == t, died=died is not None, both=both,
                        other_first=other is not None and other[0] < i, dur=(died if died is not None else n) - i, n=n))
    return out


if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(game, dirs, chunksize=8):
            if o: rows += o
    ng = len(dirs)
    print(f'{ng} games; team-games with a winning bag: {len(rows)}')
    games_with = Counter()
    print('holder won:', sum(r['won'] for r in rows), 'of', len(rows))
    print('holder died with it (first holder):', sum(r['died'] for r in rows), '; of those won anyway', sum(r['won'] for r in rows if r['died']))
    print('both sides held one at once:', sum(r['both'] for r in rows))
    for k in ('died', 'both', 'other_first'):
        for v in (True, False):
            s = [r for r in rows if r[k] == v]
            if s: print(f'  {k}={v}: {len(s)} holder won {sum(r["won"] for r in s)/len(s):.0%}')
    print('holders:', Counter(r['holder'] for r in rows).most_common(8))
    print('holder died, by holder:', Counter(r['holder'] for r in rows if r['died']).most_common(8))
    rs = sorted(r['r'] for r in rows); print('first winning-bag round p25/50/75', [rs[int(q*(len(rs)-1))] for q in (.25, .5, .75)])
    ds = sorted(r['dur'] for r in rows if not r['died']); print('rounds held to tribute/end p25/50/75', [ds[int(q*(len(ds)-1))] for q in (.25, .5, .75)])
