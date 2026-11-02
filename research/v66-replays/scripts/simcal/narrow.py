# Verdict-ok engaged stand sims by margin band: realised inputs vs the sim, and counterfactual flips, ladder vs self-play.
# Game-clustered bootstrap intervals on the first-death share.
import sys, os, json, gzip, random
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import cf as CF
import race as RC
K = 5


def share(rs):
    th = sum(1 for x in rs if RC.first(x) in ('theirs', 'same')); ou = sum(1 for x in rs if RC.first(x) == 'ours')
    return th / max(1, th + ou), th + ou


def boot(rs, n=400):
    by = defaultdict(list)
    for x in rs: by[x['key']].append(x)
    ks = list(by); out = []
    random.seed(1)
    for _ in range(n):
        s = [y for k in random.choices(ks, k=len(ks)) for y in by[k]]
        out.append(share(s)[0])
    out.sort()
    return out[int(0.025 * n)], out[int(0.975 * n)]


def inputs(rs):
    S = defaultdict(float)
    for x in rs:
        for side in ('us', 'them'):
            for f in x[side]:
                exp = [k for k in range(K) if k >= f['arr'] and (f['death'] is None or f['death'] > k)]
                S[side + 'p'] += f['pd'] * len(exp); S[side + 'a'] += sum(f['a_any'][:K])
                S[side + 'exp'] += len(exp); S[side + 'hit'] += sum(1 for k in exp if f['a_hits'][k] > 0)
                S[side + 'heal'] += sum(f['healed'][:K]); S[side + 'camp'] += sum(f['camp'][:K])
        S['extra'] += sum(sum(e['dmg'][:K]) for e in x['extra'])
        w = min(x['them'], key=lambda f: f['hp'] + f['sh'])
        S['foc_n'] += sum(w['took'][:K]); S['foc_d'] += sum(sum(f['took'][:K]) for f in x['them'])
        tgt = next(f for f in x['us'] if f['h'] == x['sim_target'])
        S['tfoc_n'] += sum(tgt['took'][:K]); S['tfoc_d'] += sum(sum(f['took'][:K]) for f in x['us'])
        S['n_us'] += len(x['us']); S['n_them'] += len(x['them']); S['n_extra'] += len(x['extra'])
        S['ci'] += any(f['typ'] in ('cassi', 'issac') for f in x['them'])
    n = len(rs)
    return ('our dmg real/pred %.2f (hit %.2f) | their %.2f (hit %.2f) | outsiders %.2f of their pred | our focus on weakest %.2f, theirs on sim target %.2f | '
            'heal them %.0f us %.0f | camp us %.0f them %.0f | roster %.1f v %.1f, outsiders/sim %.2f | C&I in sim %.2f') % (
        S['usa'] / S['usp'], S['ushit'] / S['usexp'], S['thema'] / S['themp'], S['themhit'] / S['themexp'], S['extra'] / S['themp'],
        S['foc_n'] / max(1, S['foc_d']), S['tfoc_n'] / max(1, S['tfoc_d']), S['themheal'] / n, S['usheal'] / n, S['uscamp'] / n, S['themcamp'] / n,
        S['n_us'] / n, S['n_them'] / n, S['n_extra'] / n, S['ci'] / n)


if __name__ == '__main__':
    data = {'self': CF.load('selfplay'), 'ladder': CF.load('ladder')}
    for o in ('Fish', 'Mite', 'UoS', 'PBG'): data[o] = [x for x in data['ladder'] if x['opp'] == o]
    for band, sel in (('ok margin<0.3', lambda x: not x['lost'] and x['margin'] < 0.3), ('ok margin>=0.3', lambda x: not x['lost'] and x['margin'] >= 0.3),
                      ('lost', lambda x: x['lost'])):
        print('\n######## ' + band)
        for name, rs in data.items():
            g = [x for x in rs if sel(x)]
            if len(g) < 30: continue
            sh, nd = share(g); lo, hi = boot(g)
            print('\n## %s n=%d (games %d), their share of first deaths %.2f [%.2f, %.2f] of %d decided' % (name, len(g), len({x['key'] for x in g}), sh, lo, hi, nd))
            print('   ' + inputs(g))
            line = []
            for cf in CF.CFS[1:]:
                out = [CF.sim(x, cf) for x in g]
                fl = [x for x, o in zip(g, out) if o[0] != bool(x['lost'])]
                s2, n2 = share(fl)
                line.append('%s %.2f(%.2f/%d)' % (cf, len(fl) / len(g), s2, n2))
            print('   flips [share flipped (their first-death share among flipped/decided)]: ' + '  '.join(line))
