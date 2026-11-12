"""Captures and income: Mite against its opponents, by version group."""
import fl, collections
G = fl.load()
def row(gs, who):
    n = len(gs); A = collections.Counter(); first = collections.Counter(); firstr = []; side = collections.Counter(); share_g = collections.Counter(); share_gold = collections.Counter()
    big = collections.Counter(); rank1 = collections.Counter(); gemsc = []; goldc = []
    for g in gs:
        t = g['mite'] if who == 'M' else 1 - g['mite']
        cs = [c for c in g['caps'] if c[2] == t]
        for lim in (100, 200, 300, 600): A[lim] += sum(1 for c in cs if c[0] <= lim)
        gemsc.append(sum(sh[1] for c in cs if c[0] <= 300 for sh in c[3])); goldc.append(sum(sh[2] for c in cs if c[0] <= 300 for sh in c[3]))
        if cs:
            c0 = cs[0]; first[fl.gtype(c0[4])] += 1; firstr.append(c0[0])
            # distance rank of the first capture among groups by walk distance from own spawn
            ds = sorted((q[6 + t] if q[6 + t] is not None else 999, q[0]) for q in g['groups'])
            rk = [x[1] for x in ds].index(c0[1]) if c0[1] in [x[1] for x in ds] else 99
            rank1[min(rk, 4)] += 1
        for c in cs:
            if c[0] <= 300: side[c[7]] += 1
            ty = fl.gtype(c[4])
            if ty.startswith(('Golem', 'Monolith')): big[(ty, c[0] <= 300)] += 1
            for cid, gm, gd in c[3]:
                share_g[g['name'][cid]] += gm; share_gold[g['name'][cid]] += gd
    print(f'  {who} n={n} caps r100/200/300/600: ' + ' '.join(f'{A[l]/n:.1f}' for l in (100, 200, 300, 600)) +
          f' | gems/gold captured to r300 {fl.mean(gemsc):.0f}/{fl.mean(goldc):.0f} | first cap median r{fl.med(firstr)}')
    tot = sum(first.values())
    print('   first capture type: ' + ', '.join(f'{k} {v/tot:.0%}' for k, v in first.most_common(6)) + ' | dist rank: ' + ', '.join(f'{k}:{v/tot:.0%}' for k, v in sorted(rank1.items())))
    ts = sum(side.values()); print('   sides to r300: ' + ', '.join(f'{k} {v/ts:.0%}' for k, v in side.most_common()) + f' | Golem/Monolith caps a game (to r300, all): ' +
                                  ', '.join(f'{k[0]}{"<300" if k[1] else ""} {v/n:.2f}' for k, v in sorted(big.items())))
    sg = sum(share_g.values()); sgo = sum(share_gold.values())
    print('   gem shares: ' + ', '.join(f'{k} {v/sg:.0%}' for k, v in share_g.most_common(7)) + ' | gold: ' + ', '.join(f'{k} {v/sgo:.0%}' for k, v in share_gold.most_common(7)))
for v in fl.GROUPS:
    gs = [g for g in G if g['vg'] == v]
    print(v, len(gs))
    row(gs, 'M'); row(gs, 'O')
# checkpoint diffs
print('\nMite minus opponent at checkpoints (banked gems / earned gold / kills), mean')
for v in fl.GROUPS:
    for res in (True, False):
        gs = [g for g in G if g['vg'] == v and g['win'] == res]
        s = []
        for r in ('100', '200', '400', '600', '1000'):
            xs = [(g['ck'][r]['gems'][g['mite']] - g['ck'][r]['gems'][1 - g['mite']], g['ck'][r]['earned'][g['mite']] - g['ck'][r]['earned'][1 - g['mite']],
                   g['ck'][r]['kills'][g['mite']] - g['ck'][r]['kills'][1 - g['mite']], g['ck'][r]['carry'][g['mite']] - g['ck'][r]['carry'][1 - g['mite']]) for g in gs if r in g['ck']]
            if xs: s.append(f'r{r} {fl.mean(x[0] for x in xs):+.0f}/{fl.mean(x[1] for x in xs):+.0f}/{fl.mean(x[2] for x in xs):+.1f}/c{fl.mean(x[3] for x in xs):+.0f}')
        print(f' {v} {"Mite wins" if res else "Mite loses"} n={len(gs)}: ' + '  '.join(s))
