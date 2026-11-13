"""Our Prism starting a turn alive with its stun ready and the visible enemy Prism within 4: what it did (stun the
Prism / other slot-0 target / ground cast / nothing) and what happened within 6 rounds (who died), by Focus ratio."""
import gzip,json,sys,collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    names={int(c['id']):c['name'] for c in meta['champions']}
    casts=collections.defaultdict(list)
    deaths={}
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='cast': casts[(e['r'],e['a'])].append((e['slot'],tuple(e.get('to') or [])))
        if e['k']=='death': deaths.setdefault(e['v'],[]).append(e['r'])
    ch={int(c['id']):c for c in R['champions']}
    P=[k for k,v in names.items() if v=='Prism']
    out=[]
    if len(P)!=2: return out
    for a in P:
        b=[x for x in P if x!=a][0]; c=ch[a]; p=ch[b]
        last=-99
        for i in range(1,len(c['alive'])):
            if i-last<8: continue
            if not c['alive'][i] or not p['alive'][i-1] or c['cd0'][i-1]!=0 or c['x'][i-1] is None or p['x'][i-1] is None: continue
            if b not in [x if not isinstance(x,list) else x[0] for x in c['sees'][i-1]]: continue
            dd=max(abs(c['x'][i-1]-p['x'][i-1]),abs(c['y'][i-1]-p['y'][i-1]))
            if dd>4: continue
            last=i
            r=i+1; cs=casts.get((r,a),[])
            px,py=p['x'][i-1],p['y'][i-1]
            if any(sl==0 and to and max(abs(to[0]-px),abs(to[1]-py))<=1 for sl,to in cs): act='stunP'
            elif any(sl==0 for sl,to in cs): act='stunOther'
            elif any(sl==1 for sl,to in cs): act='ground'
            else: act='none'
            ratio=c['foc'][i-1]/max(1,p['foc'][i-1])
            we=any(r<=x<=r+6 for x in deaths.get(a,[])); they=any(r<=x<=r+6 for x in deaths.get(b,[]))
            out.append((act,'ours>' if ratio>1.1 else 'ours<' if ratio<0.9 else 'par',we,they,dd))
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res=[x for r in ex.map(g,dirs,chunksize=8) for x in r]
    T=collections.defaultdict(lambda:[0,0,0])
    for act,rat,we,they,dd in res:
        T[(rat,act)][0]+=1; T[(rat,act)][1]+=we; T[(rat,act)][2]+=they
    for k in sorted(T): v=T[k]; print(k,'n',v[0],'we die 6r',round(v[1]/v[0],2),'they die 6r',round(v[2]/v[0],2))
