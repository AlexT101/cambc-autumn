import json,gzip,os,pickle
from multiprocessing import Pool
R='/home/ubuntu/cambc-autumn/replays/fish-scorecard/mite-1107/'
files=[R+p+'/actor/'+f for p in ('A','B') for f in sorted(os.listdir(R+p+'/actor/'))]
def E(lst,names): return [(e['id'],names[e['id']],e['x'],e['y'],e['hp'],e['maxHp'],e['gems'],e.get('priority'),e.get('stun',None)) for e in lst if e.get('alive') and e.get('x') is not None]
def M(m): return {k:m.get(k) for k in ('alive','x','y','hp','maxHp','gems','gold','channelType','channelTimer','priority','cd')}
def one(fn):
    d=json.load(gzip.open(fn)); names={c['id']:c['name'] for c in d['roster']}
    out=dict(g=os.path.basename(fn),side=d['side'],roster=d['roster'],map=dict(w=d['map']['width'],h=d['map']['height'],spawnA=d['map']['spawnA'],sym=d['map']['symmetry']),turns=[])
    for t in d['turns']:
        w=[a for a in t['actions'] if a['kind']=='Set priority']
        rec=dict(round=t['round'],turn=t['turn'],id=t['id'],name=names[t['id']],
            s_me=M(t['start']['me']),s_en=E(t['start']['enemies'],names),s_al=E(t['start']['allies'],names),
            e_me=M(t['end']['me']) if t.get('end') else None,e_en=E(t['end']['enemies'],names) if t.get('end') else None,
            e_al=E(t['end']['allies'],names) if t.get('end') else None,
            kinds=[a['kind'] for a in t['actions']],finish=t.get('finish'))
        if w:
            b=w[-1]['before']; rec.update(v=w[-1]['value'],w_me=M(b['me']),w_en=E(b['enemies'],names),w_al=E(b['allies'],names),nw=len(w))
        out['turns'].append(rec)
    return out
if __name__=='__main__':
    with Pool(32) as p: res=p.map(one,files,chunksize=2)
    pickle.dump(res,open('allturns.pkl','wb'),protocol=5); print(len(res),sum(len(g['turns']) for g in res))
