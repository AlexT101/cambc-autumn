# Stand verdict ok while the full play-out has our own champion falling (the stand asks self_falls only when lethal or
# linked, combat/fight.cc want_home): how often, and what happened. Engaged stand sims r<=260.
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import cf as CF, race as RC, narrow as N
for src in ('selfplay', 'ladder'):
    rs = [x for x in CF.load(src) if not x['lost']]
    groups = [('all', rs)] + ([(o, [x for x in rs if x['opp'] == o]) for o in ('Fish', 'Mite', 'UoS', 'PBG')] if src == 'ladder' else [])
    for name, g in groups:
        out = []
        for lab, sel in (('self falls in play-out', [x for x in g if x['falls']]), ('self survives', [x for x in g if not x['falls']])):
            if not sel: continue
            d10 = sum(x['self_death'] is not None and x['self_death'] <= 10 for x in sel) / len(sel)
            sh, nd = N.share(sel)
            out.append('%s %.2f of ok (self death10 %.3f, their first-death share %.2f/%d)' % (lab, len(sel) / len(g), d10, sh, nd))
        print('%-8s %-5s n=%5d: ' % (src, name, len(g)) + ' | '.join(out))
