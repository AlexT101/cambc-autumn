import sys; sys.path.insert(0,'/home/ubuntu/tmp-offload/emblem/tools'); from arch import *
import collections
S,U,m=day(sys.argv[1]); team=sys.argv[2]; ty=sys.argv[3]
s=(U['team']==team)&(U['type']==ty)
mp=S['map'][U['row'][s]]; side=U['side'][s]; f=np.array([fam(x) for x in U['e'][s][:,0]])
per=collections.defaultdict(collections.Counter)
for a,b,c in zip(mp,side,f): per[(a,b)][c]+=1
mixed=sum(1 for k,v in per.items() if len(v)>1 and v.most_common(1)[0][1]/sum(v.values())<0.9)
print('cells',len(per),'mixed(<90% modal)',mixed)
# share of games whose first emblem differs from the cell's modal
tot=sum(sum(v.values()) for v in per.values()); off=sum(sum(v.values())-v.most_common(1)[0][1] for v in per.values())
print('off-modal share',off/tot)
for k,v in list(per.items())[:8]: print(k,dict(v))
