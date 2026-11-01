# Q1 aggregation: economy curves, opening captures, invasion, steals, contested camps, grouping.
import json, glob, statistics as st, sys
from collections import defaultdict, Counter
S = 'replays/v66-analysis'
F = [json.load(open(p)) for p in glob.glob(S + '/opp/feat/*.json')]
OPP = ['Fish', 'Mite', 'UoS', 'PBG']
CK = [50, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000]
by = defaultdict(list)
for f in F: by[f['opp']].append(f)
mean = lambda a: sum(a) / len(a) if a else float('nan')


def sides(f):
    return f['us'], 1 - f['us']


print('== Lifetime collected gems (captures+kill gems), mean over games alive at checkpoint; us / them')
for o in OPP:
    xs = by[o]
    row = []
    for i, c in enumerate(CK[:8]):
        a = [f['cum'][f['us']][i] for f in xs if f['cum'][f['us']][i] is not None]
        b = [f['cum'][1 - f['us']][i] for f in xs if f['cum'][1 - f['us']][i] is not None]
        row.append(f'{c}:{mean(a):.0f}/{mean(b):.0f}(n{len(a)})')
    print(o, ' '.join(row))
print('== Lifetime earned gold, us/them')
for o in OPP:
    xs = by[o]; row = []
    for i, c in enumerate(CK[:8]):
        a = [f['gold'][f['us']][i] for f in xs if f['gold'][f['us']][i] is not None]
        b = [f['gold'][1 - f['us']][i] for f in xs if f['gold'][1 - f['us']][i] is not None]
        row.append(f'{c}:{mean(a):.0f}/{mean(b):.0f}')
    print(o, ' '.join(row))
print('== Gems from captures only (cum minus kill) at r200 is in cycles; kill gems total us/them')
for o in OPP:
    xs = by[o]
    print(o, 'killgems us %.0f them %.0f' % (mean([f['killgems'][f['us']] for f in xs]), mean([f['killgems'][1 - f['us']] for f in xs])))

# per-map consistency of r200 / r300 lead
print('== Per-map: maps where opp mean collected gems at r200 (r400) > ours; and game-level share')
for o in OPP:
    for i in (3, 5):
        pm = defaultdict(lambda: [[], []])
        gl = 0; gn = 0
        for f in by[o]:
            a, b = f['cum'][f['us']][i], f['cum'][1 - f['us']][i]
            if a is None: continue
            pm[f['map']][0].append(a); pm[f['map']][1].append(b)
            gn += 1; gl += b > a
        k = sum(1 for m, (a, b) in pm.items() if mean(b) > mean(a))
        print(f'{o} r{CK[i]}: opp ahead on {k}/{len(pm)} maps; in {gl}/{gn} games')


def caps(f, t, lo, hi):
    return [c for c in f['cycles'] if c['cap'] == t and lo <= c['cap_r'] <= hi]


print('\n== Opening captures r1-200 per game: n, gems, by class (gems), by side (gems), mean dist rank of captured groups, frac solo')
for o in OPP:
    for who in ('us', 'them'):
        xs = by[o]
        n = []; gm = []; cls = Counter(); rel = Counter(); rk = []; solo = []; clsn = Counter()
        for f in xs:
            t = f['us'] if who == 'us' else 1 - f['us']
            cs = caps(f, t, 1, 200)
            n.append(len(cs)); gm.append(sum(c['gems'] for c in cs))
            for c in cs:
                cls[c['cls']] += c['gems']; clsn[c['cls']] += 1; rel[c['rel'][t]] += c['gems']; rk.append(c['rank'][t] / max(1, f['ngroups'] - 1)); solo.append(c['shares'] == 1)
        tot = sum(cls.values())
        print(f"{o:5}{who:5} caps {mean(n):5.1f} gems {mean(gm):5.1f} | " + ' '.join(f"{k}:{v/len(xs):.1f}g/{clsn[k]/len(xs):.1f}n" for k, v in sorted(cls.items())) +
              ' | side ' + ' '.join(f"{k}:{v/max(1,tot)*100:.0f}%" for k, v in sorted(rel.items())) + f' | rankpct {mean(rk):.2f} solo {mean(solo)*100:.0f}%')

print('\n== First capture round per class (median over games where it happened; % games happened by r400)')
for o in OPP:
    for who in ('us', 'them'):
        out = []
        for cl in ('gem', 'wolf', 'elk', 'golem', 'mono'):
            rs = []; have = 0; tot = 0
            for f in by[o]:
                t = f['us'] if who == 'us' else 1 - f['us']
                if not any(c['cls'] == cl for c in f['cycles']) and not any(True for c in f['cycles']): continue
                # does the map have this class at all? approximate: any cycle of that class by anyone
                if not any(c['cls'] == cl for c in f['cycles']): continue
                tot += 1
                r = min([c['cap_r'] for c in f['cycles'] if c['cap'] == t and c['cls'] == cl], default=None)
                if r is not None and r <= 400: have += 1
                if r is not None: rs.append(r)
            out.append(f"{cl}:{st.median(rs) if rs else '-'}({have}/{tot})")
        print(f'{o:5}{who:5}', ' '.join(out))

