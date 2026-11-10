import pickle, sys, collections
R = pickle.load(open(sys.argv[1], 'rb')); n = len(R)
match = miss = 0; T = []
for g in R:
    for x in g['rows']:
        r, v, pos = x[0], x[12], x[13]
        b = g['bx'].get((r, v))
        if b is None: miss += 1; continue
        if (b[0], b[1]) != tuple(pos): miss += 1; continue
        match += 1; T.append((x, b))
print(f'{n} games; rows matched {match}, unmatched {miss}')
deaths = sum(len(g['deaths']) for g in R)
print(f'deaths to champions {deaths/n:.2f}/game; kill rows {sum(x[7] for g in R for x in g["rows"])/n:.2f}/game')
def truth(x): return 'L' if x[5] >= x[2] else ('l' if x[4] >= x[2] else '-')
c = collections.Counter((truth(x), b[3]) for x, b in T)
d = collections.Counter((truth(x), b[3]) for x, b in T if x[7])
print('truth(L seen-lethal, l unseen, -) x bot lethal: turn ends/game, death rate')
for k in sorted(c): print(f'   {k}: {c[k]/n:7.2f}  die {d[k]/c[k]:.3f}')
# Among truth-seen-lethal turn ends: branch, chose, walked, cast, safe tiles
L = [(x, b) for x, b in T if truth(x) == 'L']
print('seen-lethal turn ends by branch (n/game, die rate, bot-lethal share, a safe tile near the start):')
for br, k in collections.Counter(b[7] for x, b in L).most_common():
    s = [(x, b) for x, b in L if b[7] == br]
    print(f'   {br}: {k/n:5.2f}  die {sum(x[7] for x,_ in s)/k:.3f}  bot-lethal {sum(b[3] for _,b in s)/k:.2f}  safe-near {sum(b[14]>0 for _,b in s)/k:.2f}  chose {sum(b[8] for _,b in s)/k:.2f} cast {sum((b[10]+b[11])>0 for _,b in s)/k:.2f} stunned {sum(b[12] for _,b in s)/k:.2f}')
print('bot-lethal turn ends: by branch')
BL = [(x, b) for x, b in T if b[3]]
for br, k in collections.Counter(b[7] for x, b in BL).most_common():
    s = [(x, b) for x, b in BL if b[7] == br]
    print(f'   {br}: {k/n:5.2f}  die {sum(x[7] for x,_ in s)/k:.3f}  safe-near {sum(b[14]>0 for _,b in s)/k:.2f} truthL {sum(truth(x)=="L" for x,_ in s)/k:.2f}')
# bot's vis estimate vs truth seen burst
import statistics as st
rat = [b[4] / max(1, x[5]) for x, b in L]
rat.sort(); print('bot visible burst / truth seen burst at seen-lethal turn ends: p10/25/50/75/90', [round(rat[int(len(rat)*q)],2) for q in (.1,.25,.5,.75,.9)])
# kills: bot lethal at the turn end?
K = [(x, b) for x, b in T if x[7]]
print(f'kill rows matched {len(K)/n:.2f}/game: bot lethal {sum(b[3] for _,b in K)/max(1,len(K)):.2f}, truth L {sum(truth(x)=="L" for x,_ in K)/max(1,len(K)):.2f}')
print('  kills by victim type, bot-lethal share:', [(t, k, round(sum(b[3] for x,b in K if x[1]==t)/k,2)) for t,k in collections.Counter(x[1] for x,_ in K).most_common()])
