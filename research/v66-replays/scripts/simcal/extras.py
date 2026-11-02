# Focus concentration, stuns predicted vs realised, Cassi-as-weakest fights, time to our fall: engaged stand sims r<=260.
import sys, os, json, statistics as st
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(__file__))
import cf as CF
import race as RC
import simport as SP
K = 5


def pred_stuns(x):
    """Stuns their side casts in the sim's first K of their turns (base model)."""
    U = [CF.mk(f) for f in x['us']]; T = [CF.mk(f) for f in x['them']]
    Us = SP.Side(U, x['self_i'], x['camp']); Ts = SP.Side(T)
    n = 0; theirs = 0; t = 0
    they_first = x['first'] == 't'
    while theirs < K and t < 2 * SP.HORIZON:
        if (t % 2 == 0) == they_first:
            before = Us.stunned
            SP.act(Ts, Us, SP.Opts(), False); theirs += 1
            n += Us.stunned - before
        else:
            SP.act(Us, Ts, SP.Opts(), True)
        if Us.alive == 0 or Ts.alive == 0: break
        t += 1
    return n


if __name__ == '__main__':
    for src in ('selfplay', 'ladder'):
        rs = CF.load(src)
        groups = [('all', rs)] + ([(o, [x for x in rs if x['opp'] == o]) for o in ('Fish', 'Mite', 'UoS', 'PBG')] if src == 'ladder' else [])
        for name, g in groups:
            top_t = []; top_u = []; self_top = 0; ps = 0; as_ = 0
            for x in g:
                took = [sum(f['took'][:K]) for f in x['us']]
                if sum(took) > 0:
                    top_t.append(max(took) / sum(took)); self_top += took.index(max(took)) == x['self_i']
                tk = [sum(f['took'][:K]) for f in x['them']]
                if sum(tk) > 0: top_u.append(max(tk) / sum(tk))
                ps += pred_stuns(x); as_ += x['stuns_on_us']
            print('\n## %s %s n=%d: top-target share of damage: theirs %.2f, ours %.2f; their top target is our self %.2f; '
                  'stuns on us in %d rounds: sim %.2f, real %.2f per sim' % (src, name, len(g), sum(top_t) / len(top_t), sum(top_u) / len(top_u),
                                                                            self_top / len(top_t), K, ps / len(g), as_ / len(g)))
            # Cassi the sim's target on their side (weakest), Issac also in: our damage on each, first deaths
            cg = [x for x in g if not x['lost'] and any(f['typ'] == 'issac' for f in x['them']) and min(x['them'], key=lambda f: f['hp'] + f['sh'])['typ'] == 'cassi']
            if cg:
                dc = sum(sum(f['took'][:K]) for x in cg for f in x['them'] if f['typ'] == 'cassi')
                di = sum(sum(f['took'][:K]) for x in cg for f in x['them'] if f['typ'] == 'issac')
                do = sum(sum(f['took'][:K]) for x in cg for f in x['them'] if f['typ'] not in ('cassi', 'issac'))
                sh, nd = __import__('narrow').share(cg)
                print('   verdict ok with Cassi their weakest and Issac in: n=%d; our damage on Cassi %.0f%%, Issac %.0f%%, others %.0f%%; their share of first deaths %.2f (%d)' % (
                    len(cg), 100 * dc / max(1, dc + di + do), 100 * di / max(1, dc + di + do), 100 * do / max(1, dc + di + do), sh, nd))
            # time to our fall: lost verdicts where the sim has our self falling, and it died within 20 rounds
            tf = [(x['fall_turn'], x['self_death']) for x in g if x['falls'] and x['fall_turn'] and x['self_death'] is not None]
            if tf:
                print('   self falls in sim and died: n=%d, predicted fall turn median %.0f, actual rounds to death median %.0f, ratio of means %.2f' % (
                    len(tf), st.median(a for a, b in tf), st.median(b for a, b in tf), sum(b for a, b in tf) / sum(a for a, b in tf)))
            fl = [x for x in g if x['falls'] and x['fall_turn']]
            if fl: print('   self falls in sim: died within 2x the predicted turns %.2f, within 20 rounds %.2f (n=%d)' % (
                sum(x['self_death'] is not None and x['self_death'] <= 2 * x['fall_turn'] for x in fl) / len(fl),
                sum(x['self_death'] is not None for x in fl) / len(fl), len(fl)))
