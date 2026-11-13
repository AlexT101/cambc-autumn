"""P(win | lead in score+carried) by round, mirror."""
import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
RS = (150, 250, 350, 450, 600, 800)
def g(d):
    meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    w = meta['result']['winner']; ch = R['champions']; n = len(R['round'])
    out = []
    for r in RS:
        if r >= n: continue
        tot = [R['gems'][t][r] + sum(c['gems'][r] for c in ch if int(c['team']) == t and c['alive'][r]) for t in (0, 1)]
        out.append((r, tot[0]-tot[1], w == 0))
    return out
if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: E = [x for r in ex.map(g, dirs, chunksize=8) for x in r]
    bins = [(-9999, -300), (-300, -150), (-150, -75), (-75, -25), (-25, 25), (25, 75), (75, 150), (150, 300), (300, 9999)]
    for r in RS:
        row = []
        for lo, hi in bins:
            S = [x for x in E if x[0] == r and lo <= x[1] < hi]
            row.append(f'{lo}..{hi}:{len(S)}:{sum(x[2] for x in S)/len(S):.2f}' if len(S) >= 20 else f'{lo}..{hi}:-')
        print(r, ' '.join(row))
