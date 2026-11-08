import json,numpy as np,collections
from sklearn.tree import DecisionTreeClassifier,export_text
R=json.load(open('draftmap.json'))
F=['n','w','h','gem','gold','wolf','elk','golem','mono','altars','groups','bush','gem_minus_gold','gem_frac','area']
X=np.array([[r['n'],r['w'],r['h'],r['gem'],r['gold'],r['wolf'],r['elk'],r['golem'],r['mono'],r['altars'],r['groups'],r['bush'],r['gem']-r['gold'],r['gem']/max(1,r['gem']+r['gold']),r['w']*r['h']] for r in R],float)
for lab,y in (('first pick',[r['picks'][0] for r in R]),('second pick',[r['picks'][1] for r in R]),('has Tavi',['Tavi' in r['picks'] for r in R])):
    y=np.array(y)
    for dep in (1,2,3):
        m=DecisionTreeClassifier(max_depth=dep,min_samples_leaf=2).fit(X,y); print(lab,dep,round(m.score(X,y),3))
    m=DecisionTreeClassifier(max_depth=2,min_samples_leaf=2).fit(X,y); print(export_text(m,feature_names=F,decimals=2))
# simple rule check
c=collections.Counter()
for r in R:
    rule='Marcella' if r['gem']-r['gold']>=5 and r['n']>=4 else ('Vendetta' if r['n']==3 and r['gem']-r['gold']<=0 and r['wolf']>=5 else 'Vesper Vale')
    c[(rule==r['picks'][0])]+=1
print('hand rule first pick',c)
