# Multi-fighter engaged stand sims, verdict ok (r<=260): sim members who took no part in the exchange (no champion damage
# dealt or taken within 5 rounds), and enemies who joined from outside the sim.
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import cf as CF, narrow as N
K = 5
for src in ('selfplay', 'ladder'):
    rs = [x for x in CF.load(src) if not x['lost'] and x['n_us'] + x['n_them'] > 2]
    groups = [('all', rs)] + ([(o, [x for x in rs if x['opp'] == o]) for o in ('Fish', 'Mite', 'UoS', 'PBG')] if src == 'ladder' else [])
    for name, g in groups:
        al = [f for x in g for i, f in enumerate(x['us']) if i != x['self_i']]
        idle_al = sum(1 for f in al if sum(f['a_any'][:K]) == 0 and sum(f['took'][:K]) == 0)
        nodmg_al = sum(1 for f in al if sum(f['a_any'][:K]) == 0)
        th = [f for x in g for f in x['them']]
        idle_th = sum(1 for f in th if sum(f['a_any'][:K]) == 0 and sum(f['took'][:K]) == 0)
        ext = sum(len(x['extra']) for x in g)
        # sims where at least one ally of ours was idle: outcome
        gi = [x for x in g if any(i != x['self_i'] and sum(f['a_any'][:K]) == 0 for i, f in enumerate(x['us']))]
        gn = [x for x in g if x not in gi]
        a, na = N.share(gi); b, nb = N.share(gn)
        print('%-8s %-5s n=%4d allies/sim %.2f: dealt nothing %.2f (idle %.2f) | enemies/sim %.2f idle %.2f | outsiders/sim %.2f | '
              'first-death share with an ally dealing nothing %.2f (%d) vs all allies hitting %.2f (%d)' % (
                  src, name, len(g), len(al) / len(g), nodmg_al / max(1, len(al)), idle_al / max(1, len(al)), len(th) / len(g), idle_th / max(1, len(th)),
                  ext / len(g), a, na, b, nb))
