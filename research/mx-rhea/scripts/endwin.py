"""Endgame windows: once a team holds a winning bag (score + one champion's bag >= 1000), how many rounds pass before
it wins, and how many of those rounds had a provably safe window: every enemy (dead: respawn timer then walk from its
spawn; alive: its Chebyshev distance) needs longer to come within 5 of the holder's nearest altar than the holder's walk
plus channel. Usage: py endwin.py ANALYSIS_DIR"""
import gzip, json, sys, statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
REACH = 5

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        mp = json.loads((d/meta['mapFile']).resolve().read_text())
    except Exception:
        return None
    winner = meta['result']['winner']
    ch = R['champions']
    altars = mp['altars']
    if not altars: return None
    sp = mp['spawn']
    centre = [((s['minX']+s['maxX'])/2, (s['minY']+s['maxY'])/2) for s in sp]
    out = []
    for team in (0, 1):
        role = 'W' if team == winner else 'L'
        r1000 = None; safe_rounds = 0; first_safe = None; rounds = 0; holder_types = Counter()
        for i, r in enumerate(R['round']):
            score = R['gems'][team][i]
            best = None
            for c in ch:
                if c['team'] != team or not c['alive'][i] or c['x'][i] is None: continue
                if score + c['gems'][i] >= 1000 and (best is None or c['gems'][i] > best['gems'][i]): best = c
            if best is None:
                continue
            if r1000 is None: r1000 = r
            rounds += 1
            p = (best['x'][i], best['y'][i])
            alt = min(altars, key=lambda a: cheb(a, p))
            walk = max(0, cheb(alt, p) - 1)
            chan = max(1, -(-best['gems'][i] // 10))
            need = walk + chan
            bound = 10**9
            for e in ch:
                if e['team'] == team: continue
                if e['alive'][i] and e['x'][i] is not None:
                    t = max(0, cheb((e['x'][i], e['y'][i]), alt) - REACH)
                else:
                    t = (e['respawn'][i] or 0) + max(0, cheb(centre[e['team']], alt) - REACH)
                bound = min(bound, t)
            if bound >= need:
                safe_rounds += 1
                if first_safe is None: first_safe = r
        if r1000 is not None:
            out.append((role, r1000, rounds, safe_rounds, first_safe, meta['result']['rounds'], team == winner))
    return out

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if o: rows += o
    print('team-games reaching a winning bag:', len(rows))
    for role in 'WL':
        rr = [x for x in rows if x[0] == role]
        if not rr: continue
        lag = [x[5] - x[1] for x in rr]
        withsafe = [x for x in rr if x[3] > 0]
        print(f'{role}: n={len(rr)} lag r1000->end median {statistics.median(lag)} mean {statistics.mean(lag):.0f}; '
              f'with any provably safe round {len(withsafe)} ({100*len(withsafe)/len(rr):.0f}%), '
              f'safe rounds median {statistics.median([x[3] for x in rr])}')
        if withsafe:
            gap = [x[4] - x[1] for x in withsafe]
            fin = [x[5] - x[4] for x in withsafe]
            print(f'   first safe round - r1000: median {statistics.median(gap)}; end - first safe: median {statistics.median(fin)}, '
                  f'p75 {sorted(fin)[3*len(fin)//4]}')
    # games where both reached; loser had a safe window before winner's end
    print('L team-games with a safe round (lost anyway):', sum(1 for x in rows if x[0]=='L' and x[3]>0))

if __name__ == '__main__':
    main()
