from lib import *
import pickle
def cls_of(g):
    tys=set(x.split()[0] for x in g['types'])
    return 'Mono' if 'Monolith' in tys else 'Golem' if 'Golem' in tys else 'Elk' if 'Elk' in tys else 'Wolf' if 'Wolf' in tys else 'Clus'
out=[]
for d,gm in find():
    A,meta,R,ev,mp,us,team,typ=acct(d,gm)
    G={g['id']:g for g in mp['groups']}
    cls=collections.defaultdict(lambda:[0,0,0,0])
    first={}
    for e in ev:
        if e['k']=='capture':
            g=G[e['g']]; t=0 if e['team']==us else 1
            side='mid' if g['side']==-1 else ('own' if g['side']==us else 'enemy')
            k=(side,cls_of(g)); cls[k][t]+=1; cls[k][2+t]+=sum(s[1] for s in e['shares'])
            kk=(cls_of(g),t)
            if kk not in first: first[kk]=e['r']
    supply=collections.Counter()
    for g in mp['groups']:
        supply[cls_of(g)]+=g['gems']/g['respawn']
    hp=collections.defaultdict(float)
    out.append(dict(match=gm['match'],map=gm['map'],opp=gm['opp_name'][:4],side=gm['side'],win=gm['result']=='win',rounds=gm['rounds'],cls={k:v for k,v in cls.items()},first=first,supply=dict(supply),our_picks=gm['our_picks'],opp_picks=gm['opp_picks']))
pickle.dump(out,open('v115-class.pkl','wb'))
