"""Tributes from bushes and loitering in altar bushes."""
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from common import games, load, chebyshev, TOP, US, SHORT, ref


def feat(rec):
    g = load(rec)
    M = g.map
    ab = {b for b in M.bushes if any(chebyshev(b, a) <= 1 for a in M.altars)}
    ab3 = {b for b in M.bushes if any(chebyshev(b, a) <= 3 for a in M.altars)}
    out = {'rec': rec, 'names': g.names, 'has_ab': bool(ab), 'trib': Counter(), 'loiter': Counter(), 'alive': Counter()}
    if not ab:
        return out
    for e in g.events:
        if e['k'] == 'tribute_start':
            t = g.team_of[e['a']]
            out['trib'][(t, 'n')] += 1
            out['trib'][(t, 'bush')] += tuple(e['at']) in M.bushes
    for c in g.champs:
        ch = g.ch(c['id'])
        t = c['team']
        for i in range(len(ch['x'])):
            if not ch['alive'][i]:
                continue
            p = (ch['x'][i], ch['y'][i])
            out['alive'][t] += 1
            if p in ab3:
                out['loiter'][(t, 'altarbush')] += 1
                if ch['chan'][i] == 0 and ch['gems'][i] == 0:
                    out['loiter'][(t, 'altarbush_idle')] += 1
    return out


if __name__ == '__main__':
    recs = games()
    with Pool(14) as p:
        res = p.map(feat, recs, chunksize=4)
    st = defaultdict(Counter)
    for r in res:
        if not r['has_ab']:
            continue
        for t in (0, 1):
            n = r['names'][t]
            st[n]['games'] += 1
            st[n]['trib'] += r['trib'][(t, 'n')]
            st[n]['tb'] += r['trib'][(t, 'bush')]
            st[n]['alive'] += r['alive'][t]
            st[n]['lo'] += r['loiter'][(t, 'altarbush')]
            st[n]['idle'] += r['loiter'][(t, 'altarbush_idle')]
    print('| team | games (maps with a bush next to an altar) | tributes started from a bush | champion-rounds in bushes within 3 of an altar | ...of which with no bag, not channelling |')
    print('|---|---|---|---|---|')
    for n in TOP + [US]:
        s = st[n]
        if s['games']:
            print(f"| {SHORT[n]} | {s['games']} | {100*s['tb']/max(1,s['trib']):.0f}% | {100*s['lo']/s['alive']:.1f}% | {100*s['idle']/s['alive']:.1f}% |")
