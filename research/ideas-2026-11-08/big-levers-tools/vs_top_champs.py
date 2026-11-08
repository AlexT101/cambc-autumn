# Archive (11-05/06): games against Fish or Mite. P(opponent of Fish/Mite wins) ~ rating diff + map FE + champion
# presence in the opponent's comp (and in Fish/Mite's). Coefficients in logit per champion.
import pickle,collections,numpy as np,json
from sklearn.linear_model import LogisticRegression
d=pickle.load(open('/home/ubuntu/tmp-offload/counter/games.pkl','rb')); rows=d['rows']; names=d['names']
champs=json.load(open('/home/ubuntu/tmp-offload/counter/archive/2026-11-06/meta.json'))['picks']
TOP={'1890540d-1ffc-4847-adbf-d0d08772f268':'Fish','ee83f5e5-bcad-4923-86b4-b79ea6083d2e':'Mite'}
US='547efb5b-57e5-4355-8501-3b331f506d62'
maps=sorted(set(r['map'] for r in rows)); mi={m:i for i,m in enumerate(maps)}
for tgt in ('Fish','Mite','both'):
    X=[];y=[];ours=[]
    for r in rows:
        if r['day'] not in ('2026-11-05','2026-11-06'): continue
        for top_side,other_side in (('A','B'),('B','A')):
            t=r[top_side]
            if t not in TOP or (tgt!='both' and TOP[t]!=tgt) or r[other_side] in TOP or r[other_side]==US: continue
            po=r['pb'] if other_side=='B' else r['pa']; pt=r['pa'] if top_side=='A' else r['pb']
            ro=r['rb'] if other_side=='B' else r['ra']; rt=r['ra'] if top_side=='A' else r['rb']
            other_won=(r['winner']==0)==(other_side=='A')   # winner 0 = side A (archive)
            f=np.zeros(len(champs)*2+1+len(maps)); 
            for p in set(po): f[p]=1
            for p in set(pt): f[len(champs)+p]=1
            f[2*len(champs)]=(ro-rt)/400; f[2*len(champs)+1+mi[r['map']]]=1
            X.append(f); y.append(other_won); ours.append(r[other_side]==US)
    X=np.array(X);y=np.array(y)
    m=LogisticRegression(C=1.0,max_iter=2000).fit(X,y)
    print(f'== vs {tgt}: n={len(y)}, opp win {y.mean():.3f}, rating coef {m.coef_[0][2*len(champs)]:.2f}')
    print('  opponent-of-top has champ:',' '.join(f'{champs[i][:6]}:{m.coef_[0][i]:+.2f}' for i in np.argsort(-m.coef_[0][:len(champs)])))
    cnt=X[:,:len(champs)].mean(0); print('  pick rate:',' '.join(f'{champs[i][:6]}:{cnt[i]:.2f}' for i in range(len(champs))))
