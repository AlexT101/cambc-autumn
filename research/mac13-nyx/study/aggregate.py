"""Aggregates out/*.json into the answers. python3 aggregate.py [q1 q2 ...]"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

OUT = Path(__file__).resolve().parent / 'out'
G = [json.loads(p.read_text()) for p in sorted(OUT.glob('*.json'))]
NG = len(G)
WL = {True: 'winner', False: 'loser'}
want = set(sys.argv[1:]) or {'q0', 'q1', 'q2', 'q3', 'q4', 'q5', 'q6'}


def pct(a, b):
    return f'{100 * a / b:.1f}%' if b else '-'


def q(xs, ps=(0.25, 0.5, 0.75)):
    xs = sorted(xs)
    if not xs:
        return '-'
    return '/'.join(f'{xs[min(len(xs) - 1, int(p * len(xs)))]:.3g}' for p in ps)


if 'q0' in want:
    trunc = sum(1 for g in G if g['dmax'] < g['rounds'])
    print(f'games {NG}, D trace truncated in {trunc}; mean rounds {mean(g["rounds"] for g in G):.0f}; '
          f'side A wins {sum(g["winner"] == 0 for g in G)}')

if 'q1' in want:
    print('\n== Q1 deaths to champions: killer visibility (best = any killer seen; worst = every killer)')
    for key in ('best', 'worst'):
        for won in (True, False, None):
            rows = [d for g in G for d in g['q1'] if won is None or d['won'] == won]
            c = Counter(d[key] for d in rows)
            n = len(rows)
            lab = 'all' if won is None else WL[won] + ' victims'
            print(f'  {key:5s} {lab:15s} n={n:4d} ({n / NG:.1f}/game)  seen by victim at last turn {pct(c["victim"], n)}, '
                  f'only in its 3 earlier turns {pct(c["victim3"], n)}, unseen by victim but seen by ally {pct(c["ally"], n)}, '
                  f'unseen by team {pct(c["none"], n)}')
    # per killer, with distance at the first hit's round start
    ks = [k for g in G for d in g['q1'] for k in d['killers']]
    c = Counter(k['cls'] for k in ks)
    print(f'  per killer n={len(ks)}: ' + ', '.join(f'{x} {pct(c[x], len(ks))}' for x in ('victim', 'victim3', 'ally', 'none')))
    for cls in ('ally', 'none'):
        sub = [k for k in ks if k['cls'] == cls and k['dist'] is not None]
        print(f'    {cls}: dist at first-hit round start q25/50/75 {q([k["dist"] for k in sub])}; within 8: '
              f'{pct(sum(k["dist"] <= 8 for k in sub), len(sub))}; killer on bush {pct(sum(bool(k["kbush"]) for k in sub), len(sub))}')
    rows = [d for g in G for d in g['q1']]
    for cls in ('victim', 'victim3', 'ally', 'none'):
        sub = [d for d in rows if d['worst'] == cls]
        if sub:
            print(f'    worst={cls}: mean bag {mean(d["gems"] for d in sub):.1f}, types {Counter(d["vtype"] for d in sub).most_common(4)}')
    print('  general: enemy-champion pairs within 10 (8) of a champion at round start')
    for key, lab in (('q1gen', '<=10'), ('q1gen8', '<=8')):
        for won in (True, False):
            tot = [0, 0, 0, 0]
            for g in G:
                t = g['winner'] if won else 1 - g['winner']
                for j in range(4):
                    tot[j] += g[key][str(t)][j]
            print(f'    {lab} {WL[won]}: pairs {tot[0]} ({tot[0] / NG:.0f}/game), unseen by champ {pct(tot[1], tot[0])}, '
                  f'unseen by champ but seen by an ally {pct(tot[2], tot[0])}, unseen by all {pct(tot[3], tot[0])}')

if 'q2' in want:
    print('\n== Q2 fights: allies within 8 of the first target at the first-hit round start')
    for label, filt in (('all', lambda f: True), ('r<300', lambda f: f['r0'] < 300), ('r>=300', lambda f: f['r0'] >= 300)):
        for won in (True, False):
            near = dealt = camp = 0
            nf = 0
            kills = 0
            deaths = 0
            outs = Counter()
            for g in G:
                t = g['winner'] if won else 1 - g['winner']
                for f in g['q2']:
                    if not filt(f):
                        continue
                    s = f['sides'][str(t)]
                    nf += 1
                    near += s['near']
                    dealt += s['dealt']
                    camp += s['camp']
                    kills += f['kills'][t]
                    deaths += f['kills'][1 - t]
                    for x in s['other_chars']:
                        outs[x[0]] += 1
            print(f'  {label:6s} {WL[won]}: fights {nf} ({nf / NG:.1f}/game), near/fight {near / nf:.2f}, dealt champ dmg in 3 rds '
                  f'{pct(dealt, near)}, hit camps instead {pct(camp, near)}, neither {pct(near - dealt - camp, near)} '
                  f'(their D char r0: {outs.most_common(6)}); kills {kills} deaths {deaths}')
    # by role: defender side (first target's side) vs initiator side
    print('  by role (pooled):')
    for role in ('def', 'att'):
        near = dealt = camp = 0
        for g in G:
            for f in g['q2']:
                t = f['def'] if role == 'def' else 1 - f['def']
                s = f['sides'][str(t)]
                near += s['near']
                dealt += s['dealt']
                camp += s['camp']
        print(f'    {role}: near {near}, dealt {pct(dealt, near)}, camp {pct(camp, near)}, neither {pct(near - dealt - camp, near)}')
    # kill outcome vs participation difference
    print('  outcome by (dealers side A - side B) in first 3 rounds, fights with any kill:')
    tab = defaultdict(lambda: [0, 0, 0])
    for g in G:
        for f in g['q2']:
            if sum(f['kills']) == 0:
                continue
            w = g['winner']
            dd = f['sides'][str(w)]['dealt'] - f['sides'][str(1 - w)]['dealt']
            dd = max(-2, min(2, dd))
            tab[dd][0] += 1
            tab[dd][1] += f['kills'][w]
            tab[dd][2] += f['kills'][1 - w]
    for dd in sorted(tab):
        n, kw, kl = tab[dd]
        print(f'    dealers(winner-loser)={dd:+d}: fights {n}, winner kills {kw}, loser kills {kl}')
    # fights where a side had >=3 near: share of near that dealt
    print('  fights with >=3 allies near the target (per side):')
    for won in (True, False):
        near = dealt = camp = nf = 0
        for g in G:
            t = g['winner'] if won else 1 - g['winner']
            for f in g['q2']:
                s = f['sides'][str(t)]
                if s['near'] >= 3:
                    nf += 1
                    near += s['near']
                    dealt += s['dealt']
                    camp += s['camp']
        print(f'    {WL[won]}: {nf} fights, near {near / nf:.2f}, dealt {pct(dealt, near)}, camp {pct(camp, near)}')
    # kill-producing fights: total kills by participants
    allf = [f for g in G for f in g['q2']]
    print(f'  fights with a kill {pct(sum(1 for f in allf if sum(f["kills"])), len(allf))}; '
          f'size near (both sides) q25/50/75 {q([f["sides"]["0"]["near"] + f["sides"]["1"]["near"] for f in allf])}')

if 'q3' in want:
    print('\n== Q3 home cycle (completed recalls)')
    for won in (True, False):
        rs = [x for g in G for x in g['q3'] if x['won'] == won]
        starts = sum(g['q3starts'][str(g['winner'] if won else 1 - g['winner'])] for g in G)
        wi = [x for g in G for x in g['q3walkin'] if x['won'] == won]
        print(f'  {WL[won]}: recall starts {starts / NG:.0f}/game, completed {len(rs) / NG:.1f}/game, walk-in spawn visits {len(wi) / NG:.1f}/game')
        print(f'    at start: hp frac q25/50/75 {q([x["hpf"] for x in rs])}, gems {q([x["gems"] for x in rs])}, gold {q([x["gold"] for x in rs])}, '
              f'walk dist from spawn {q([x["from_dist"] for x in rs if x["from_dist"] is not None])}')
        print(f'    to next camp hit/hold: rounds {q([x["gap"] for x in rs if x["gap"] is not None])} (mean {mean(x["gap"] for x in rs if x["gap"] is not None):.1f}), '
              f'walk-out {q([x["walk"] for x in rs if x["walk"] is not None])}, died first {pct(sum(x["dead_first"] for x in rs), len(rs))}, '
              f'none in 300 {pct(sum(x["next"] is None and not x["dead_first"] for x in rs), len(rs))}, stay on spawn {q([x["stay"] for x in rs if x["stay"] is not None])}')
        pre = Counter(x['pre'][:3] for x in rs)
        at = Counter(x['pre'][3] for x in rs)
        print(f'    D chars 3 turns before: {pre.most_common(8)}; at the start turn: {at.most_common(6)}')
        # classification
        cls = Counter()
        for x in rs:
            if x['hpf'] < 0.5:
                c = 'heal'
            elif x['trib_after'] is not None and x['gems'] > 0:
                c = 'bank'
            elif x['shop_gold'] > 0:
                c = 'shop'
            else:
                c = 'travel'
            x['cls'] = c
            cls[c] += 1
        print('    split: ' + ', '.join(f'{k} {pct(v, len(rs))}' for k, v in cls.most_common()))
        for c in ('heal', 'bank', 'shop', 'travel'):
            sub = [x for x in rs if x['cls'] == c]
            if sub:
                gaps = [x['gap'] for x in sub if x['gap'] is not None]
                print(f'      {c}: n {len(sub) / NG:.1f}/game, gems {q([x["gems"] for x in sub])}, gold {q([x["gold"] for x in sub])}, '
                      f'hp {q([x["hpf"] for x in sub])}, from {q([x["from_dist"] for x in sub if x["from_dist"] is not None])}, '
                      f'gap {q(gaps)}, walk-out {q([x["walk"] for x in sub if x["walk"] is not None])}, pre {Counter(x["pre"] for x in sub).most_common(3)}, types {Counter(x["type"] for x in sub).most_common(3)}')
        # gems carried in recall with gems>0 & no tribute after
        g0 = [x for x in rs if x['gems'] > 0]
        print(f'    recalls carrying gems {pct(len(g0), len(rs))}, of those tribute before next camp work {pct(sum(x["trib_after"] is not None for x in g0), len(g0))}')
        print(f'    walk-ins: hp {q([x["hpf"] for x in wi])}, gems {q([x["gems"] for x in wi])}, gold {q([x["gold"] for x in wi])}, D {Counter(x["ch"] for x in wi).most_common(5)}')
        canc = Counter()
        for g in G:
            canc.update(g['q3cancels'][str(g['winner'] if won else 1 - g['winner'])])
        print(f'    recall cancels/game: ' + ', '.join(f'{k} {v / NG:.1f}' for k, v in canc.most_common(6)))

if 'q4' in want:
    print('\n== Q4 decisive divergence (first round a side trails by 2+ deaths; Cassi/Issac counted once, camp deaths included)')
    dv = [g for g in G if g['q4']['div_r']]
    print(f'  games with a 2+ gap: {len(dv)}/{NG}; trailing side lost {pct(sum(g["q4"]["div_team"] != g["winner"] for g in dv), len(dv))}; '
          f'divergence round q25/50/75 {q([g["q4"]["div_r"] for g in dv])}; deaths/game winner {mean(g["q4"]["n_deaths"][g["winner"]] for g in G):.1f} loser {mean(g["q4"]["n_deaths"][1 - g["winner"]] for g in G):.1f}; '
          f'camp deaths/game {mean(sum(g["q4"]["n_camp_deaths"]) for g in G):.2f}')
    for lab, rows in (('first death of game', [g['q4']['first'][0] for g in G if g['q4']['first']]),
                      ('trailing side deaths up to divergence', [x for g in dv for x in g['q4']['div_deaths']]),
                      ('first two deaths of trailing side', [x for g in dv for x in g['q4']['div_deaths'][:2]])):
        n = len(rows)
        print(f'  {lab}: n {n}, victim on losing side {pct(sum(not x["won"] for x in rows), n)}, Prism {pct(sum(x["type"] == "Prism" for x in rows), n)}, '
              f'round q {q([x["r"] for x in rows])}, bag q {q([x["gems"] for x in rows])}, camp {pct(sum(x["camp"] for x in rows), n)}')
        print(f'    D char at last turn {Counter(x["ch"] for x in rows).most_common(8)}')
        print(f'    D last 3 turns {Counter(x["ch3"] for x in rows).most_common(8)}')
        print(f'    where {Counter(x["side"] for x in rows).most_common()}; types {Counter(x["type"] for x in rows).most_common(6)}')
    # prism share of champions overall
    tp = Counter()
    for g in G:
        tp.update(g['names'].values())
    print(f'  Prism share of bodies {pct(tp["Prism"], sum(tp.values()))}; picks: {tp.most_common(8)}')

if 'q5' in want:
    print('\n== Q5 decision chars: share of alive champion-rounds and what the turns did')
    agg = defaultdict(lambda: defaultdict(int))
    for g in G:
        for k, v in g['q5'].items():
            won, typ, ch = k.split('|')
            for kk, vv in v.items():
                agg[(int(won), ch)][kk] += vv
                agg[(int(won), '*')][kk] += vv
    for won in (1, 0):
        tot = agg[(won, '*')]['n']
        print(f'  {WL[bool(won)]} (alive rounds {tot / NG:.0f}/game):')
        for (w, ch), v in sorted(agg.items(), key=lambda kv: -kv[1]['n']):
            if w != won:
                continue
            n = v['n']
            print(f'    {ch}: {pct(n, tot):>6s}  idle {pct(v["idle"], n)}, chan {pct(v["chan"], n)}, moved {pct(v["moved"], n)}, '
                  f'camp {pct(v["camp"], n)}, fight {pct(v["fight"], n)}, on spawn {pct(v["onspawn"], n)}, oof {pct(v["oof"], n)}')
    print('  per type, the h/-/F idle shares:')
    agt = defaultdict(lambda: defaultdict(int))
    for g in G:
        for k, v in g['q5'].items():
            won, typ, ch = k.split('|')
            for kk, vv in v.items():
                agt[(typ, ch)][kk] += vv
                agt[(typ, '*')][kk] += vv
    for typ in sorted({t for t, _ in agt}):
        tot = agt[(typ, '*')]
        mix = sorted(((ch, v['n']) for (t, ch), v in agt.items() if t == typ and ch != '*'), key=lambda x: -x[1])[:5]
        print(f'    {typ:14s} n {tot["n"]}, idle {pct(tot["idle"], tot["n"])}, camp {pct(tot["camp"], tot["n"])}, moved {pct(tot["moved"], tot["n"])}, '
              f'mix ' + ' '.join(f'{c}:{pct(n, tot["n"])}' for c, n in mix))

if 'q6' in want:
    print('\n== Q6 stale targets: F turns walking to farm_group (3+ turns, >4 steps away) while the group is not alive')
    for won in (True, False):
        ws = [w for g in G for w in g['q6walks'] if w['won'] == won]
        st = [w for w in ws if w['stale']]
        tot_walk = sum(w['n'] for w in ws)
        print(f'  {WL[won]}: farm walks {len(ws) / NG:.1f}/game ({tot_walk / NG:.0f} rounds); stale {len(st) / NG:.1f}/game, '
              f'stale rounds {sum(w["dead"] for w in st) / NG:.1f}/game ({pct(sum(w["dead"] for w in st), tot_walk)} of walk rounds)')
        for key in ('state', 'emptier', 'holder', 'gside', 'why', 'type', 'arrive_late', 'mono'):
            c = Counter()
            for w in st:
                c[w[key]] += w['dead']
            print(f'    by {key} (rounds/game): ' + ', '.join(f'{k} {v / NG:.1f}' for k, v in c.most_common(7)))
        # state x emptier
        c = Counter()
        for w in st:
            c[(w['state'], w['emptier'], w['holder'])] += w['dead']
        print('    state(2 claimable,3 respawning) x emptier x holder: ' + ', '.join(f'{k} {v / NG:.1f}' for k, v in c.most_common(8)))
        r3 = [w for w in st if w['state'] == 3]
        if r3:
            print(f'    respawning targets: resp_left q {q([w["resp_left"] for w in r3])}, dist0 q {q([w["dist0"] for w in r3])}, '
                  f'walk would arrive before respawn (resp_left > dist0) {pct(sum(w["resp_left"] > w["dist0"] for w in r3), len(r3))}')
        # outcome classes of stale walks
        c = Counter()
        for w in st:
            if w['why'] == 'reached':
                k = 'reached, alive on arrival' if w['wait_after'] == 0 else ('reached, waited 1-10' if w['wait_after'] <= 10 else 'reached, waited 11+')
            elif w['end_alive']:
                k = 'left it as it came alive'
            else:
                k = 'abandoned while dead (' + w['why'] + ')'
            c[(k, w['emptier'])] += w['dead']
        print('    outcome x emptier (stale rounds/game): ' + ', '.join(f'{k} {v / NG:.1f}' for k, v in c.most_common(12)))
        wa = [w['wait_after'] for w in st if w['why'] == 'reached']
        print(f'    reached: wait after arrival q {q(wa)}; mean {mean(wa):.1f}; total wait {sum(wa) / NG:.0f} rounds/game')
        ab = [w for w in st if w['why'] != 'reached' and not w['end_alive']]
        print(f'    abandoned while dead: {len(ab) / NG:.1f} walks/game, {sum(w["n"] for w in ab) / NG:.0f} walk rounds/game '
              f'(own-emptied {sum(w["n"] for w in ab if w["emptier"] == "own") / NG:.0f}, enemy-emptied {sum(w["n"] for w in ab if w["emptier"] == "enemy") / NG:.0f}); '
              f'by side {Counter(w["gside"] for w in ab).most_common()}; state {Counter(w["state"] for w in ab).most_common()}')
        en = [w for w in st if w['emptier'] == 'enemy']
        print(f'    enemy-emptied targets: {len(en) / NG:.1f} walks/game, {sum(w["dead"] for w in en) / NG:.0f} dead-target rounds/game, '
              f'by gside {Counter(w["gside"] for w in en).most_common()}, outcomes {Counter(w["why"] for w in en).most_common()}')
    print('  alive non-Monolith groups nobody hits this round, with an ally of the side within 12 steps that is still (F/B/-), '
          'walking to a dead farm target, or walking to a target 5+ steps farther')
    for won in (1, 0):
        agg = defaultdict(float)
        for g in G:
            for k, v in g['q6unworked'].items():
                parts = k.split('|')
                if int(parts[0]) != won:
                    continue
                agg[tuple(parts[1:])] += v
        gems = sum(v for k, v in agg.items() if k[-1] == 'gems')
        n = sum(v for k, v in agg.items() if k[-1] == 'n')
        print(f'  {WL[bool(won)]}: gem-weighted group-rounds {gems / NG:.0f}/game, group-rounds {n / NG:.0f}/game')
        for idx, lab in ((0, 'group side'), (1, 'ally kind'), (2, 'ally D char'), (3, 'ally type'), (4, 'group top monster')):
            c = Counter()
            for k, v in agg.items():
                if k[-1] == 'gems':
                    c[k[idx]] += v
            print(f'    by {lab}: ' + ', '.join(f'{a} {b / NG:.0f}' for a, b in c.most_common(8)))
        c = Counter()
        for k, v in agg.items():
            if k[-1] == 'n':
                c[(k[0], k[1])] += v
        print('    group-rounds by (side, kind): ' + ', '.join(f'{a} {b / NG:.0f}' for a, b in c.most_common(9)))

if 'q2b' in want:
    print('\n== Q2b fights, excluding the first target and its Cassi/Issac partner')
    for role in ('def', 'att'):
        for label, filt in (('r<300', lambda f: f['r0'] < 300), ('r>=300', lambda f: f['r0'] >= 300)):
            for won in (True, False):
                c = Counter()
                chars = Counter()
                nf = 0
                for g in G:
                    t = g['winner'] if won else 1 - g['winner']
                    for f in g['q2']:
                        if not filt(f) or ((f['def'] == t) != (role == 'def')):
                            continue
                        nf += 1
                        for cid, cls, is_t, dist, ch in f['sides'][str(t)]['mem']:
                            if is_t:
                                continue
                            c[cls] += 1
                            if cls != 'dealt':
                                chars[ch[-1]] += 1
                n = sum(c.values())
                if nf:
                    print(f'  {role} {label} {WL[won]}: fights {nf / NG:.1f}/game, other allies near {n / nf:.2f}/fight, dealt {pct(c["dealt"], n)}, '
                          f'camp {pct(c["camp"], n)}, neither {pct(c["other"], n)}; non-dealers D at r0 {chars.most_common(6)}')
    # target's own response
    for won in (True, False):
        c = Counter()
        for g in G:
            t = g['winner'] if won else 1 - g['winner']
            for f in g['q2']:
                if f['def'] != t:
                    continue
                for cid, cls, is_t, dist, ch in f['sides'][str(t)]['mem']:
                    if is_t and dist == 0:
                        c[cls] += 1
        n = sum(c.values())
        print(f'  first target itself ({WL[won]}): hit back in 3 rds {pct(c["dealt"], n)}, camp {pct(c["camp"], n)}, neither {pct(c["other"], n)}')
    # numbers: near per side, winner vs loser, in kill fights
    for won in (True, False):
        nn = Counter()
        for g in G:
            t = g['winner'] if won else 1 - g['winner']
            for f in g['q2']:
                nn[min(4, f['sides'][str(t)]['near'])] += 1
        print(f'  near count distribution {WL[won]}: {sorted(nn.items())}')
    # kill outcome by near numbers advantage
    tab = defaultdict(lambda: [0, 0, 0])
    for g in G:
        for f in g['q2']:
            a = f['sides'][str(f['def'])]['near']
            b = f['sides'][str(1 - f['def'])]['near']
            k = max(-2, min(2, a - b))
            tab[k][0] += 1
            tab[k][1] += f['kills'][f['def']]
            tab[k][2] += f['kills'][1 - f['def']]
    for k in sorted(tab):
        n, kd, ka = tab[k]
        print(f'    near(def-att)={k:+d}: fights {n}, defender kills {kd}, attacker kills {ka}')

if 'q4b' in want:
    print('\n== Q4b what victims did before the first hit of the fatal run (champion kills only)')
    dv = [g for g in G if g['q4']['div_r']]
    for lab, rows in (('first death of game', [g['q4']['first'][0] for g in G if g['q4']['first']]),
                      ('first two deaths of trailing side', [x for g in dv for x in g['q4']['div_deaths'][:2]])):
        rows = [x for x in rows if x['pre']]
        n = len(rows)
        print(f'  {lab} (n {n}): D at last turn before first hit {Counter(x["pre"][-1] for x in rows).most_common(8)}')
        print(f'    3 turns before {Counter(x["pre"] for x in rows).most_common(8)}')
        print(f'    where at first hit {Counter(x["pside"] for x in rows).most_common()}; hp frac q {q([x["php"] for x in rows])}; '
              f'rounds from first hit to death q {q([x["r"] - x["r0"] for x in rows])}')
        print(f'    Prism {pct(sum(x["type"] == "Prism" for x in rows), n)}; Prism victims on losing side '
              f'{sum(1 for x in rows if x["type"] == "Prism" and not x["won"])}/{sum(1 for x in rows if x["type"] == "Prism")}')
