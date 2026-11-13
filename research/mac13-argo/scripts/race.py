"""The end race: per game, the first round each team's wealth (tributed + carried by living bodies) reached 1000, and who
won. A loser that reached 1000 wealth first lost a conversion race.
    py race.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
    except Exception:
        return None
    w = meta['result']['winner']; n = len(R['round'])
    first = [None, None]
    lead_at = {}
    tribs = R['gems']
    for i in range(n):
        wl = [tribs[0][i], tribs[1][i]]
        for c in R['champions']:
            if c['alive'][i]: wl[c['team']] += c['gems'][i]
        for t in (0, 1):
            if first[t] is None and wl[t] >= 1000: first[t] = R['round'][i]
    # tributes of the loser in the final 100 rounds: count events
    return dict(w=w, end=meta['result']['rounds'], first=first, trib=[tribs[0][n-1], tribs[1][n-1]], map=meta['map']['name'])

if __name__ == '__main__':
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(24) as ex:
        rows = [r for r in ex.map(one, dirs, chunksize=16) if r]
    n = len(rows)
    lf = [r for r in rows if r['first'][1-r['w']] is not None and (r['first'][r['w']] is None or r['first'][1-r['w']] < r['first'][r['w']])]
    print(f'games {n}; loser reached 1000 wealth strictly first: {len(lf)} ({100*len(lf)/n:.1f}%)')
    if lf:
        lead = [ (r['first'][r['w']] or r['end']) - r['first'][1-r['w']] for r in lf]
        conv = [r['end'] - r['first'][1-r['w']] for r in lf]
        print('  rounds the loser was first by: median', st.median(lead), 'quartiles', st.quantiles(lead, n=4))
        print('  rounds from loser reaching 1000 wealth to the end: median', st.median(conv), st.quantiles(conv, n=4))
    wf = [r for r in rows if r['first'][r['w']] is not None]
    conv_w = [r['end'] - r['first'][r['w']] for r in wf]
    print('  winner: rounds from 1000 wealth to its win: median', st.median(conv_w), st.quantiles(conv_w, n=4))
    both = [r for r in rows if None not in r['first']]
    print('  both reached 1000 wealth:', len(both), f'({100*len(both)/n:.1f}%)')
    json.dump(rows, open('/home/ubuntu/wt/mac13-argo/research/mac13-argo/data/race.json', 'w'))