print('\n== Whole game: captures on enemy side (invasion), % of capture gems; steals')
# steal: capture where the other team dealt > 50% of the cycle's camp damage (camp groups with hp>0)
for o in OPP:
    for who in ('us', 'them'):
        inv = []; st_n = []; st_g = []; cl_other = []; woke_other = []; tot_g = []
        for f in by[o]:
            t = f['us'] if who == 'us' else 1 - f['us']
            cs = [c for c in f['cycles'] if c['cap'] == t]
            g = sum(c['gems'] for c in cs); tot_g.append(g)
            inv.append(sum(c['gems'] for c in cs if c['rel'][t] == 'enemy'))
            s = [c for c in cs if sum(c['dmg']) > 0 and c['dmg'][1 - t] > 0.5 * sum(c['dmg'])]
            st_n.append(len(s)); st_g.append(sum(c['gems'] for c in s))
            cl_other.append(sum(1 for c in cs if c['clearer'] == 1 - t))
        print(f"{o:5}{who:5} capgems {mean(tot_g):6.0f} invasion {sum(inv)/max(1,sum(tot_g))*100:4.1f}% | steals(other>50% dmg) {mean(st_n):4.2f}/game {mean(st_g):5.1f} gems/game | cleared-by-other {mean(cl_other):.2f}/game")

print('\n== Contested cycles: both teams dealt >=10% of damage, or both held. Capture share by team; first 3 contested of game')
for o in OPP:
    won = Counter(); first = Counter(); first_g = Counter(); nn = 0
    early = Counter()
    for f in by[o]:
        u = f['us']
        cs = [c for c in f['cycles'] if (sum(c['dmg']) > 0 and min(c['dmg']) >= 0.1 * sum(c['dmg'])) or len(c['holds']) == 2]
        cs.sort(key=lambda c: c['cap_r'])
        for c in cs:
            won['us' if c['cap'] == u else 'them'] += 1
        for c in cs[:3]:
            first['us' if c['cap'] == u else 'them'] += 1; first_g['us' if c['cap'] == u else 'them'] += c['gems']
        for c in cs:
            if c['cap_r'] <= 200: early['us' if c['cap'] == u else 'them'] += 1
        nn += 1
    print(f"{o:5} all contested: us {won['us']} them {won['them']} ({won['us']/max(1,sum(won.values()))*100:.0f}% us) | first3: us {first['us']} them {first['them']} gems us {first_g['us']} them {first_g['them']} | r<=200: us {early['us']} them {early['them']}")

print('\n== Territory: % of off-spawn champion-rounds in enemy half (walk dist), r<=200 and r>200; % within 6 of enemy spawn')
for o in OPP:
    for who in ('us', 'them'):
        e1 = e2 = n1 = n2 = 0; ns = nt = 0
        for f in by[o]:
            t = f['us'] if who == 'us' else 1 - f['us']
            a, b, c, d = f['terr'][t]; e1 += a; n1 += b; e2 += c; n2 += d
            ns += f['nes'][t][0]; nt += f['nes'][t][1]
        print(f'{o:5}{who:5} enemy-half early {e1/n1*100:4.1f}% late {e2/n2*100:4.1f}% | near enemy spawn {ns/nt*100:.2f}%')

print('\n== Grouping: max pairwise Chebyshev spread of off-spawn alive champions (median of game medians), % rounds spread<=6; capture sharers')
for o in OPP:
    for who in ('us', 'them'):
        m0 = []; m1 = []; l0 = []; l1 = []; sh = []
        for f in by[o]:
            t = f['us'] if who == 'us' else 1 - f['us']
            s = f['spread'][t]
            if s[0]['med'] is not None: m0.append(s[0]['med']); l0.append(s[0]['le6'])
            if s[1]['med'] is not None: m1.append(s[1]['med']); l1.append(s[1]['le6'])
            sh += [c['shares'] for c in f['cycles'] if c['cap'] == t]
        print(f'{o:5}{who:5} spread r<=300 med {st.median(m0):.0f} le6 {mean(l0)*100:.0f}% | r>300 med {st.median(m1) if m1 else "-"} le6 {mean(l1)*100:.0f}% | sharers/capture {mean(sh):.2f} solo {sum(1 for x in sh if x==1)/len(sh)*100:.0f}%')
