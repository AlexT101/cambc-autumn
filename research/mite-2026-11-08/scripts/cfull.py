import json,gzip,os,pickle
from multiprocessing import Pool
R='/home/ubuntu/cambc-autumn/replays/fish-scorecard/mite-1107/'
files=[R+p+'/actor/'+f for p in ('A','B') for f in sorted(os.listdir(R+p+'/actor/'))]
D=lambda a,b:max(abs(a['x']-b['x']),abs(a['y']-b['y']))
def alive(l): return [e for e in l if e.get('alive') and e.get('x') is not None]
def one(fn):
    d=json.load(gzip.open(fn)); names={c['id']:c['name'] for c in d['roster']}; out=[]
    for t in d['turns']:
        for a in t['actions']:
            if a['kind']!='Set priority': continue
            b=a['before']; me=b['me']
            if not me['alive'] or me.get('x') is None: continue
            se=alive(t['start']['enemies'])
            if not any(D(e,me)<=6 for e in se): continue
            nm=lambda l:[dict(e,name=names[e['id']]) for e in l]
            out.append(dict(g=os.path.basename(fn),round=t['round'],turn=t['turn'],id=t['id'],name=names[t['id']],v=a['value'],me=me,start_me=t['start']['me'],
                s_en=nm(se),w_en=nm(alive(b['enemies'])),w_al=nm(alive(b['allies'])),kinds=[x['kind'] for x in t['actions']],
                camps=[c for c in b['camps'] if D(c,me)<=6]))
    return out
if __name__=='__main__':
    with Pool(32) as p: res=p.map(one,files,chunksize=2)
    rows=[r for x in res for r in x]; pickle.dump(rows,open('cfull.pkl','wb'),protocol=5); print(len(rows))
    print({k:str(v)[:200] for k,v in rows[0]['s_en'][0].items()})
