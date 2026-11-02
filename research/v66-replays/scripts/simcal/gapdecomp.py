# Ladder vs self-play gap in our champion's death within 10 rounds after an engaged stand_ok (r<=260), split
# (Kitagawa) into composition (how often each flag occurs) and rate within the strata.
# Flags: F our champion falls in the sim's own play-out; I an ally in the sim dealt nothing in 5 rounds; J enemies
# outside the sim hit our participants within 5 rounds; C Cassi & Issac among their fighters.
import sys, os, itertools
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import cf as CF
K = 5
def flags(x):
    return (int(bool(x['falls'])), int(any(i != x['self_i'] and sum(f['a_any'][:K]) == 0 for i, f in enumerate(x['us']))),
            int(bool(x['extra'])), int(any(f['typ'] in ('cassi', 'issac') for f in x['them'])))
def strata(rs):
    d = defaultdict(list)
    for x in rs: d[flags(x)].append(x['self_death'] is not None and x['self_death'] <= 10)
    return d
S = strata([x for x in CF.load('selfplay') if not x['lost']])
ld = [x for x in CF.load('ladder') if not x['lost']]
for name, rs in [('ladder', ld)] + [(o, [x for x in ld if x['opp'] == o]) for o in ('Fish', 'Mite', 'UoS', 'PBG')]:
    Lr = strata(rs)
    nS = sum(len(v) for v in S.values()); nL = sum(len(v) for v in Lr.values())
    rate = lambda d, k: sum(d[k]) / len(d[k]) if d.get(k) else None
    tot_S = sum(sum(v) for v in S.values()) / nS; tot_L = sum(sum(v) for v in Lr.values()) / nL
    comp = within = 0.0
    for k in set(S) | set(Lr):
        pS = len(S.get(k, [])) / nS; pL = len(Lr.get(k, [])) / nL
        rS = rate(S, k); rL = rate(Lr, k)
        if rS is None: rS = rL
        if rL is None: rL = rS
        comp += (pL - pS) * (rS + rL) / 2; within += (rL - rS) * (pS + pL) / 2
    # marginal prevalence and death rates per flag
    marg = []
    for i, f in enumerate('FIJC'):
        a = [v for k, vs in Lr.items() if k[i] for v in vs]; b = [v for k, vs in S.items() if k[i] for v in vs]
        marg.append('%s %.2f/%.2f (die %.3f/%.3f)' % (f, len(a) / nL, len(b) / nS, sum(a) / max(1, len(a)), sum(b) / max(1, len(b))))
    print('%-6s n=%d death10 %.3f vs self-play %.3f: gap %.3f = composition %.3f + within-strata %.3f | flag prevalence ladder/self (death rate): %s' % (
        name, nL, tot_L, tot_S, tot_L - tot_S, comp, within, '; '.join(marg)))
none = lambda d: d.get((0, 0, 0, 0), [])
print('no flag at all: self-play %d sims death10 %.3f' % (len(none(S)), sum(none(S)) / len(none(S))))
import narrow as N
for name, rs in (('self-play', [x for x in CF.load('selfplay') if not x['lost']]), ('ladder', ld)) + tuple((o, [x for x in ld if x['opp'] == o]) for o in ('Fish', 'Mite', 'UoS', 'PBG')):
    nf = [x for x in rs if flags(x)[:3] == (0, 0, 0)]; fl = [x for x in rs if flags(x)[:3] != (0, 0, 0)]
    a, na = N.share(nf); b, nb = N.share(fl)
    print('%-9s none of F/I/J: %.2f of ok, death10 %.3f, their first-death share %.2f (%d) | any of F/I/J: death10 %.3f, share %.2f (%d)' % (
        name, len(nf) / len(rs), sum(x['self_death'] is not None and x['self_death'] <= 10 for x in nf) / max(1, len(nf)), a, na,
        sum(x['self_death'] is not None and x['self_death'] <= 10 for x in fl) / max(1, len(fl)), b, nb))
