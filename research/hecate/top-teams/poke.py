"""Damage to dangerous camps (wolf/elk/monolith) by attacker distance, and how often it is followed by camp damage taken."""
from collections import Counter, defaultdict
from multiprocessing import Pool
from common import games, load, chebyshev, TOP, US, SHORT, ref


def feat(rec):
    g = load(rec)
    M = g.map
    T = g.team_of
    cp = {c['id']: c for c in M.camps}
    st = defaultdict(Counter)
    ex = []
    for e in g.events:
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            t = T[e['a']]
            f = tuple(e['f'])
            for c, amt in e['cdmg']:
                if cp[c]['type'] in ('Gem cluster', 'Gold cluster'):
                    continue
                d = chebyshev(f, (cp[c]['x'], cp[c]['y']))
                key = cp[c]['type'][0]
                st[t][('all', key)] += amt
                if d >= 4:
                    st[t][('far', key)] += amt
                    st[t][('far_' + (e.get('ab') or 'atk'), key)] += amt
                    if len(ex) < 3 and key == 'E':
                        ex.append(ref(rec, e['r']) + f" {g.name_of[e['a']]} {e.get('ab')} d{d}")
    return {'names': g.names, 'st': {t: dict(v) for t, v in st.items()}, 'ex': ex}


if __name__ == '__main__':
    with Pool(14) as p:
        res = p.map(feat, games(), chunksize=4)
    S = defaultdict(Counter)
    ex = defaultdict(list)
    for r in res:
        for t, d in r['st'].items():
            n = r['names'][t]
            for k, v in d.items():
                S[n][k] += v
            ex[n] += r['ex']
    print('| team | wolf dmg from 4+ | elk dmg from 4+ | monolith dmg from 4+ |')
    print('|---|---|---|---|')
    for n in TOP + [US]:
        s = S[n]
        print(f"| {SHORT[n]} | " + ' | '.join(f"{100*s[('far',k)]/max(1,s[('all',k)]):.0f}%" for k in 'WEM') + ' |')
    for n in TOP[:3]:
        print('-', SHORT[n], '; '.join(ex[n][:3]))
