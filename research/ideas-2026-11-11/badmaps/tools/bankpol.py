from lib import *
import pickle
# For each capture share: (team us/them, opp, type, bag after capture, cheb dist to nearest altar, banked_next: tribute_start before this champ's next capture share or death)
out=[]
for d,gm in find():
    A,meta,R,ev,mp,us,team,typ=acct(d,gm)
    alt=mp['altars']
    ch={c['id']:c for c in R['champions']}
    pend={}  # cid -> record
    for e in ev:
        k=e['k']
        if k=='capture':
            for cid,g,go in e['shares']:
                if g<=0: continue
                if cid in pend: pend[cid]['next']='capture'; out.append(pend.pop(cid))
                i=min(e['r']-1,len(R['round'])-1); c=ch[cid]
                if not c['alive'][i]: continue
                pos=(c['x'][i],c['y'][i]); bag=c['gems'][i]
                dmin=min(max(abs(pos[0]-a[0]),abs(pos[1]-a[1])) for a in alt)
                pend[cid]=dict(us=team[cid]==us,opp=gm['opp_name'][:4],typ=typ[cid],bag=bag,d=dmin,r=e['r'],map=gm['map'],next=None)
        elif k=='tribute_start' and e['a'] in pend:
            pend[e['a']]['next']='tribute'; pend[e['a']]['dt']=e['r']-pend[e['a']]['r']; out.append(pend.pop(e['a']))
        elif k=='death' and e['v'] in pend:
            pend[e['v']]['next']='death'; out.append(pend.pop(e['v']))
pickle.dump(out,open('bankpol.pkl','wb')); print(len(out))
