"""Summaries of fx.pkl: flips, divergence, plan following, farm-target churn, captures by side, deaths."""
import pickle, sys, collections, numpy as np
rows = pickle.load(open(sys.argv[1], 'rb'))
H = int(sys.argv[2]) if len(sys.argv) > 2 else 100


def churn(D, ids, us_ids, lim=H):
    # farm_group changes per own champion over rounds <= lim, counting only changes between two groups >= 0
    n = 0; t = 0
    for h, d in D.items():
        prev = None
        for r in sorted(d):
            if r > lim: break
            g = d[r][1]
            if g >= 0 and prev is not None and prev >= 0 and g != prev: n += 1
            if g >= 0: prev = g
            t += 1
    return n


def m(xs): return np.mean(xs) if len(xs) else float('nan')


def caps(G, lim, ours, s_lo, s_hi):
    return sum(1 for c in G['caps'] if c[0] <= lim and c[2] == ours and s_lo <= G['gside'].get(c[1], 0) < s_hi)


def capv(G, lim, ours):
    return sum(c[3] + 0.3 * c[4] for c in G['caps'] if c[0] <= lim and c[2] == ours)


cls = collections.defaultdict(list)
for r in rows:
    k = {(True, False): 'gain', (False, True): 'loss'}.get((r['C']['win'], r['B']['win']), 'same')
    cls[k].append(r)
print({k: len(v) for k, v in cls.items()}, 'n', len(rows), 'cand win', m([r['C']['win'] for r in rows]), 'base side win', m([r['B']['win'] for r in rows]))
divs = [r['div'] for r in rows]
print('no divergence by r400:', sum(d is None for d in divs), ' div quantiles', np.percentile([d for d in divs if d], [10, 25, 50, 75, 90]))
for k in ('gain', 'loss', 'same'):
    v = cls[k]
    print(f'--- {k} n {len(v)} div median {np.median([r["div"] or 999 for r in v]):.0f}')
    for lim in (100, 150, 200):
        print(f'  r{lim} gold u C/B {m([r["C"][f"gold{lim}u"] for r in v]):.0f}/{m([r["B"][f"gold{lim}u"] for r in v]):.0f}'
              f'  o {m([r["C"][f"gold{lim}o"] for r in v]):.0f}/{m([r["B"][f"gold{lim}o"] for r in v]):.0f}'
              f'  gems u {m([r["C"][f"own{lim}u"] for r in v]):.1f}/{m([r["B"][f"own{lim}u"] for r in v]):.1f}'
              f'  o {m([r["C"][f"own{lim}o"] for r in v]):.1f}/{m([r["B"][f"own{lim}o"] for r in v]):.1f}')
    for lim in (100, 150):
        dU = m([sum(1 for d in r['C']['deaths'] if d[0] <= lim and d[1]) for r in v]); dUB = m([sum(1 for d in r['B']['deaths'] if d[0] <= lim and d[1]) for r in v])
        dO = m([sum(1 for d in r['C']['deaths'] if d[0] <= lim and not d[1]) for r in v]); dOB = m([sum(1 for d in r['B']['deaths'] if d[0] <= lim and not d[1]) for r in v])
        print(f'  deaths<=r{lim} ours C/B {dU:.2f}/{dUB:.2f} theirs {dO:.2f}/{dOB:.2f}')
    for nm, lo, hi in (('our', 0.15, 9), ('mid', -0.15, 0.15), ('their', -9, -0.15)):
        print(f'  caps<=r150 on {nm} half: ours C/B {m([caps(r["C"],150,True,lo,hi) for r in v]):.2f}/{m([caps(r["B"],150,True,lo,hi) for r in v]):.2f}'
              f'  theirs {m([caps(r["C"],150,False,lo,hi) for r in v]):.2f}/{m([caps(r["B"],150,False,lo,hi) for r in v]):.2f}')
    print(f'  farm-target churn r<={H} C/B {m([churn(r["C"]["D"],0,0) for r in v]):.1f}/{m([churn(r["B"]["D"],0,0) for r in v]):.1f}')

# Plan following: per cand game, fraction of own champion turns (r<=H, decision any) whose farm_group is the body's
# plan group at some step; and whether the base's own first groups already match the plan.
def first_groups(D, lim=H):
    out = {}
    for h, d in D.items():
        seq = []
        for r in sorted(d):
            if r > lim: break
            g = d[r][1]
            if g >= 0 and (not seq or seq[-1] != g): seq.append(g)
        out[h] = seq
    return out


agree = []; planned_any = []
for r in rows:
    plan = r['C']['plan']
    if not plan: continue
    fb = first_groups(r['B']['D']); fc = first_groups(r['C']['D'])
    hs = sorted(fb)
    for b, h in enumerate(hs):
        if b >= len(plan) or not plan[b]: continue
        p0 = plan[b][0]
        agree.append((fb[h][:1] == [p0], fc.get(h, [])[:1] == [p0]))
print('first planned group = first farm group: base', m([a for a, _ in agree]), 'cand', m([c for _, c in agree]), 'n', len(agree))
print('games with plan:', sum(1 for r in rows if r['C']['plan']), 'of', len(rows))
# divergence vs flip
for lo, hi in ((0, 30), (30, 60), (60, 100), (100, 200), (200, 1000)):
    v = [r for r in rows if r['div'] and lo <= r['div'] < hi]
    if v: print(f'div r{lo}-{hi}: n {len(v)}  cand {m([r["C"]["win"] for r in v]):.3f} base {m([r["B"]["win"] for r in v]):.3f}')
