"""Per game: winner/loser tributed and carried gems at the end; how often the loser's wealth (tributed+carried) at the end
was at least the winner's (a conversion loss), and the bag in channel at the end.
    py endcarry.py ANALYSIS_DIR"""
import gzip, json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
    except Exception:
        return None
    w = meta['result']['winner']; n = len(R['round'])
    carried = [0, 0]; maxbag = [0, 0]; chan = [0, 0]
    for c in R['champions']:
        g = c['gems'][n - 1] if c['alive'][n - 1] else 0
        carried[c['team']] += g
        maxbag[c['team']] = max(maxbag[c['team']], g)
        if c['chan'][n - 1] == 2: chan[c['team']] += g
    trib = [R['gems'][0][n - 1], R['gems'][1][n - 1]]
    # wealth at r-50 before end
    return dict(w=w, rounds=meta['result']['rounds'], trib=trib, carried=carried, maxbag=maxbag, chan=chan)

if __name__ == '__main__':
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(24) as ex:
        rows = [r for r in ex.map(one, dirs, chunksize=16) if r]
    n = len(rows)
    conv = [r for r in rows if r['trib'][1 - r['w']] + r['carried'][1 - r['w']] >= r['trib'][r['w']]]
    print(f'games {n}; loser wealth >= winner tributed at the end: {len(conv)} ({100*len(conv)/n:.1f}%)')
    for lo in (0, 100, 200, 400):
        k = sum(1 for r in rows if r['maxbag'][1 - r['w']] >= lo and r['maxbag'][1-r['w']] > 0)
        print(f'  loser max bag at end >= {lo}: {k} ({100*k/n:.1f}%)')
    chan = sum(1 for r in rows if r['chan'][1 - r['w']] > 0)
    print(f'  loser channelling a tribute at the end: {chan} ({100*chan/n:.1f}%)')
    import statistics as st
    print('  loser carried at end median', st.median(r['carried'][1-r['w']] for r in rows), 'winner', st.median(r['carried'][r['w']] for r in rows))
    print('  round-2000 games', sum(1 for r in rows if r['rounds'] >= 2000))
    # side
    print('  team A wins', sum(1 for r in rows if r['w'] == 0))
