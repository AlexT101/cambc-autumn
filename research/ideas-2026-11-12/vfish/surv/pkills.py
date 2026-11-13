"""pkills.py EXT [--maxr 300]: each enemy-Prism kill of ours: the Prism's damage in the last 3 rounds against the victim's health then; who else hit."""
import sys, collections, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv')
from tracelib import *
ext = sys.argv[1]; maxr = int(sys.argv[sys.argv.index('--maxr') + 1]) if '--maxr' in sys.argv else 300
rows = []; ng = 0
for gm in games(ext):
    ng += 1
    typ = gm.typ; team = gm.team; cand = gm.cand
    for d in gm.deaths(maxr):
        by = d.get('by')
        if by not in typ or typ[by] != 'Prism' or team[by] == cand: continue
        v = d['v']; r = d['r']; c = gm.ch[v]
        # walk back 6 rounds: damage by source
        src = collections.Counter(); pcasts = []; hp_at_first = None
        for rr in range(max(1, r - 5), r + 1):
            for e in gm.byr[rr]:
                if e['k'] in ('attack', 'cast'):
                    for (t, dm) in (e.get('dmg') or []):
                        if t == v:
                            a = e['a']; src['Prism' if a == by else 'other champion'] += dm
                            if a == by and e['k'] == 'cast': pcasts.append((rr, e.get('ab'), dm))
                elif e['k'] == 'camp_attack' and e.get('tgt') == v: src['camp'] += e.get('dmg') or 0
        first = pcasts[0][0] if pcasts else r
        i = first - 2
        hp0 = c['hp'][i] if i >= 0 else c['maxHp'][0]
        F = gm.ch[by]['foc'][max(0, r - 2)]
        tot = sum(src.values()) or 1
        kinds = [k for (_, k, _) in pcasts]
        rows.append({'v': typ[v], 'r': r, 'hp0': hp0, 'maxhp': c['maxHp'][max(0, i)], 'F': F, 'pshare': src['Prism'] / tot, 'ncasts': len(pcasts), 'kinds': tuple(kinds[-2:]), 'span': r - first,
                     'hp6': c['hp'][max(0, r - 7)] / max(1, c['maxHp'][max(0, r - 7)])})
print(ng, 'games,', len(rows), 'Prism kills by r', maxr)
fr = lambda f: f"{sum(1 for x in rows if f(x))} ({sum(1 for x in rows if f(x)) / len(rows):.2f})"
print(' Prism casts on the victim in its last 6 rounds:', collections.Counter(x['ncasts'] for x in rows).most_common())
print(' last two casts:', collections.Counter(x['kinds'] for x in rows).most_common(6))
print(' victim health when the first of those casts landed (share of max): median', round(st.median(x['hp0'] / max(1, x['maxhp']) for x in rows), 2), '| 6 rounds before death', round(st.median(x['hp6'] for x in rows), 2))
print(' that health against the Prism Focus then: <= 1.0F', fr(lambda x: x['hp0'] <= x['F']), ' <= 1.5F+35', fr(lambda x: x['hp0'] <= 1.5 * x['F'] + 35), ' <= 2.5F+70', fr(lambda x: x['hp0'] <= 2.5 * x['F'] + 70), ' more', fr(lambda x: x['hp0'] > 2.5 * x['F'] + 70))
print(' Prism share of the damage in the last 6 rounds: median', round(st.median(x['pshare'] for x in rows), 2), '| over 0.8:', fr(lambda x: x['pshare'] > 0.8), '| under 0.5:', fr(lambda x: x['pshare'] < 0.5))
print(' Focus at the kill: median', st.median(x['F'] for x in rows), '| victims', collections.Counter(x['v'] for x in rows).most_common(8))
