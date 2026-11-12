"""Locks, lock hits, teleports, recalls, wards: Mite against its opponents."""
import fl, collections
G = fl.load()
for v in fl.GROUPS:
    gs = [g for g in G if g['vg'] == v]; n = len(gs)
    for who in ('M', 'O'):
        L = []; LH = []; TP = []; RC = []; W = 0
        for g in gs:
            t = g['mite'] if who == 'M' else 1 - g['mite']
            L += [(x, g) for x in g['locks'] if x[2] == t]
            LH += [(x, g) for x in g['lockhits'] if x[2] == t]
            TP += [(x, g) for x in g['tps'] if x[2] == t]
            RC += [(x, g) for x in g['recalls'] if x[2] == t]
        on_trib = sum(1 for x, g in L if x[4]); first = [min(x[0] for x, g2 in L if g2 is g) for g in gs if any(g2 is g for x, g2 in L)]
        lside = collections.Counter(x[6] for x, g in L)
        print(f'{v} {who}: locks {len(L)/n:.2f}/game ({sum(1 for g in gs if any(g2 is g for x,g2 in L))/n:.0%} of games), on live enemy tribute {on_trib/max(1,len(L)):.0%}, '
              f'first median r{fl.med(first)}, sides ' + ', '.join(f'{k} {c/max(1,len(L)):.0%}' for k, c in lside.most_common()) +
              f'; one-altar-map locks {sum(1 for x,g in L if g["nalt"]==1)/max(1,sum(1 for g in gs if g["nalt"]==1)):.2f}/game')
        lh_bag = [x[4] for x, g in LH]
        print(f'   lock hits {len(LH)/n:.1f}/game; hitter bag 0: {sum(1 for b in lh_bag if b==0)/max(1,len(lh_bag)):.0%}, median bag {fl.med(lh_bag)}; nearest enemy median {fl.med([x[5] for x,g in LH])}')
        cross = [x for x, g in TP if x[7] is None or x[7] > x[6] + 2]
        print(f'   teleports {len(TP)/n:.2f}/game; wall-crossing (walk > cheb+2) {len(cross)/max(1,len(TP)):.0%}; bag median {fl.med([x[5] for x,g in TP])} (p75 {fl.q([x[5] for x,g in TP],.75)}); '
              f'enemy within 6 {sum(1 for x,g in TP if x[8]<=6)/max(1,len(TP)):.0%}; hp<.4 {sum(1 for x,g in TP if x[9]<.4)/max(1,len(TP)):.0%}; to side ' +
              ', '.join(f'{k} {c/max(1,len(TP)):.0%}' for k, c in collections.Counter(x[11] for x, g in TP).most_common()) +
              f'; median round {fl.med([x[0] for x,g in TP])}')
        byty = collections.Counter(g['name'][x[1]] for x, g in TP)
        print('   teleporters: ' + ', '.join(f'{k} {c/n:.2f}' for k, c in byty.most_common(6)))
        rc = [x for x, g in RC if x[4]]
        print(f'   completed recalls {len(RC)/n:.1f}/game; bag median {fl.med([x[3] or 0 for x,g in RC])} (bag>=10: {sum(1 for x,g in RC if (x[3] or 0)>=10)/max(1,len(RC)):.0%}); '
              f'at start hp<.4 {sum(1 for x in rc if x[4][2]<.4)/max(1,len(rc)):.0%}, enemy within 8 {sum(1 for x in rc if x[4][3]<=8)/max(1,len(rc)):.0%}; from side ' +
              ', '.join(f'{k} {c/max(1,len(RC)):.0%}' for k, c in collections.Counter(x[5] for x, g in RC).most_common()))
# wheel maps
print('\nwheel-like maps: teleports per game by map for Mite (r7) top 12')
by = collections.defaultdict(list)
for g in G:
    if g['vg'] == 'r7': by[g['map']].append(sum(1 for x in g['tps'] if x[2] == g['mite']))
for k, v in sorted(by.items(), key=lambda kv: -fl.mean(kv[1]))[:12]: print(f'   {k} {fl.mean(v):.1f} (n{len(v)})')
