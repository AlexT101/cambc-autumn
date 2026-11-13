"""The first Prism-on-Prism kill of each game: round, killer's bag minus victim's bag the round before, allies and
enemies of the victim within 6, and whether the killer's team won."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); w=m['result']['winner']; typ={c['id']:CH[c['type']] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}; ch={c['id']:c for c in R['champions']}
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and typ[e['v']]=='Prism' and typ.get(e.get('by'))=='Prism':
            i=ri.get(e['r']-1)
            if i is None: return None
            v,k=ch[e['v']],ch[e['by']]
            gap=(k['gems'][i] or 0)-(v['gems'][i] or 0)
            x,y=v['x'][i],v['y'][i]; al=en=0
            for c in R['champions']:
                if c['id']==v['id'] or not c['alive'][i] or c['x'][i] is None or x is None: continue
                if max(abs(c['x'][i]-x),abs(c['y'][i]-y))<=6:
                    if c['team']==team[v['id']]: al+=1
                    else: en+=1
            return (e['r'],gap,al,en,w==team[k['id']],v['gems'][i] or 0)
    return None
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=[s for s in ex.map(one,ds,chunksize=8) if s]
    n=len(S); print('games with a Prism-on-Prism kill',n,'of',len(ds),'killer team won %.0f%%'%(100*sum(s[4] for s in S)/n))
    q=sorted(s[0] for s in S); print('round q',q[n//4],q[n//2],q[3*n//4])
    for lo,hi in ((-9999,0),(0,50),(50,150),(150,300),(300,9999)):
        X=[s for s in S if lo<=s[1]<hi]
        if X: print('  killer-victim bag gap [%d,%d): %d (%.0f%%) killer won %.0f%%, victim bag median %d, victim allies-enemies within 6 mean %.2f'%(lo,hi,len(X),100*len(X)/n,100*sum(s[4] for s in X)/len(X),sorted(s[5] for s in X)[len(X)//2],sum(s[2]-s[3] for s in X)/len(X)))
