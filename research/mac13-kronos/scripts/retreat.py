# Deaths r<=500 whose victim was retreating ('R' in its last 5 D lines): the nearest living ally (and the
# nearest ally with a ready stun) 5 rounds before and at death; did the retreat move towards or away from allies.
import json,gzip,glob,collections,statistics,zipfile
from multiprocessing import Pool
def ch(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}; tm={c['id']:c['team'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz')); C={c['id']:c for c in o['champions']}
    z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    br={}
    for side in (0,1):
        for line in z.read('team-%s.stdout'%'ab'[side]).decode('latin1').splitlines():
            if line.startswith('D '):
                p=line.split(); r=int(p[1])
                if r<=500: br[(r,int(p[2]))]=p[3]
    sp={}
    for c in o['champions']: sp.setdefault(c['team'],(c['x'][0],c['y'][0]))
    out=[]; seen=set()
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['r']>500: break
        if e['k']!='death': continue
        v=e['v']; r=e['r']; t=tm[v]
        if (r,t,names[v] in('Cassi','Issac')) in seen and names[v] in ('Cassi','Issac'): continue
        seen.add((r,t,names[v] in('Cassi','Issac')))
        last=[br.get((r-i,v)) for i in range(1,7)]
        if 'R' not in last: continue
        V=C[v]; r5=r-7; r=r-1  # array index i is round i+1: r-1 is the round before the death
        if r5<0 or V['x'][r5] is None or V['x'][r-1] is None: continue
        mates=[c for c in o['champions'] if c['team']==t and c['id']!=v and names[c['id']] not in(('Cassi','Issac') if names[v] in('Cassi','Issac') else ())]
        def near(rr):
            ds=[ch((c['x'][rr],c['y'][rr]),(V['x'][rr],V['y'][rr])) for c in mates if c['alive'][rr] and c['x'][rr] is not None]
            return min(ds) if ds else 99
        k=e.get('by'); K=C.get(k) if isinstance(k,int) else None
        homeward=None
        if True:
            homeward=ch((V['x'][r-1],V['y'][r-1]),sp[t])-ch((V['x'][r5],V['y'][r5]),sp[t])
        # branches of allies within 4 of the victim over the 5 rounds before the death
        ab=collections.Counter()
        for c in mates:
            for rr in range(r5,r):
                if c['alive'][rr] and c['x'][rr] is not None and ch((c['x'][rr],c['y'][rr]),(V['x'][rr],V['y'][rr]))<=4:
                    b=br.get((rr+1,c['id']))
                    if b: ab[b]+=1
        out.append((names[v],near(r5),near(r-1),homeward,names.get(k,'camp') if K else 'camp',ab))
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for r in p.map(one,fs,chunksize=4) if r for x in r]
    print('retreat deaths r<=500',len(R))
    print('nearest ally 5 rounds before',collections.Counter(min(x[1],13)//2*2 for x in R).most_common())
    print('nearest ally at death',collections.Counter(min(x[2],13)//2*2 for x in R).most_common())
    print('ally got nearer',sum(x[2]<x[1] for x in R),'farther',sum(x[2]>x[1] for x in R))
    print('steps towards home over 5 rounds (neg = nearer)',collections.Counter(max(-6,min(6,x[3])) for x in R).most_common())
    print('ally within 6 at r-5 but beyond at death',sum(x[1]<=6 and x[2]>6 for x in R),'ally beyond 6 throughout',sum(x[1]>6 and x[2]>6 for x in R))
    A=collections.Counter()
    for x in R: A.update(x[5])
    tot=sum(A.values()); print('branches of allies within 4 in the 5 rounds before',{k:round(v/tot,3) for k,v in A.most_common(10)})
    mixed=sum(1 for x in R if x[5] and any(k in x[5] for k in ('F','C','E','K','h','P')) and 'R' in x[5])
    print('deaths with allies near both fighting/farming and retreating',mixed,'any ally near',sum(1 for x in R if x[5]))
    print('killers',collections.Counter(x[4] for x in R).most_common(5))
