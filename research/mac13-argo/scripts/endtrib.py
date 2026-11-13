"""After a team first reaches 1000 wealth (data/race.json): its tribute starts, cancels by cause, channel turns lost to
cancels, and the bag of each start, for winners and losers.
    py endtrib.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    w = meta['result']['winner']; n = len(R['round'])
    team = {c['id']: c['team'] for c in R['champions']}
    ctype = {c['id']: c['name'] for c in meta['champions']}
    first = [None, None]
    for i in range(n):
        wl = [R['gems'][0][i], R['gems'][1][i]]
        for c in R['champions']:
            if c['alive'][i]: wl[c['team']] += c['gems'][i]
        for t in (0, 1):
            if first[t] is None and wl[t] >= 1000: first[t] = R['round'][i]
    out = []
    for t in (0, 1):
        if first[t] is None: continue
        starts = []; cancels = Counter(); lost = 0; open_ = {}
        for e in ev:
            if e['r'] < first[t]: continue
            a = e.get('a')
            if a is None or team.get(a) != t: continue
            if e['k'] == 'tribute_start':
                starts.append((e['gems'], ctype[a], e['dur'])); open_[a] = (e['r'], e['dur'])
            elif e['k'] == 'tribute_cancel':
                cancels[e.get('cause')] += 1
                if a in open_: lost += e['r'] - open_[a][0]; open_.pop(a)
            elif e['k'] == 'tribute_end':
                open_.pop(a, None)
        out.append(dict(won=(t == w), first=first[t], end=meta['result']['rounds'], starts=starts, cancels=dict(cancels), lost=lost))
    return out

if __name__ == '__main__':
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=16):
            if r: rows += r
    for won in (True, False):
        S = [r for r in rows if r['won'] == won]
        if not S: continue
        big = [s for r in S for s in r['starts'] if s[0] >= 100]
        c = Counter()
        for r in S: c.update(r['cancels'])
        print(f"{'winners' if won else 'losers'} after 1000 wealth: n={len(S)}; starts/team {sum(len(r['starts']) for r in S)/len(S):.2f}; "
              f"100+ starts/team {len(big)/len(S):.2f} (median bag {st.median(b[0] for b in big) if big else 0}, by {Counter(b[1] for b in big).most_common(3)}); "
              f"cancels/team {sum(c.values())/len(S):.2f} {dict(c)}; channel rounds lost to cancels/team {sum(r['lost'] for r in S)/len(S):.1f}; "
              f"rounds 1000-wealth to end median {st.median(r['end']-r['first'] for r in S)}")
