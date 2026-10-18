"""Damage/stun spell usage rate: casts per 100 alive champion-rounds and what they hit."""
from collections import Counter, defaultdict
from multiprocessing import Pool
from common import games, load, TOP, US, SHORT

UTIL = {'Attack reset', 'Dash', 'Shield', 'Heal'}


def feat(rec):
    g = load(rec)
    T = g.team_of
    st = Counter()
    for c in g.champs:
        st[(c['team'], 'alive')] += sum(g.ch(c['id'])['alive'])
    for e in g.events:
        if e['k'] != 'cast' or e.get('ab') in UTIL:
            continue
        t = T[e['a']]
        hit_ch = any(v in T and T[v] != t for v, _ in e.get('dmg', [])) or any(v in T and T[v] != t for v in e.get('stun', []))
        hit_camp = bool(e.get('cdmg')) or 'camp' in e
        st[(t, 'casts')] += 1
        st[(t, 'champ' if hit_ch else 'camp' if hit_camp else 'nothing')] += 1
    return g.names, st


if __name__ == '__main__':
    with Pool(14) as p:
        res = p.map(feat, games(), chunksize=4)
    S = defaultdict(Counter)
    for names, st in res:
        for (t, k), v in st.items():
            S[names[t]][k] += v
    print('| team | damage/stun casts per 100 alive champion-rounds | on champions | on camps | hit nothing |')
    print('|---|---|---|---|---|')
    for n in TOP + [US]:
        s = S[n]
        c = max(1, s['casts'])
        print(f"| {SHORT[n]} | {100*s['casts']/s['alive']:.1f} | {100*s['champ']/c:.0f}% | {100*s['camp']/c:.0f}% | {100*s['nothing']/c:.0f}% |")
