"""Summaries of bl.py output: how many of our deaths to enemy champions were predictable as a ready
lethal burst at the victim's last turn end, and the death rate by exposure."""
import pickle, sys, collections
R = pickle.load(open(sys.argv[1], 'rb'))
n = len(R)
deaths = sum(len(g['deaths']) for g in R)
nl = sum(sum(not d[6] for d in g['deaths']) for g in R)
rows = [x for g in R for x in g['rows']]
kills = [x for x in rows if x[7]]
print(f'{n} games; our deaths to enemy champions {deaths/n:.2f}/game ({nl/n:.2f} not linked); window rows with a kill {len(kills)/n:.2f}/game')
def cls(x):
    vh, B, Bv, Sp = x[2], x[4], x[5], x[6]
    if Bv >= vh: return 'lethal-seen'
    if B >= vh: return 'lethal-unseen'
    return 'not-lethal'
c = collections.Counter(cls(x) for x in kills)
print('  kills by class at the last turn end:', {k: f'{v/n:.2f}' for k, v in c.items()})
# spell-dependent: lethal only with the spell part
sp = sum(1 for x in kills if x[5] >= x[2] and x[5] - x[6] < x[2])
print(f'  lethal-seen kills that needed a spell: {sp/n:.2f}/game; cause cast {sum(1 for x in kills if cls(x)=="lethal-seen" and x[9]=="Cast ability")/n:.2f}')
# exposure: rows by class, death rate
E = collections.Counter(cls(x) for x in rows); D = collections.Counter(cls(x) for x in kills)
for k in ('lethal-seen', 'lethal-unseen', 'not-lethal'):
    print(f'  {k:14s} turn ends {E[k]/n:7.1f}/game  die before next turn {D[k]/max(1,E[k]):.3f}')
# by margin: B/hp
print('  seen burst / health  -> turn ends/game, death rate')
bins = [0, .25, .5, .75, 1, 1.25, 1.5, 2, 3, 1e9]
for lo, hi in zip(bins, bins[1:]):
    s = [x for x in rows if lo <= x[5] / max(1, x[2]) < hi]
    if s: print(f'    [{lo:.2f},{hi:.2f}) {len(s)/n:7.1f}  {sum(x[7] for x in s)/len(s):.3f}')
# by our type and killer type for lethal-seen kills
print('  lethal-seen kills by victim:', sorted(collections.Counter(x[1] for x in kills if cls(x) == 'lethal-seen').items(), key=lambda t: -t[1]))
print('  lethal-seen kills by killer:', sorted(collections.Counter(x[8] for x in kills if cls(x) == 'lethal-seen').items(), key=lambda t: -t[1]))
# exposure by victim type
print('  lethal-seen exposure/game and death rate by victim:')
for t, k in sorted(collections.Counter(x[1] for x in rows if cls(x) == 'lethal-seen').items(), key=lambda t: -t[1]):
    s = [x for x in rows if cls(x) == 'lethal-seen' and x[1] == t]
    print(f'    {t:14s} {k/n:6.1f}  {sum(x[7] for x in s)/len(s):.3f}  gems {sum(x[10] for x in s)/len(s):.0f}')
# spell-ready lethal vs lethal with spells off
s1 = [x for x in rows if x[5] >= x[2] and x[5] - x[6] < x[2]]
s2 = [x for x in rows if x[5] - x[6] >= x[2]]
print(f'  lethal only with a ready spell: {len(s1)/n:.1f}/game, die {sum(x[7] for x in s1)/max(1,len(s1)):.3f};  lethal without spells: {len(s2)/n:.1f}/game, die {sum(x[7] for x in s2)/max(1,len(s2)):.3f}')
# by the number of enemies needed (seen)
print('  lethal-seen by enemies in window:')
for m in (1, 2, 3, 4):
    s = [x for x in rows if cls(x) == 'lethal-seen' and len([z for z in x[11] if z[4]]) == m]
    if s: print(f'    {m}: {len(s)/n:6.1f}/game die {sum(x[7] for x in s)/len(s):.3f}')
