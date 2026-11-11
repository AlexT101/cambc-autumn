"""What the big-bag Prism deaths have in common (live v115 scrims). One row per death + hazard table of states."""
from lib import *
import pickle, statistics as st, sys
from multiprocessing import Pool
BAG = 40
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def xy(a):
    return (a['x'], a['y']) if isinstance(a, dict) else (a[0], a[1])

def one(arg):
    d, gm = arg
    if 'Prism' not in gm['our_picks']: return None
    meta, R, ev, mp = load(d)
    us = 0 if gm['side'] == 'a' else 1
    team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}
    n = len(R['round'])
    pid = [c for c in ch if typ[c] == 'Prism' and team[c] == us][0]
    P = ch[pid]
    allies = [c for c in ch if team[c] == us and c != pid]
    enemies = [c for c in ch if team[c] != us]
    altars = [xy(a) for a in mp['altars']]
    sp = mp['spawn']; ctr = lambda s: ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)
    own = ctr(sp[us])
    pos = lambda c, i: (ch[c]['x'][i], ch[c]['y'][i])
    def state(i):
        p = pos(pid, i)
        ed = sorted(cheb(p, pos(c, i)) for c in enemies if ch[c]['alive'][i])
        ad = sorted(cheb(p, pos(c, i)) for c in allies if ch[c]['alive'][i])
        return dict(hp=P['hp'][i] / max(1, P['maxHp'][i]), bag=P['gems'][i], ne=sum(x <= 6 for x in ed), na=sum(x <= 6 for x in ad),
                    e1=ed[0] if ed else 99, a1=ad[0] if ad else 99, alt=min(cheb(p, a) for a in altars), own=cheb(p, own), sees=len(P['sees'][i]))
    # events by round for prism
    mine = collections.defaultdict(list); monst = collections.Counter()
    for e in ev:
        if e.get('a') == pid: mine[e['r']].append(e)
        if e['k'] == 'camp_attack' and e.get('tgt') == pid: monst[e['r']] += e['dmg']
    deaths = []
    for e in ev:
        if e['k'] == 'death' and e['v'] == pid and e.get('gems', 0) >= BAG:
            T = e['r']; i = T - 1
            row = dict(match=gm['match'], map=gm['map'], opp=gm['opp_name'][:4], win=gm['result'] == 'win', r=T, gems=e['gems'],
                       killer=typ.get(e.get('by')) if 'camp' not in e and e.get('by') is not None else 'camp', cause=e.get('cause'), nass=len(e.get('assists') or []))
            for back in (1, 3, 5, 8, 12):
                j = max(0, i - back); row['s%d' % back] = state(j) if P['alive'][j] else None
            # first round (going back) of the continuous danger episode: enemy within 6
            j = i - 1
            gap = 0
            while j > 0 and P['alive'][j]:
                s = state(j)
                if s['ne'] == 0:
                    gap += 1
                    if gap > 3: break
                else: gap = 0
                j -= 1
            j0 = min(i - 1, j + gap + 1) if gap else j + 1
            row['L'] = i - j0; row['s0'] = state(j0) if P['alive'][j0] else None
            # first round in episode with hp<0.5
            row['t50'] = None
            for k in range(j0, i):
                if P['alive'][k] and P['hp'][k] / max(1, P['maxHp'][k]) < 0.5:
                    row['t50'] = i - k; row['s50'] = state(k); break
            acts = collections.Counter()
            for rr in range(T - 6, T + 1):
                for x in mine.get(rr, []):
                    k = x['k']
                    if k == 'attack': k = 'attack_camp' if 'camp' in x or 'cdmg' in x else 'attack_champ'
                    acts[k] += 1
            row['acts'] = dict(acts)
            row['monst10'] = sum(monst[rr] for rr in range(T - 10, T + 1))
            j10 = max(0, i - 10)
            row['hplost10'] = (P['hp'][j10] - 0) if P['alive'][j10] else None
            row['stun3'] = sum(1 for k in range(max(0, i - 3), i) if P['stun'][k])
            # movement in last 6 rounds relative to nearest enemy and own spawn
            a, b = max(0, i - 6), i - 1
            if P['alive'][a] and P['alive'][b]:
                sa, sb = state(a), state(b)
                row['de'] = sb['e1'] - sa['e1']; row['down'] = sb['own'] - sa['own']; row['dal'] = sb['a1'] - sa['a1']
            row['recalls_ep'] = sum(1 for rr in range(j0 + 1, T + 1) for x in mine.get(rr, []) if x['k'] == 'recall_start')
            deaths.append(row)
    # hazard: every round with bag>=BAG, alive, enemy within 6
    haz = collections.Counter(); trig = collections.Counter()
    dround = sorted(e['r'] for e in ev if e['k'] == 'death' and e['v'] == pid)
    prev = {}
    for i in range(n):
        if not P['alive'][i] or P['gems'][i] < BAG: prev = {}; continue
        s = state(i)
        if s['ne'] == 0: prev = {}; continue
        dies = any(i + 1 < r <= i + 9 for r in dround)
        hb = 0 if s['hp'] < .3 else 1 if s['hp'] < .5 else 2 if s['hp'] < .75 else 3
        nb = max(-2, min(2, s['ne'] - s['na'] - 1))  # enemies minus (allies + self)
        haz[(hb, nb, dies)] += 1
        rules = dict(hp50=s['hp'] < .5, outnum=s['ne'] > s['na'] + 1, alone=s['na'] == 0, hp50_out=s['hp'] < .5 and s['ne'] > s['na'], any=True,
                     hp75_alone=s['hp'] < .75 and s['na'] == 0)
        for k, v in rules.items():
            if v and not prev.get(k): trig[(k, dies)] += 1
        prev = rules
    bags = [P['gems'][i] for i in range(n) if P['alive'][i]]
    # enemy prism
    ep = [c for c in enemies if typ[c] == 'Prism']
    eb = None
    if ep:
        E = ch[ep[0]]; b = [E['gems'][i] for i in range(n) if E['alive'][i]]
        eb = (sum(b) / max(1, len(b)), sum(1 for e in ev if e['k'] == 'death' and e['v'] == ep[0] and e.get('gems', 0) >= BAG))
    return dict(match=gm['match'], opp=gm['opp_name'][:4], win=gm['result'] == 'win', deaths=deaths, haz=haz, trig=trig, eb=eb, n=n)

