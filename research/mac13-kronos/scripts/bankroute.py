# Non-Prism bank trips: walk start (first round of the B run before the tribute) -> altar -> position at the
# champion's next capture. Chebyshev cost of the chosen altar against the best altar seen in the game.
import json,gzip,glob,collections,statistics,zipfile
from multiprocessing import Pool
def ch(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz')); C={c['id']:c for c in o['champions']}; T=len(o['round'])
    z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    br={}
    for side in (0,1):
        for line in z.read('team-%s.stdout'%'ab'[side]).decode('latin1').splitlines():
            if line.startswith('D '):
                p=line.split(); br[(int(p[1]),int(p[2]))]=p[3]
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz')]
    altars=set()
    for e in ev:
        if e['k']=='tribute_start': altars.add(tuple(e['altar']))
        if e['k']=='lock_place': altars.add(tuple(e['to']))
    if len(altars)<2: return []
    caps=collections.defaultdict(list)
    for e in ev:
        if e['k']=='capture':
            for s in e['shares']: caps[s[0]].append(e['r'])
    out=[]
    for e in ev:
        if e['k']!='tribute_start' or names[e['a']]=='Prism': continue
        a=e['a']; r=e['r']; s=r
        while br.get((s-1,a))=='B': s-=1
        if s==r or s<2: continue
        c=C[a]; i0=s-1
        if i0>=T or c['x'][i0] is None: continue
        start=(c['x'][i0],c['y'][i0])
        nxt=[x for x in caps[a] if x>r]
        if not nxt: continue
        j=min(nxt[0]-1,T-1)
        if c['x'][j] is None: continue
        nextp=(c['x'][j],c['y'][j]); alt=tuple(e['altar'])
        chosen=ch(start,alt)+ch(alt,nextp)
        best=min(ch(start,b)+ch(b,nextp) for b in altars)
        out.append((chosen,best,ch(start,alt),r-s))
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for r in p.map(one,fs,chunksize=4) if r for x in r]
    print('non-Prism bank trips on 2+ altar games',len(R))
    print('chosen cost mean',round(statistics.mean(x[0] for x in R),1),'best mean',round(statistics.mean(x[1] for x in R),1))
    print('trips where another altar saves 5+ tiles',sum(x[0]-x[1]>=5 for x in R),'10+',sum(x[0]-x[1]>=10 for x in R))
    print('saving per trip mean',round(statistics.mean(x[0]-x[1] for x in R),2),'; walk to the altar mean',round(statistics.mean(x[2] for x in R),1),'rounds of the B run mean',round(statistics.mean(x[3] for x in R),1))
