"""Contact episodes: a champion with an enemy within 6 at round r and none within 6 in r-3..r-1 (onset). Counts allies
(excluding self) and enemies within 6 at onset (bodies), and within 10; death within 10 rounds; and kills its team gets
within 10 rounds near it (enemy deaths within 8 of it)."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]
def one(p):
    d=os.path.dirname(p); m=json.load(open(p))
    RR=json.load(gzip.open(d+'/rounds.json.gz')); rounds=RR['round']; n=len(rounds); C=RR['champions']
    deaths=collections.defaultdict(list)
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and not e.get('linked'): deaths[e['v']].append(e['r'])
    mp=json.load(open(os.path.join(d,m['mapFile']))); sp=mp['spawn']
    def side(c,i):
        x,y=c['x'][i],c['y'][i]
        dd=[max(abs(x-(s['minX']+s['maxX'])/2),abs(y-(s['minY']+s['maxY'])/2)) for s in sp]
        return 'own' if dd[c['team']]<dd[1-c['team']] else 'enemy'
    out=[]
    def near(i,c,R_):
        a=en=0
        for o in C:
            if o is c or not o['alive'][i] or o['x'][i] is None: continue
            if max(abs(o['x'][i]-c['x'][i]),abs(o['y'][i]-c['y'][i]))<=R_:
                if o['team']==c['team']: a+=1
                else: en+=1
        return a,en
    for c in C:
        last=-99
        for i in range(3,n,1):
            if not c['alive'][i] or c['x'][i] is None: continue
            a,en=near(i,c,6)
            if en==0: continue
            if rounds[i]-last<=3: last=rounds[i]; continue
            last=rounds[i]
            a10,e10=near(i,c,10)
            r=rounds[i]; died=any(r<x<=r+10 for x in deaths[c['id']])
            out.append((min(a,3),min(en,3),min(a10,4),min(e10,4),died,side(c,i)))
    return out
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json')[:800]
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ps,chunksize=4) for x in o]
    print('onsets',len(S),'death within 10: %.3f'%(sum(s[4] for s in S)/len(S)))
    t=collections.defaultdict(lambda:[0,0])
    for a,e,a10,e10,dd,sd in S: t[(a,e)][0]+=1; t[(a,e)][1]+=dd
    print('by allies within 6 (rows) x enemies within 6 (cols): death rate (n)')
    for a in range(4): print('  a=%d '%a+' '.join('e=%d %.3f(%d)'%(e,t[(a,e)][1]/max(1,t[(a,e)][0]),t[(a,e)][0]) for e in range(1,4)))
    t=collections.defaultdict(lambda:[0,0])
    for a,e,a10,e10,dd,sd in S: t[(a10-e10)][0]+=1; t[(a10-e10)][1]+=dd
    print('by allies-enemies within 10:',' '.join('%+d %.3f(%d)'%(k,v[1]/v[0],v[0]) for k,v in sorted(t.items())))
    for SD in ('own','enemy'):
        t=collections.defaultdict(lambda:[0,0])
        for a,e,a10,e10,dd,sd in S:
            if sd==SD: t[(a10-e10)][0]+=1; t[(a10-e10)][1]+=dd
        print(SD,'half, by allies-enemies within 10:',' '.join('%+d %.3f(%d)'%(k,v[1]/v[0],v[0]) for k,v in sorted(t.items()) if v[0]>200))