if __name__ == '__main__':
    with Pool(24) as p: rows = [r for r in p.map(one, find(), chunksize=4) if r]
    pickle.dump(rows, open('prism2.pkl', 'wb'))
    D = [d for r in rows for d in r['deaths']]
    G = len(rows)
    med = lambda v: round(st.median(v), 2) if v else None
    print('games', G, 'deaths', len(D), 'in losses', sum(not d['win'] for d in D), 'by opp', collections.Counter(d['opp'] for d in D))
    print('killer', collections.Counter(d['killer'] for d in D).most_common(8), 'cause', collections.Counter(d['cause'] for d in D).most_common(6))
    print('assists', collections.Counter(d['nass'] for d in D))
    print('episode length L (rounds enemy within 6 before death): median', med([d['L'] for d in D]), 'hist', collections.Counter(min(d['L'] // 3 * 3, 30) for d in D))
    for key in ('s0', 's12', 's8', 's5', 's3', 's1'):
        S = [d[key] for d in D if d.get(key)]
        print(key, 'n', len(S), 'hp', med([s['hp'] for s in S]), 'bag', med([s['bag'] for s in S]), 'ne', med([s['ne'] for s in S]), 'na', med([s['na'] for s in S]),
              'alone%', round(100 * sum(s['na'] == 0 for s in S) / len(S)), 'outnum%', round(100 * sum(s['ne'] > s['na'] + 1 for s in S) / len(S)),
              'ne0%', round(100 * sum(s['ne'] == 0 for s in S) / len(S)),
              'e1', med([s['e1'] for s in S]), 'a1', med([s['a1'] for s in S]), 'alt', med([s['alt'] for s in S]), 'own', med([s['own'] for s in S]))
    S = [d['s0'] for d in D if d.get('s0')]
    print('hp at episode start: <30', sum(s['hp'] < .3 for s in S), '30-50', sum(.3 <= s['hp'] < .5 for s in S), '50-75', sum(.5 <= s['hp'] < .75 for s in S), '75+', sum(s['hp'] >= .75 for s in S))
    print('na at episode start', collections.Counter(s['na'] for s in S), 'ne', collections.Counter(s['ne'] for s in S))
    print('a1 at episode start hist', collections.Counter(min(s['a1'] // 4 * 4, 20) for s in S))
    print('t50 (rounds from hp<50% to death) median', med([d['t50'] for d in D if d['t50']]), 'never<50 before', sum(d['t50'] is None for d in D), 'hist', collections.Counter(min(d['t50'], 10) for d in D if d['t50']))
    acts = collections.Counter()
    for d in D:
        for k, v in d['acts'].items(): acts[k] += v
    print('own actions in last 6 rounds per death', {k: round(v / len(D), 2) for k, v in acts.most_common(12)})
    print('deaths with attack_champ in last 6', sum('attack_champ' in d['acts'] or 'cast' in d['acts'] for d in D), 'with attack_camp', sum('attack_camp' in d['acts'] for d in D), 'tribute_start', sum('tribute_start' in d['acts'] for d in D))
    print('monster dmg share of last-10 hp lost: median', med([d['monst10'] / d['hplost10'] for d in D if d['hplost10']]), '>=30% in', sum(1 for d in D if d['hplost10'] and d['monst10'] / d['hplost10'] >= .3))
    print('stunned in last 3 rounds', sum(d['stun3'] > 0 for d in D))
    M = [d for d in D if 'de' in d]
    print('last 6 rounds: nearest-enemy dist change median', med([d['de'] for d in M]), 'closing(<0)', sum(d['de'] < 0 for d in M), 'opening(>0)', sum(d['de'] > 0 for d in M),
          '| own-spawn dist change: toward', sum(d['down'] < 0 for d in M), 'away', sum(d['down'] > 0 for d in M), '| ally dist: toward', sum(d['dal'] < 0 for d in M), 'away', sum(d['dal'] > 0 for d in M))
    print('recall starts in episode: median', med([d['recalls_ep'] for d in D]))
    H = collections.Counter(); TR = collections.Counter()
    for r in rows: H.update(r['haz']); TR.update(r['trig'])
    print('hazard: P(death within 8 rounds) by hp bin (rows <30,30-50,50-75,75+) x enemies-(allies+self) (cols <=-2,-1,0,1,>=2); cell = rate% (rounds)')
    for hb in range(4):
        print('  ', ' | '.join('%4.1f%% (%5d)' % (100 * H[(hb, nb, True)] / max(1, H[(hb, nb, True)] + H[(hb, nb, False)]), H[(hb, nb, True)] + H[(hb, nb, False)]) for nb in range(-2, 3)))
    print('rules: episodes/game, P(death within 8 | trigger)')
    for k in ('any', 'hp50', 'outnum', 'alone', 'hp50_out', 'hp75_alone'):
        t = TR[(k, True)] + TR[(k, False)]
        print('  %-10s %.2f/game  %.1f%%  (deaths-preceded %d)' % (k, t / G, 100 * TR[(k, True)] / max(1, t), TR[(k, True)]))
    E = [r['eb'] for r in rows if r['eb']]
    for o in ('Inte', 'Mite'):
        e = [r['eb'] for r in rows if r['eb'] and r['opp'] == o]
        print('enemy Prism', o, 'games', len(e), 'mean bag', med([x[0] for x in e]), 'deaths 40+ per game', round(sum(x[1] for x in e) / max(1, len(e)), 2))
