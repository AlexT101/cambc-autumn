import sys; sys.path.insert(0,sys.argv[1])
from common import *
rows=[]
for r in games(distinct=False):
    m=meta(r['dir']); us=r['us']
    ch=m['champions']
    def side(t):
        cs=[c for c in ch if c['team']==t]
        return dict(names=[c['name'] for c in cs], coll=sum(c['stats']['collectedGems'] for c in cs), sub=sum(c['stats']['submittedGems'] for c in cs),
            kills=sum(c['stats']['kills'] for c in cs), deaths=sum(c['stats']['deaths'] for c in cs), gold=sum(c['stats']['earnedGold'] for c in cs),
            mdmg=sum(c['stats']['monsterDamageDone'] for c in cs), cdmg=sum(c['stats']['championDamageDone'] for c in cs), carried=sum(c['gems'] for c in cs))
    a,b=side(us),side(1-us)
    rows.append(dict(r=r,us=a,th=b))
import collections
by=collections.defaultdict(list)
for x in rows: by[x['r']['opp']].append(x)
print('opp  n  W  | coll us/them  sub us/them  kills us/them  gold us/them  rounds')
for o,xs in by.items():
    n=len(xs); w=sum(x['r']['won'] for x in xs)
    f=lambda k,s: sum(x[s][k] for x in xs)/n
    print(f"{o:5}{n:4}{w:4} | {f('coll','us'):6.0f}/{f('coll','th'):6.0f} {f('sub','us'):6.0f}/{f('sub','th'):6.0f} {f('kills','us'):5.1f}/{f('kills','th'):5.1f} {f('gold','us'):6.0f}/{f('gold','th'):6.0f} {sum(x['r']['rounds'] for x in xs)/n:6.0f}")
# drafts
print()
for o,xs in by.items():
    c=collections.Counter(tuple(x['th']['names']) for x in xs); cu=collections.Counter(tuple(x['us']['names']) for x in xs)
    print(o,'THEM',c.most_common(6)); print(o,'US',cu.most_common(6))
# loss stats: collected gems ratio in losses
print()
for o,xs in by.items():
    L=[x for x in xs if not x['r']['won']]; W=[x for x in xs if x['r']['won']]
    for nm,S_ in (('L',L),('W',W)):
        if not S_: continue
        import statistics as st
        print(o,nm,len(S_),'coll ratio med %.2f'%st.median(x['us']['coll']/max(1,x['th']['coll']) for x in S_),'kills %.1f/%.1f'%(st.mean(x['us']['kills'] for x in S_),st.mean(x['th']['kills'] for x in S_)), 'mdmg %.0f/%.0f'%(st.mean(x['us']['mdmg'] for x in S_),st.mean(x['th']['mdmg'] for x in S_)))
