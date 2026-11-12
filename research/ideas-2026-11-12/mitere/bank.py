"""Tributes, banking and carry: Mite against its opponents."""
import fl, collections
G = fl.load()
for v in fl.GROUPS:
    gs = [g for g in G if g['vg'] == v]
    for who in ('M', 'O'):
        T = []; first = []; payers = collections.Counter(); out = collections.Counter(); sides = collections.Counter(); fin = 0; nfin = 0
        for g in gs:
            t = g['mite'] if who == 'M' else 1 - g['mite']
            tr = [x for x in g['tribs'] if x[2] == t]
            if tr: first.append(tr[0][0])
            for x in tr:
                T.append(x); payers[g['name'][x[1]]] += 1; out[x[6] if x[6] in ('end', None) else ('cancel:' + str(x[6]))] += 1; sides[x[11]] += 1
                if x[3] + x[12] >= 1000: fin += 1; nfin += x[6] == 'end'
        n = len(gs); bags = [x[3] for x in T]
        print(f'{v} {who}: {len(T)/n:.1f} tributes/game, bag p25/50/75/90 {fl.q(bags,.25)}/{fl.q(bags,.5)}/{fl.q(bags,.75)}/{fl.q(bags,.9)}, first r{fl.med(first)}; '
              f'complete {out["end"]/max(1,len(T)):.0%}; ' + ', '.join(f'{k} {c/len(T):.0%}' for k, c in out.most_common(5) if k != 'end'))
        print(f'   altars: ' + ', '.join(f'{k} {c/len(T):.0%}' for k, c in sides.most_common()) + ' | payers: ' + ', '.join(f'{k} {c/len(T):.0%}' for k, c in payers.most_common(7)) +
              f' | finisher starts (bag+banked>=1000) {fin/n:.2f}/game, completed {nfin}/{fin}')
        # context at start: nearest enemy, allies within 3, hp
        ne = [x[9] for x in T]; al = [x[10] for x in T]
        print(f'   start context: nearest enemy median {fl.med(ne)} (<=4: {sum(1 for d in ne if d<=4)/max(1,len(ne)):.0%}), allies within 3 mean {fl.mean(al):.2f}, hp median {fl.med([x[14] for x in T])}')
        # bag by round bucket
        bb = collections.defaultdict(list)
        for x in T: bb[min(x[0] // 200, 5)].append(x[3])
        print('   median bag by round: ' + ' '.join(f'r{k*200}+:{fl.med(b)}(n{len(b)})' for k, b in sorted(bb.items())))
# carry by champion type at checkpoints (Mite), r7 and v2
print('\nMite carry per champion, median / p90, at r200/400/600')
for v in ('v1', 'v2', 'r7'):
    gs = [g for g in G if g['vg'] == v]
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for g in gs:
        for r in ('200', '400', '600'):
            if r not in g['ck']: continue
            for c, val in g['ck'][r]['cc'].items():
                c = int(c)
                if g['team'][c] == g['mite']: by[g['name'][c]][r].append(val)
    print(v, ' | '.join(f'{k}: ' + ' '.join(f'{fl.med(by[k][r])}/{fl.q(by[k][r],.9)}' for r in ('200', '400', '600')) for k in sorted(by)))
