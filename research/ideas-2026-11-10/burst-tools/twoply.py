"""Double-turn traps: kills at a seen-lethal turn end O whose killer had no turn after the turn end before (P).
Truth, walls and occupancy ignored: at O, was any tile within 1 of O's start (P's end tile) clear of the seen
enemies' burst (trapped at O)? At P, was there a tile within 1 of P's start from which some step at O is clear
(escapable at P, the enemies held where they stood at O)?"""
import pickle, sys, collections, os
sys.path.insert(0, os.path.dirname(__file__)); import bl
R = pickle.load(open(sys.argv[1], 'rb')); n = len(R)
L = lambda x: x[5] >= x[2]
def burst(q, near):
    t = 0.0
    for z in near:
        if not z[4]: continue
        d = max(abs(q[0] - z[10][0]), abs(q[1] - z[10][1]))
        t += bl.window_burst(z[0], z[13], z[14], d, (z[6], z[7]), z[5], z[15])[0]
    return t
nb = lambda p: [(p[0] + dx, p[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
C = collections.Counter(); BR = collections.Counter()
for g in R:
    by = collections.defaultdict(dict)
    for x in g['rows']: by[x[12]][x[0]] = x
    for x in g['rows']:
        if not (x[7] and L(x)): continue
        v, r = x[12], x[0]; P = by[v].get(r - 1); Q = by[v].get(r - 2)
        if not P or L(P): continue
        kz = max(x[11], key=lambda z: z[2]); kp = [z for z in P[11] if z[9] == kz[9]]
        if not kp or kp[0][5] != 0: continue
        hp = x[2]
        trappedO = all(burst(q, x[11]) >= hp for q in nb(P[13]))
        if Q is None: C[('trapped at O' if trappedO else 'a clear step at O', 'P start unknown')] += 1; continue
        escP = any(any(burst(q, x[11]) < hp for q in nb(p)) for p in nb(Q[13]))
        key = ('trapped at O' if trappedO else 'a clear step at O', 'escapable at P' if escP else 'trapped at P too')
        C[key] += 1
        if 'bx' in g:
            b = g['bx'].get((P[0], v)); bo = g['bx'].get((r, v))
            if b and bo: BR[key + (b[7], bo[7], bo[10] + bo[11] > 0, bo[12])] += 1
print(f'{n} games; double-turn-trap kills {sum(C.values())/n:.2f}/game')
for k, v in C.most_common(): print(f'   {v/n:5.2f}/game {v/sum(C.values()):.2f}  {k}')
if BR:
    print('  (class, branch P, branch O, cast at O, stunned at O):')
    for k, v in BR.most_common(12): print(f'     {v/n:.3f} {k}')
