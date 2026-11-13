"""Monolith groups (mirror): maps with one, captures of them a game, by the winner/loser, round, and gems.
py monolith.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text()); mp = json.loads((d / meta['mapFile']).resolve().read_text())
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception: return None
    mg = {c['group'] for c in mp['camps'] if c['type'] == 'Monolith'}
    if not mg: return (0, [], meta['result']['winner'], 0)
    caps = [(e['r'], e['team'], sum(s[1] for s in e['shares'])) for e in ev if e['k'] == 'capture' and e['g'] in mg]
    hits = sum(1 for e in ev if e['k'] in ('attack', 'cast') and any(c[0] in {c2['id'] for c2 in mp['camps'] if c2['group'] in mg} for c in e.get('cdmg', [])))
    return (len(mg), caps, meta['result']['winner'], hits)
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(24) as ex: rows = [r for r in ex.map(one, dirs, chunksize=8) if r and r[0]]
    caps = [c for r in rows for c in r[1]]
    print('games with a Monolith', len(rows), 'Monolith groups a game', st.mean(r[0] for r in rows))
    print('captures a game', len(caps) / len(rows), 'by the winner', sum(1 for r in rows for c in r[1] if c[1] == r[2]) / max(1, len(caps)),
          'median round', st.median(c[0] for c in caps) if caps else '-', 'gems each', st.mean(c[2] for c in caps) if caps else '-')
    print('games with >=1 capture', sum(1 for r in rows if r[1]), '; won by the first capturer',
          sum(1 for r in rows if r[1] and r[1][0][1] == r[2]) / max(1, sum(1 for r in rows if r[1])), '; hit events a game', st.mean(r[3] for r in rows))
