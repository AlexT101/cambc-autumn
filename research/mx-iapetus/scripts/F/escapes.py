# Kills we fail to make: an enemy body falls below 25% health with one of ours within 4, and lives 15 more rounds.
# Our nearest body's branch (D trace) on that round. Usage: escapes.py BATCH EXTRACT CAND [N]
import json,gzip,sys,os,zipfile,collections
from multiprocessing import Pool
B,A,cand=sys.argv[1],sys.argv[2].rstrip('/')+'/',sys.argv[3]; N=int(sys.argv[4]) if len(sys.argv)>4 else 400
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(r):
    src=os.path.basename(r['source']); f=os.path.join(B,src)
    if not os.path.exists(f) or cand not in r['teams']: return None
    ct=r['teams'].index(cand); side='ab'[ct]
    try: out=zipfile.ZipFile(f).read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    except KeyError: return None
    dec={}
    for l in out:
        p=l.split()
        if len(p)==6 and p[0]=='D' and p[1].isdigit():
            try: dec[(int(p[1]),int(p[2]))]=p[3]
            except ValueError: pass
    R=json.load(gzip.open(A+r['dir']+'/rounds.json.gz')); ch=R['champions']; n=len(R['round'])
    C=collections.Counter()
    ours=[c for c in ch if c['team']==ct]; theirs=[c for c in ch if c['team']!=ct]
    for e in theirs:
        low=False
        for i in range(1,n-15):
            if not e['alive'][i] or e['x'][i] is None: low=False; continue
            l=e['hp'][i]<0.25*e['maxHp'][i]
            if l and not low:
                pe=(e['x'][i],e['y'][i])
                near=[(cheb(pe,(o['x'][i],o['y'][i])),o) for o in ours if o['alive'][i] and o['x'][i] is not None]
                near=[x for x in near if x[0]<=4]
                if near:
                    died=any(not e['alive'][j] for j in range(i,i+15))
                    dmin,o=min(near,key=lambda x:x[0])
                    br=dec.get((R['round'][i],o['id']),'?')
                    C[('killed' if died else 'escaped',br)]+=1
                    if br in 'RFC':
                        hits=e['hp'][i]/max(1,o['str'][i])
                        oth=sum(1 for x in theirs if x is not e and x['alive'][i] and x['x'][i] is not None and cheb((x['x'][i],x['y'][i]),(o['x'][i],o['y'][i]))<=5)
                        tag=('killed' if died else 'escaped')
                        C[(br+' '+tag,'hits%s'%('<=1' if hits<=1 else '<=2' if hits<=2 else '<=4' if hits<=4 else '>4'))]+=1
                        C[(br+' '+tag,'ourhp%s'%('<.3' if o['hp'][i]<.3*o['maxHp'][i] else '<.6' if o['hp'][i]<.6*o['maxHp'][i] else '>=.6'))]+=1
                        C[(br+' '+tag,'others5 %d'%min(oth,3))]+=1
                        C[(br+' '+tag,'d%d'%dmin)]+=1
            low=l
    return C
if __name__=='__main__':
  idx=json.load(open(A+'index.json'))['games'][:N]
  with Pool(8) as p: res=[x for x in p.map(one,idx) if x is not None]
  T=collections.Counter()
  for c in res: T.update(c)
  g=len(res); print('games',g)
  for b in sorted({k[1] for k in T}, key=lambda b:-(T[('killed',b)]+T[('escaped',b)])):
    k,e=T[('killed',b)],T[('escaped',b)]
    if k+e>=10 and not b.startswith('hits') and not b.startswith('our') and not b.startswith('oth') and not (b[0]=='d' and b[1:].isdigit()): print(f'  nearest-ours branch {b}: killed {k/g:.2f}/g escaped {e/g:.2f}/g  ({100*k/(k+e):.0f}% converted)')

  for k in sorted(T):
    if k[0][:2] in ('R ','F ','C '): print(k,round(T[k]/g,3))
