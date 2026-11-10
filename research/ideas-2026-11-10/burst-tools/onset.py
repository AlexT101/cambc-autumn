"""For kills at seen-lethal turn ends: the streak of seen-lethal turn ends before death, and what changed at its
onset against the turn end before it (P): cooldowns, our health, distances (our move or theirs)."""
import pickle, sys, collections
R = pickle.load(open(sys.argv[1], 'rb')); n = len(R)
L = lambda x: x[5] >= x[2]
C = collections.Counter(); S = collections.Counter(); BR = collections.Counter()
ex = []
for g in R:
    by = collections.defaultdict(dict)
    for x in g['rows']: by[x[12]][x[0]] = x
    for x in g['rows']:
        if not (x[7] and L(x)): continue
        v = x[12]; r = x[0]; k = 0
        while (r - 1) in by[v] and L(by[v][r - 1]): r -= 1; k += 1
        S[min(k, 6)] += 1
        O = by[v][r]; P = by[v].get(r - 1)
        if P is None: C['no-prev-row (enemy came into 6 / first sighting)'] += 1; continue
        seen = [z for z in P[11] if z[4]]
        cdP = sum(z[11] for z in seen)
        hpP, hpO = P[2], O[2]
        # killer: the enemy with the biggest burst at O
        kz = max(O[11], key=lambda z: z[2]); kid = kz[9]
        kp = [z for z in P[11] if z[9] == kid]
        if cdP >= hpP and P[5] < hpP: why = 'cooldown (lethal had spells been ready)'
        elif P[5] >= hpO: why = 'health drop (same burst, lower health)'
        elif not kp: why = 'killer not near at P'
        else:
            dP, dO = kp[0][1], kz[1]
            vm = max(abs(O[13][0] - P[13][0]), abs(O[13][1] - P[13][1]))
            if dO < dP: why = 'closer: ' + ('we moved' if vm and max(abs(O[13][0]-kz[10][0]),abs(O[13][1]-kz[10][1])) < max(abs(P[13][0]-kz[10][0]),abs(P[13][1]-kz[10][1])) else 'they moved')
            elif len([z for z in O[11] if z[4]]) > len(seen): why = 'more enemies seen'
            else: why = 'other (turn order / reach)'
        C[why] += 1
        if 'bx' in g:
            b = g['bx'].get((P[0], v))
            if b: BR[(why[:8], b[7], b[3])] += 1
tot = sum(C.values()) + 0
print(f'{n} games; kills at seen-lethal turn ends {sum(S.values())/n:.2f}/game; streak length before death (turn ends):', dict(sorted(S.items())))
for k, v in C.most_common(): print(f'   {v/n:5.2f}/game  {v/sum(C.values()):.2f}  {k}')
if BR:
    print('  branch at P (why, branch, bot lethal at P):')
    for k, v in BR.most_common(14): print(f'     {k} {v/n:.3f}')
