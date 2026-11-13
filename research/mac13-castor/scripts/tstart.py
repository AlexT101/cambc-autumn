# Every Prism tribute start with >=100 gems: enemies within 8 / within 15 at the start, the nearest enemy distance,
# its outcome (end / cancel cause) and turns spent; by bot.
import json,gzip,glob,collections,sys,os,statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx={g['dir']:g for g in json.load(open(ROOT+'/index.json'))['games']}
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    g=idx.get(os.path.basename(d))
    if not g: return None
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    rid={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    pr={c['id']:c['team'] for c in meta['champions'] if en[c['type']]=='Prism'}
    out=[]; open_={}
    for line in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(line)
        a=e.get('a')
        if a not in pr: continue
        if e['k']=='tribute_start' and e.get('gems',0)>=100:
            i=rid.get(e['r'],None)
            if i is None: continue
            t=pr[a]; p=tuple(e['at']) if e.get('at') else (C[a]['x'][i],C[a]['y'][i])
            if p[0] is None: continue
            ds=[cheb((c['x'][i],c['y'][i]),p) for c in R['champions'] if c['team']!=t and c['alive'][i] and c['x'][i] is not None]
            al=sum(1 for c in R['champions'] if c['team']==t and c['id']!=a and c['alive'][i] and c['x'][i] is not None and cheb((c['x'][i],c['y'][i]),p)<=8)
            open_[a]=(e['r'],e['gems'],e.get('dur'),min(ds) if ds else 99,al,g['teams'][t])
        elif e['k'] in ('tribute_end','tribute_cancel') and a in open_:
            s=open_.pop(a); out.append(s+(e['k']=='tribute_end' and 'end' or e.get('cause'),e['r']-s[0]))
    return out
def b(d): return '<=8' if d<=8 else '9-15' if d<=15 else '16-25' if d<=25 else '26+'
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    S=[]
    with ProcessPoolExecutor(32) as ex:
        for s in ex.map(one,ds,chunksize=4): S+= s or []
    N=collections.Counter(); O=collections.Counter(); T=collections.Counter()
    for r,gems,dur,nd,al,bot,res,turns in S:
        k=b(nd); N[k]+=1; O[(k,res)]+=1; T[(k,res)]+=turns
    for k in ('<=8','9-15','16-25','26+'):
        print(k,N[k],{res:(O[(k,res)],round(T[(k,res)]/max(1,O[(k,res)]),1)) for res in ('end','stun','lock','manual','death')})
    print('starts',len(S),'mean dur',st.mean(s[2] for s in S if s[2]))
