from lib import *
import pickle
out=[]
for d,gm in find():
    A,meta,R,ev,mp,us,team,typ=acct(d,gm)
    row=dict(match=gm['match'],map=gm['map'],opp=gm['opp_name'][:4],side=gm['side'],win=gm['result']=='win',rounds=gm['rounds'],us=dict(A[0]),them=dict(A[1]),our_picks=gm['our_picks'],opp_picks=gm['opp_picks'],dir=d)
    # died gems by champion type, per team
    dg=[collections.Counter(),collections.Counter()]; dn=[collections.Counter(),collections.Counter()]
    big=[[],[]]
    for e in ev:
        if e['k']=='death':
            t=0 if team[e['v']]==us else 1
            dg[t][typ[e['v']]]+=e.get('gems',0); dn[t][typ[e['v']]]+=1
            if e.get('gems',0)>=40: big[t].append((e['r'],typ[e['v']],e['gems']))
    row['died_by_type']=[dict(dg[0]),dict(dg[1])]; row['deaths_by_type']=[dict(dn[0]),dict(dn[1])]; row['big']=big
    ts=[[],[]]
    for e in ev:
        if e['k']=='tribute_start':
            ts[0 if team[e['a']]==us else 1].append((e['r'],typ[e['a']],e['gems']))
    row['tstarts']=ts
    rr=R['round']; g=R['gems']
    row['g600']=[g[us][min(599,len(rr)-1)],g[1-us][min(599,len(rr)-1)]]
    row['size']=(mp['width'],mp['height']); row['naltars']=len(mp['altars'])
    out.append(row)
pickle.dump(out,open('v115-acct.pkl','wb'))
print(len(out))
