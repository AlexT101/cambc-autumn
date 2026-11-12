"""Convergence: after a first contact (enemy within 3 after 8 quiet rounds), do far teammates come?"""
import fl, collections
G = fl.load()
for v in ('v1', 'v2', 'r7'):
    for who in ('M', 'O'):
        rows = collections.defaultdict(list); fr = []; kills = []
        for g in G:
            if g['vg'] != v: continue
            t = g['mite'] if who == 'M' else 1 - g['mite']
            for r, tt, c0, x0, mates, nf, ne, k, side in g['conv']:
                if tt != t or r > 600: continue
                fr.append((nf, ne)); kills.append(k)
                for c, nm, ds, gems, camp in mates:
                    if ds[0] is None or nm == 'Issac' and g['name'][c0] == 'Cassi' or nm == 'Cassi' and g['name'][c0] == 'Issac': continue
                    b = '5-8' if 5 <= ds[0] <= 8 else '9-14' if 9 <= ds[0] <= 14 else None
                    if b and ds[2] is not None: rows[b].append((ds[0] - ds[2], ds[2] <= 4, ds[3] is not None and ds[3] <= 4, gems > 0))
        print(f'{v} {who}: contacts {len(fr)}; own/enemy bodies within 8 {fl.mean(a for a,b in fr):.2f}/{fl.mean(b for a,b in fr):.2f}; net kills in 12 rounds {fl.mean(k[0]-k[1] for k in kills):+.2f}')
        for b in ('5-8', '9-14'):
            rs = rows[b]
            if rs: print(f'   mates at {b}: n={len(rs)} closed by {fl.mean(x[0] for x in rs):.1f} in 6 rounds; within 4 by +6 {sum(x[1] for x in rs)/len(rs):.2f}, by +10 {sum(x[2] for x in rs)/len(rs):.2f}; carriers {sum(x[3] for x in rs)/len(rs):.2f}')
