# Example pointers for the report's patterns, plus per-map consistency for low-HP death rate and UoS invasion.
import json, glob
from collections import defaultdict, Counter
S='replays/v66-analysis'
feat={}; 
for p in glob.glob(S+'/opp/feat/*.json'):
    f=json.load(open(p)); feat[f['dir']]=f
ff={}
for p in glob.glob(S+'/opp/fightfeat/*.json'):
    f=json.load(open(p)); ff[f['dir']]=f
fs={}
for p in glob.glob(S+'/opp/fs/*.json'):
    f=json.load(open(p)); fs[f['dir']]=f
# 1 UoS group captures on our side r<=200 with >=2 sharers
print('UoS grouped invasion captures:')
k=0
for d,f in feat.items():
    if f['opp']!='UoS': continue
    t=1-f['us']
    for c in f['cycles']:
        if c['cap']==t and c['rel'][t]=='enemy' and c['shares']>=2 and c['cap_r']<=200 and k<4:
            print('  ',f['source'],'r',c['cap_r'],c['cls'],c['sharers']); k+=1
# 2 their fight starts with big wins; our outnumbered initiations with losses
for o in ['Fish','UoS','Mite','PBG']:
    a=[];b=[]
    for d,f in fs.items():
        if f['opp']!=o: continue
        u=f['us']
        for s in f['starts']:
            if s['init']!=u and s['before'][1-u]-s['before'][u]>=1 and s['kills'][1-u]>=2 and s['kills'][u]==0: a.append((f['source'],s['r'],s['a'],'->',s['v'],s['before']))
            if s['init']==u and s['before'][u]-s['before'][1-u]<=-1 and s['kills'][1-u]>=1 and s['kills'][u]==0: b.append((f['source'],s['r'],s['a'],'->',s['v'],s['before']))
    print(o,'their ahead-initiated multi-kill fights',len(a),a[:2]); print(o,'our outnumbered initiations lost',len(b),b[:2])
# 3 deep dashes / missed kills examples
for o in ['Fish','UoS','Mite','PBG']:
    for key in ('them|deepdash','them|missed','us|missed'):
        xs=[(f['source'],e) for d,f in ff.items() if f['opp']==o for e in f['ex'].get(key,[])][:2]
        print(o,key,xs)
# per-map: low-HP died rate us vs them
print('per-map low-HP death rate (episodes) us > them:')
for o in ['Fish','Mite','UoS','PBG']:
    pm=defaultdict(lambda:{'us':[0,0],'them':[0,0]})
    for d,f in ff.items():
        if f['opp']!=o: continue
        for ro in ('us','them'):
            for k,v in f['out'].get(ro+'|lowhp',{}).items():
                pm[f['map']][ro][1]+=v; pm[f['map']][ro][0]+=v*(k.startswith('died'))
    ok=[m for m,v in pm.items() if v['us'][1]>=3 and v['them'][1]>=3]
    print(' ',o, sum(1 for m in ok if pm[m]['us'][0]/pm[m]['us'][1]>pm[m]['them'][0]/pm[m]['them'][1]),'/',len(ok))
# per-map UoS invasion share
pm=defaultdict(lambda:[0,0,0,0])
for d,f in feat.items():
    if f['opp']!='UoS': continue
    u=f['us']; t=1-u
    for c in f['cycles']:
        if c['cap']==t: pm[f['map']][1]+=c['gems']; pm[f['map']][0]+=c['gems']*(c['rel'][t]=='enemy')
        if c['cap']==u: pm[f['map']][3]+=c['gems']; pm[f['map']][2]+=c['gems']*(c['rel'][u]=='enemy')
print('UoS invasion share > ours on', sum(1 for v in pm.values() if v[1] and v[3] and v[0]/v[1]>v[2]/v[3]),'/',len(pm),'maps; UoS invasion share >=20% on',sum(1 for v in pm.values() if v[1] and v[0]/v[1]>=0.2),'maps')
# per-map steals by them > us
for o in ['Fish','Mite','UoS','PBG']:
    pm=defaultdict(lambda:[0,0])
    for d,f in feat.items():
        if f['opp']!=o: continue
        u=f['us']
        for c in f['cycles']:
            tot=sum(c['dmg'])
            if tot>0 and c['dmg'][1-c['cap']]>0.5*tot: pm[f['map']][c['cap']==u]+=c['gems']
    print(o,'maps where their stolen gems > ours:',sum(1 for a,b in pm.values() if a>b),'/',len(pm))
