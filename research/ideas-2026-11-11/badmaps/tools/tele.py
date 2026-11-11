from lib import *
import pickle
out=[]
for d,gm in find():
    meta=json.load(open(d+'/meta.json'))
    us=0 if gm['side']=='a' else 1
    team={c['id']:c['team'] for c in meta['champions']}
    n=[0,0]; bank=[0,0]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        if '"teleport_start"' in l:
            e=json.loads(l); n[0 if team[e['a']]==us else 1]+=1
    out.append(dict(map=gm['map'],opp=gm['opp_name'][:4],side=gm['side'],win=gm['result']=='win',us=n[0],them=n[1],hash=meta['map']['hash']))
pickle.dump(out,open('tele.pkl','wb'))
