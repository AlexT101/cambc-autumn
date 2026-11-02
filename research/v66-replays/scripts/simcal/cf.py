# Counterfactual re-sims of engaged sims: replace one input with what happened (hindsight) or change one model rule,
# and see how verdicts move and whether they predict the outcome better. Ladder (r<=260) vs self-play (r<=260).
# usage: cf.py [stand|chase|all]
import sys, os, json, gzip, math
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import simport as SP

kind = sys.argv[1] if len(sys.argv) > 1 else 'stand'
K = 5
NAMES = ['ryth', 'vesper', 'vendetta', 'cassi', 'issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'hor']


def load(src):
    rs = [json.loads(l) for l in gzip.open(f'replays/v66-analysis/simcal/l2_{src}.jsonl.gz', 'rt')]
    rs = [x for x in rs if x['r'] <= 260 and (kind == 'all' or x['kind'] == kind)]
    return [x for x in rs if sum(sum(f['a_part'][:K]) for f in x['us']) > 0 and sum(sum(f['a_part'][:K]) for f in x['them']) > 0]


def mk(f):
    g = SP.fighter(f['typ'], f['hp'], f['mx'], f['sh'], f['st'], f['arr'], f['rd'], f['foc'], f['fs'], taken=f['tk'], ident=f['h'])
    g.shield_until = f['shu']
    return g


def realised(f):
    exp = [k for k in range(K) if k >= f['arr'] and (f['death'] is None or f['death'] > k)]
    if not exp or f['pd'] <= 0: return 1.0
    return min(3.0, sum(f['a_any'][k] for k in exp) / (f['pd'] * len(exp)))


def engaged_f(f): return sum(f['a_any'][:K]) > 0 or sum(f['took'][:K]) > 0


def extra_fighter(e):
    if e['typ'] is None or e['hp'] is None: return None
    arr = next((k for k in range(K) if e['dmg'][k] > 0), K)
    kit, _ = SP.make_kit(e['typ'], e['st'], e['foc'], e['foc'])
    rd = [SP.NEVER if kit[s]['value'] <= 0 else int(e['cd'][s] or 0) for s in range(2)]
    st = e['st'] * (SP.hor_scale(type('F', (), {'health': e['hp'], 'max_health': e['mx']})) if e['typ'] == 'hor' else 1)
    return SP.fighter(e['typ'], e['hp'], e['mx'], 0, st, arr, rd, e['foc'], e['foc'], taken=e['tk'], ident=e['h'])


def sim(x, cf):
    us = list(x['us']); them = list(x['them'])
    opts = SP.Opts()
    self_i = x['self_i']
    if cf == 'roster':
        keep = [i for i, f in enumerate(us) if i == self_i or engaged_f(f)]
        self_i = keep.index(self_i); us = [us[i] for i in keep]
        them = [f for f in them if engaged_f(f)] or them[:1]
    U = [mk(f) for f in us]; T = [mk(f) for f in them]
    if cf in ('us_real', 'both_real'):
        for g, f in zip(U, us): g.mult = realised(f)
    if cf in ('them_real', 'both_real'):
        for g, f in zip(T, them): g.mult = realised(f)
    if cf == 'extra':
        for e in x['extra']:
            g = extra_fighter(e)
            if g and len(T) < 6: T.append(g)
    if cf in ('near', 'combo'):  # enemies the bot believed within 8, outside the sim, walking in
        for e in x.get('near', []):
            e2 = dict(e, dmg=[0] * K)
            g = extra_fighter(e2)
            if g and len(T) < 6:
                g.arrives = max(1, e['dist'] - 2); T.append(g)
    if cf in ('ci', 'combo'):  # Cassi with Issac in front: the pair falls through Issac
        if any(f['typ'] == 'issac' for f in them):
            for g, f in zip(T, them):
                if f['typ'] == 'cassi': g.untarget = True
    if cf == 'combo': opts.hor_dynamic = True
    if cf == 'reach':  # enemies we never damaged cannot be targeted (e.g. Cassi behind Issac)
        for g, f in zip(T, them):
            if sum(f['took'][:K]) == 0: g.untarget = True
    if cf == 'reach_us':
        for i, (g, f) in enumerate(zip(U, us)):
            if sum(f['took'][:K]) == 0 and i != self_i: g.untarget = True
    if cf == 'hor': opts.hor_dynamic = True
    if cf == 'vend': opts.vendetta_reset = True
    if cf == 'splash': opts.splash = 2.0
    Us = SP.Side(U, self_i, x['camp']); Ts = SP.Side(T)
    res = SP.simulate(Us, Ts, x['first'] == 't', opts=opts)
    for side in (Us, Ts):
        for g in side.f: g.health0 = g.health0
    import collect_l2 as CL
    res['U'] = Us; res['T'] = Ts
    return res['they_kill'] > 0, CL.margin(res), res['self_falls']


def auc(scores, ys):
    pos = [s for s, y in zip(scores, ys) if y]; neg = [s for s, y in zip(scores, ys) if not y]
    if not pos or not neg: return float('nan')
    allv = sorted([(s, 1) for s in pos] + [(s, 0) for s in neg])
    rank = 0; r = {}; i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]: j += 1
        for k in range(i, j): r.setdefault(k, (i + j + 1) / 2)
        i = j
    rp = sum(r[k] for k, (s, y) in enumerate(allv) if y)
    return (rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def died(d, h): return d is not None and d <= h


def xloss(x): return sum(died(f['death'], 10) for f in x['us']) > sum(died(f['death'], 10) for f in x['them'])


CFS = ['base', 'us_real', 'them_real', 'both_real', 'roster', 'extra', 'reach', 'reach_us', 'hor', 'vend', 'splash', 'near', 'ci', 'combo']

if __name__ == '__main__':
    for src in ('selfplay', 'ladder'):
        rs = load(src)
        groups = [('all', rs)] + ([(o, [x for x in rs if x['opp'] == o]) for o in ('Fish', 'Mite', 'UoS', 'PBG')] if src == 'ladder' else [])
        for gname, g in groups:
            ys = [xloss(x) for x in g]; yd = [died(x['self_death'], 10) for x in g]
            base_lost = [bool(x['lost']) for x in g]
            print('\n## %s %s engaged %s sims n=%d  xloss10 %.3f  self-death10 %.3f   [bot lost %.2f]' % (
                src, gname, kind, len(g), sum(ys) / len(g), sum(yd) / len(g), sum(base_lost) / len(g)))
            print('  %-10s %7s %8s %8s %8s %8s %8s %8s %8s' % ('cf', 'p_lost', 'ok->lost', 'lost->ok', 'mean_m', 'AUCx', 'AUCd', 'xl|ok', 'xl|lost'))
            for cf in CFS:
                out = [sim(x, cf) for x in g]
                lost = [o[0] for o in out]; m = [o[1] for o in out]
                if cf == 'base':
                    agree = sum(l == b for l, b in zip(lost, base_lost)) / len(g)
                okl = sum(1 for l, b in zip(lost, base_lost) if l and not b) / len(g)
                lok = sum(1 for l, b in zip(lost, base_lost) if not l and b) / len(g)
                ok_ = [y for y, l in zip(ys, lost) if not l]; lo_ = [y for y, l in zip(ys, lost) if l]
                print('  %-10s %7.3f %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f' % (
                    cf, sum(lost) / len(g), okl, lok, sum(m) / len(m), auc([-v for v in m], ys), auc([-v for v in m], yd),
                    sum(ok_) / max(1, len(ok_)), sum(lo_) / max(1, len(lo_))))
            print('  (base reproduces the bot verdict in %.3f)' % agree)
