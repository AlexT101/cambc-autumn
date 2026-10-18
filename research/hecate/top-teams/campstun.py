"""Stuns cast on camps (a stunned camp skips its next attack)."""
from collections import Counter, defaultdict
from multiprocessing import Pool
from common import games, load, TOP, US, SHORT


def feat(rec):
    g = load(rec)
    cp = {c['id']: c['type'] for c in g.map.camps}
    st = Counter()
    for e in g.events:
        if e['k'] == 'cast' and 'camp' in e and e.get('ab') in ('CC',) and e['camp'] in cp:
            st[(g.team_of[e['a']], cp[e['camp']][0], g.name_of[e['a']])] += 1
    return g.names, st


if __name__ == '__main__':
    with Pool(14) as p:
        res = p.map(feat, games(), chunksize=4)
    S = defaultdict(Counter)
    G = Counter()
    for names, st in res:
        for t in (0, 1):
            G[names[t]] += 1
        for (t, ty, ch), v in st.items():
            S[names[t]][ty] += v
            S[names[t]]['ch:' + ch] += v
    print('| team | unit-target stun casts on camps per game: wolf / elk / monolith / clusters | casters |')
    print('|---|---|---|')
    for n in TOP + [US]:
        s = S[n]
        g = G[n]
        chs = ', '.join(f"{k[3:]} {v/g:.1f}" for k, v in s.most_common() if k.startswith('ch:'))
        print(f"| {SHORT[n]} | {s['W']/g:.1f} / {s['E']/g:.1f} / {s['M']/g:.1f} / {s['G']/g:.1f} | {chs} |")
