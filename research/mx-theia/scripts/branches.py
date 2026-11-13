# Alive champion turns by D branch and champion: share of turns, and share of those turns spent moving
# (position changed), r<=LIMIT. W vs L.
import json,gzip,collections,sys,os,re,zipfile
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; LIMIT=int(sys.argv[2]) if len(sys.argv)>2 else 600
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$',re.M)
def one(item):
    dname,row=item; d=os.path.join(ROOT,dname)
    try:
        meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
        z=zipfile.ZipFile(os.path.join('/home/ubuntu/wt/mx-theia',row['source'])); D={}
        for fn in ('team-a.stdout','team-b.stdout'):
            for m in D_RE.finditer(z.read(fn)): D[(int(m.group(1)),int(m.group(2)))]=m.group(3).decode()
    except Exception: return None
    w=meta['result']['winner']; names={c['id']:c['name'] for c in meta['champions']}
    out=collections.Counter()
    for c in R['champions']:
        lab='W' if c['team']==w else 'L'; nm='Prism' if names[c['id']]=='Prism' else 'other'
        for t in range(1,len(R['round'])):
            r=R['round'][t]
            if r>LIMIT: break
            if not c['alive'][t] or not c['alive'][t-1]: continue
            b=D.get((r,c['id']),'?'); mv=(c['x'][t],c['y'][t])!=(c['x'][t-1],c['y'][t-1])
            out[(lab,nm,b,'n')]+=1; out[(lab,nm,b,'mv')]+=mv
    return out
if __name__=='__main__':
    idx=json.load(open(ROOT+'/index.json')); rows={}
    for g in idx['games']: rows.setdefault(g['dir'],g)
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,list(rows.items()),chunksize=4) if r]
    T=collections.Counter()
    for r in res: T.update(r)
    for lab in 'WL':
        for nm in ('Prism','other'):
            tot=sum(v for k,v in T.items() if k[0]==lab and k[1]==nm and k[3]=='n'); mvt=sum(v for k,v in T.items() if k[0]==lab and k[1]==nm and k[3]=='mv')
            bs=sorted({k[2] for k in T if k[0]==lab and k[1]==nm},key=lambda b:-T[(lab,nm,b,'n')])
            print(lab,nm,'turns',tot,'moving %.2f'%(mvt/tot),' '.join('%s:%.3f(mv%.2f)'%(b,T[(lab,nm,b,'n')]/tot,T[(lab,nm,b,'mv')]/max(1,T[(lab,nm,b,'n')])) for b in bs[:12]))
