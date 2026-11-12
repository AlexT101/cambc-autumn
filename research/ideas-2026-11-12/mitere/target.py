"""Target choice in fights: basic attacks and unit spells with 2+ enemy champions in reach."""
import fl, collections
G = fl.load()
UNIT_SPELLS = None
for v in ('v1', 'v2', 'r7'):
    for who in ('M', 'O'):
        S = collections.Counter(); n = collections.Counter(); bytype = collections.Counter(); exp = collections.Counter()
        for g in G:
            if g['vg'] != v: continue
            t = g['mite'] if who == 'M' else 1 - g['mite']
            for r, a, kind, tg, cands in g['targ']:
                if g['team'][a] != t or len(cands) < 2 or tg not in [c[0] for c in cands]: continue
                k = 'atk' if kind == 'attack' else 'spell'
                ch = next(c for c in cands if c[0] == tg)
                lo_abs = min(c[2] for c in cands); lo_fr = min(c[1] for c in cands); nd = min(c[4] for c in cands); mg = max(c[3] for c in cands)
                n[k] += 1
                S[(k, 'lowest_abs')] += ch[2] == lo_abs; S[(k, 'lowest_frac')] += ch[1] == lo_fr; S[(k, 'nearest')] += ch[4] == nd
                if mg > 0: n[(k, 'carrier')] += 1; S[(k, 'most_gems')] += ch[3] == mg
                if any(c[6] for c in cands): n[(k, 'chan')] += 1; S[(k, 'channeler')] += bool(ch[6])
                # conflicts: nearest != lowest abs
                near = [c for c in cands if c[4] == nd]; low = [c for c in cands if c[2] == lo_abs]
                if not set(x[0] for x in near) & set(x[0] for x in low):
                    n[(k, 'conf')] += 1; S[(k, 'conf_low')] += ch[2] == lo_abs; S[(k, 'conf_near')] += ch[4] == nd
                # among equally near
                if len(near) >= 2 and tg in [x[0] for x in near]:
                    n[(k, 'eqnear')] += 1; S[(k, 'eq_low')] += ch[2] == min(x[2] for x in near); S[(k, 'eq_lowfr')] += ch[1] == min(x[1] for x in near)
                    if max(x[3] for x in near) > 0: n[(k, 'eqg')] += 1; S[(k, 'eq_gems')] += ch[3] == max(x[3] for x in near)
                bytype[ch[5]] += 1
                for c in cands: exp[c[5]] += 1 / len(cands)
        for k in ('atk', 'spell'):
            if not n[k]: continue
            print(f'{v} {who} {k} n={n[k]}: lowest hp {S[(k,"lowest_abs")]/n[k]:.2f}, lowest frac {S[(k,"lowest_frac")]/n[k]:.2f}, nearest {S[(k,"nearest")]/n[k]:.2f}, '
                  f'most gems {S[(k,"most_gems")]/max(1,n[(k,"carrier")]):.2f} (n{n[(k,"carrier")]}), channeler {S[(k,"channeler")]/max(1,n[(k,"chan")]):.2f} (n{n[(k,"chan")]}); '
                  f'near!=low (n{n[(k,"conf")]}): low {S[(k,"conf_low")]/max(1,n[(k,"conf")]):.2f} near {S[(k,"conf_near")]/max(1,n[(k,"conf")]):.2f}; '
                  f'eq-near (n{n[(k,"eqnear")]}): low {S[(k,"eq_low")]/max(1,n[(k,"eqnear")]):.2f} lowfr {S[(k,"eq_lowfr")]/max(1,n[(k,"eqnear")]):.2f} gems {S[(k,"eq_gems")]/max(1,n[(k,"eqg")]):.2f}')
        tot = sum(bytype.values())
        print('   chosen/expected by type: ' + ', '.join(f'{k} {bytype[k]/exp[k]:.2f}' for k in sorted(exp, key=lambda k: -bytype[k] / exp[k]) if exp[k] > 20))
# focus fire: share of a team's champion damage in a round on its top target, rounds with 2+ attackers... use focus rows
print('\nFocus: rounds where a team damaged 2+ enemy champions or one with 2+ hits')
for v in ('v1', 'v2', 'r7'):
    for who in ('M', 'O'):
        tops = []; ntg = collections.Counter()
        for g in G:
            if g['vg'] != v: continue
            t = g['mite'] if who == 'M' else 1 - g['mite']
            for r, tt, d in g['focus']:
                if tt != t: continue
                tot = sum(d.values())
                if tot <= 0: continue
                ntg[min(len(d), 4)] += 1
                if len(d) >= 2: tops.append(max(d.values()) / tot)
        s = sum(ntg.values())
        print(f'  {v} {who}: rounds with champion damage {s}; targets hit 1/2/3/4+: ' + ' '.join(f'{ntg[i]/s:.2f}' for i in (1, 2, 3, 4)) + f'; top target share when 2+ hit {fl.mean(tops):.2f}')
