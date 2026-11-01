# Q2 aggregation over opp/fightfeat
import json, glob
from collections import defaultdict, Counter
S = 'replays/v66-analysis'
F = [json.load(open(p)) for p in glob.glob(S + '/opp/fightfeat/*.json')]
OPP = ['Fish', 'Mite', 'UoS', 'PBG']
by = defaultdict(list)
for f in F: by[f['opp']].append(f)


def tot(o, key):
    c = Counter()
    for f in by[o]:
        c.update(f['out'].get(key, {}))
    return c


def pct(a, b): return f'{a/b*100:4.0f}%' if b else '   -'


print('== (a) Response to local numbers: champion with a SEEN enemy within 5 (round end r); bucket = own bodies - enemy bodies within 8;')
print('   outcome at r+2: close/hold/open distance to nearest enemy, died. cells: close% open% died% (n)')
for meas in ('adv_cnt', 'adv_hp'):
    order = ['<=-2', '-1', '+0', '+1', '>=+2'] if meas == 'adv_cnt' else ['<0.5', '0.5-0.8', '0.8-1.25', '1.25-2', '>2']
    print(' ', meas)
    for o in OPP:
        for ro in ('us', 'them'):
            c = tot(o, ro + '|' + meas)
            cells = []
            for b in order:
                n = sum(c[f'{b}|{x}'] for x in ('close', 'hold', 'open', 'died'))
                cells.append(f"{b}: {pct(c[b+'|close'],n)} {pct(c[b+'|open'],n)} {pct(c[b+'|died'],n)} ({n})")
            print(f'   {o:5}{ro:5}', ' | '.join(cells))

print('\n== (c) Low-HP episodes (first round <30% HP, off spawn, enemy within 8): outcome within 10 rounds; kept recall in 5; moved away (r+3)')
for o in OPP:
    for ro in ('us', 'them'):
        c = tot(o, ro + '|lowhp'); n = sum(c.values())
        res = Counter(); rec = Counter(); mv = Counter()
        for k, v in c.items():
            a, b, m = k.split('|'); res[a] += v; rec[(a, b)] += v; mv[m] += v
        print(f'   {o:5}{ro:5} n={n} died {pct(res["died"],n)} home {pct(res["home"],n)} stay {pct(res["stay"],n)} | recall-kept {pct(sum(v for (a,b),v in rec.items() if b=="rec1"),n)} (of home: {pct(rec[("home","rec1")],res["home"])}) | r+3 open {pct(mv["open"],n)} close {pct(mv["close"],n)}')

print('\n== Chase (hunter side): enemy just dropped <30% off its spawn with hunters within 8: # hunters closing within 2 rounds; where')
for o in OPP:
    for ro in ('us', 'them'):
        c = tot(o, ro + '|chase_closers'); n = sum(c.values())
        anyc = sum(v for k, v in c.items() if not k.startswith('0of'))
        w = tot(o, ro + '|chase_where')
        print(f'   {o:5}{ro:5} n={n} any hunter closes {pct(anyc,n)}; >=2 close {pct(sum(v for k,v in c.items() if int(k.split("of")[0])>=2),n)} | in victim own half {pct(w["victim_own_half"],sum(w.values()))}')

print('\n== Target selection: attacks/unit casts on champions with >=2 enemy candidates in range')
for o in OPP:
    for ro in ('us', 'them'):
        c = tot(o, ro + '|tsel'); n = c['n']
        print(f'   {o:5}{ro:5} n={n:.0f} lowest-HP {pct(c["lowhp"],n)} lowest-HP% {pct(c["lowfrac"],n)} (chance {pct(c["chance"],n)}) | max-gems {pct(c["maxgems"],c["gn"])} (chance {pct(c["gchance"],c["gn"])}) | Prism when present {pct(c["prism"],c["pn"])} (chance {pct(c["pchance"],c["pn"])})')

print('\n== Focus: rounds with >=2 attackers on champions; mean share on main target; % all on one')
for o in OPP:
    for ro in ('us', 'them'):
        c = tot(o, ro + '|focus'); n = c['rounds']
        print(f'   {o:5}{ro:5} rounds {n:.0f} share {c["share"]/max(1,n)*100:.0f}% all-one {pct(c["all_one"],n)}')

print('\n== Damage by range: share of champion damage dealt from Chebyshev >=2, by attacker kind')
for o in OPP:
    for ro in ('us', 'them'):
        c = tot(o, ro + '|dmg_dist')
        r2 = c['ranged|>=2'] + c['ranged|<=1']; m2 = c['melee|>=2'] + c['melee|<=1']
        print(f'   {o:5}{ro:5} ranged dmg {r2:9.0f} ({pct(c["ranged|>=2"],r2)} from >=2) melee dmg {m2:9.0f} ({pct(c["melee|>=2"],m2)} from >=2 [spells/AoE])')

print('\n== Kill opportunities: end of round, enemy off-spawn with HP <= Strength of a champion within reach (ranged 3, melee 2)')
for o in OPP:
    for ro in ('us', 'them'):
        c = tot(o, ro + '|killopp'); n = sum(c.values())
        print(f'   {o:5}{ro:5} n={n} killed next round {pct(c["killed"],n)} died otherwise {pct(c["died_other"],n)} survived {pct(c["survived"],n)}')

print('\n== Combat dashes (enemy within 8 at cast): per champion type, engage/escape counts; engage: landed adjacent, stun, kill within 3, dasher died within 5, landed within 8 walk of enemy spawn')
for o in OPP:
    for ro in ('us', 'them'):
        c = tot(o, ro + '|dash')
        types = sorted({k.split('|')[0] for k in c})
        parts = []
        for ty in types:
            e = c[f'{ty}|engage']; s = c[f'{ty}|escape']; l = c[f'{ty}|lateral']
            if e + s + l < 20: continue
            parts.append(f"{ty}: eng {e/len(by[o]):.1f}/g esc {s/len(by[o]):.1f}/g | eng adj {pct(c[ty+'|engage|adj'],e)} stun {pct(c[ty+'|engage|stun'],e)} kill {pct(c[ty+'|engage|kill'],e)} died {pct(c[ty+'|engage|died'],e)} deep {pct(c[ty+'|engage|deep'],e)}")
        print(f'   {o:5}{ro:5}'); [print('        ', p) for p in parts]

print('\n== Damage exchange by type pair (their X vs our Y): dmg X->Y / dmg Y->X, per game where both present (top pairs)')
for o in OPP:
    pair = Counter()
    for f in by[o]:
        for a, b, ro, v in f['dmg_pair']:
            if ro == 'them': pair[(a, b, 'out')] += v
            else: pair[(b, a, 'in')] += v
    keys = {(a, b) for a, b, _ in pair}
    rows = sorted(keys, key=lambda k: -(pair[(k[0], k[1], 'out')] + pair[(k[0], k[1], 'in')]))[:10]
    print(f'   {o}: ' + '; '.join(f"{a}->{b} {pair[(a,b,'out')]/1000:.0f}k vs {pair[(a,b,'in')]/1000:.0f}k" for a, b in rows))
