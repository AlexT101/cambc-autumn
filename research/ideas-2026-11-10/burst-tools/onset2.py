"""Kills at seen-lethal turn ends O whose killer had no turn in the window after the turn end before (P): the
double-turn trap. At P: could one step from P's tile have left the killer's lethal reach at O (truth, walls ignored)?
Local batches with BX: the bot's branch and beliefs at P."""
import pickle, sys, collections, os
sys.path.insert(0, os.path.dirname(__file__)); import bl
R = pickle.load(open(sys.argv[1], 'rb')); n = len(R)
L = lambda x: x[5] >= x[2]
C = collections.Counter(); BR = collections.Counter(); ESC = collections.Counter(); TYPES = collections.Counter()
exposure = collections.Counter()
for g in R:
    by = collections.defaultdict(dict)
    for x in g['rows']: by[x[12]][x[0]] = x
    # exposure: turn ends P whose killer-like enemies have 0 turns now and 2 next, and a step can't escape
    for x in g['rows']:
        if not (x[7] and L(x)): continue
        v = x[12]; r = x[0]; P = by[v].get(r - 1)
        if not P: C['no P'] += 1; continue
        kz = max(x[11], key=lambda z: z[2]); kid = kz[9]
        kp = [z for z in P[11] if z[9] == kid]
        if not kp: C['killer far at P'] += 1; continue
        kp = kp[0]
        if L(P): C['P lethal too'] += 1; continue
        cls = f'turnsP {kp[5]} -> turnsO {kz[5]}'
        C[cls] += 1
        if kp[5] == 0:
            TYPES[kz[0]] += 1
            if 'bx' in g:
                b = g['bx'].get((P[0], v)); bo = g['bx'].get((x[0], v))
                if b and bo: BR[(b[7], bo[7])] += 1
for k, v in C.most_common(): print(f'  {v/n:5.2f}/game  {k}')
print('  killers in the 0-turn onset:', TYPES.most_common(8))
if BR:
    print('  branch at P -> at O (0-turn onsets):')
    for k, v in BR.most_common(12): print(f'     {k} {v/n:.3f}/game')
