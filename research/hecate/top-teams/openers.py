"""How fights open: first hit's ability, range, target state."""
from collections import Counter, defaultdict
from multiprocessing import Pool
from common import games, load, chebyshev, TOP, US, SHORT, ref
from analysis.fights import engagements


def feat(rec):
    g = load(rec)
    M = g.map
    T = g.team_of
    fights, _ = engagements(g)
    hits = [e for e in g.events if e['k'] in ('attack', 'cast') and e.get('dmg') and any(v in T and T[v] != T[e['a']] for v, _ in e['dmg'])]
    camp_hit = defaultdict(set)
    for e in g.events:
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            camp_hit[e['a']].add(e['r'])
    out = []
    j = 0
    for f in fights:
        r0 = f['r0']
        first = next((e for e in hits if e['r'] == r0), None)
        if not first:
            continue
        a = first['a']
        t = T[a]
        v = next(v for v, _ in first['dmg'] if v in T and T[v] != t)
        i = g.start_idx(r0)
        vp = g.pos(v, i)
        ap = tuple(first['f'])
        vch = g.ch(v)
        allies_v = sum(1 for c in T if T[c] == T[v] and c != v and g.pos(c, i) and vp and chebyshev(g.pos(c, i), vp) <= 4)
        allies_a = sum(1 for c in T if T[c] == t and c != a and g.pos(c, i) and chebyshev(g.pos(c, i), ap) <= 5)
        farming = any(rr in camp_hit[v] for rr in range(r0 - 3, r0 + 1))
        kills = f['kills'][t]
        deaths = f['kills'][1 - t]
        out.append({'t': t, 'ab': first.get('ab') if first['k'] == 'cast' else 'attack', 'range': chebyshev(ap, vp) if vp else None,
                    'stun': bool(first.get('stun')), 'v_alone': allies_v == 0, 'a_allies': allies_a, 'v_farming': farming,
                    'v_hp': vch['hp'][i] / vch['maxHp'][i], 'v_gems': vch['gems'][i], 'from_bush': ap in M.bushes,
                    'k': kills, 'd': deaths, 'half': M.half(M.own(t, ap)), 'ref': ref(rec, r0)})
    return {'rec': rec, 'names': g.names, 'f': out}


if __name__ == '__main__':
    with Pool(14) as p:
        res = p.map(feat, games(), chunksize=4)
    st = defaultdict(Counter)
    abs_ = defaultdict(Counter)
    ex = defaultdict(list)
    for r in res:
        for f in r['f']:
            n = r['names'][f['t']]
            s = st[n]
            s['n'] += 1
            abs_[n][f['ab'] + ('+stun' if f['stun'] else '')] += 1
            s['r4'] += (f['range'] or 0) >= 4
            s['valone'] += f['v_alone']
            s['farm'] += f['v_farming']
            s['bag'] += f['v_gems'] >= 30
            s['bush'] += f['from_bush']
            s['allies'] += f['a_allies']
            s['enemyhalf'] += f['half'] == 1
            s['kill'] += f['k'] > 0
            s['lost'] += f['d'] > 0
            key = 'alone' if f['v_alone'] else 'supported'
            s[key] += 1
            s[key + '_kill'] += f['k'] > 0
            s[key + '_lost'] += f['d'] > 0
            if f['v_alone'] and f['k'] and len(ex[n]) < 3:
                ex[n].append(f['ref'])
    print('| team | fights opened | opened from range 4+ | with a stun | from bush | target alone (no ally within 4) | target farming | target carrying 30+ | opener allies within 5 (mean) | in enemy half | got a kill | lost a champion | vs alone target: kill / loss | vs supported: kill / loss |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n in TOP + [US]:
        s = st[n]
        N = max(1, s['n'])
        A = max(1, s['alone'])
        S = max(1, s['supported'])
        p = lambda x, y=N: f'{100*x/y:.0f}%'
        print(f"| {SHORT[n]} | {s['n']} | {p(s['r4'])} | {p(sum(v for k, v in abs_[n].items() if 'stun' in k))} | {p(s['bush'])} | {p(s['valone'])} | {p(s['farm'])} | {p(s['bag'])} | {s['allies']/N:.2f} | {p(s['enemyhalf'])} | {p(s['kill'])} | {p(s['lost'])} | {p(s['alone_kill'],A)} / {p(s['alone_lost'],A)} | {p(s['supported_kill'],S)} / {p(s['supported_lost'],S)} |")
    print()
    for n in TOP + [US]:
        tot = sum(abs_[n].values())
        print(f'- {SHORT[n]} openers: ' + ', '.join(f'{k} {100*v/tot:.0f}%' for k, v in abs_[n].most_common(5)) + ' | e.g. ' + '; '.join(ex[n][:2]))
