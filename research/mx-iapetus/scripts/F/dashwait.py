# Retreat turns (D trace 'R') of our dashers that end unmoved, not stunned, beside a hole or altar, dash cooling.
# Usage: dashwait.py BATCH EXTRACT CAND [N]
import json,gzip,sys,os,zipfile,collections
from multiprocessing import Pool
B,A,cand=sys.argv[1],sys.argv[2].rstrip('/')+'/',sys.argv[3]; N=int(sys.argv[4]) if len(sys.argv)>4 else 300
DASH={'Vesper Vale':1,'Vendetta':1,'Ren':1,'Issac':1,'Heart of Ruin':1}
def one(r):
    src=os.path.basename(r['source']); f=os.path.join(B,src)
    if not os.path.exists(f) or cand not in r['teams']: return None
    ct=r['teams'].index(cand); side='ab'[ct]
    out=zipfile.ZipFile(f).read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    dec={}
    for l in out:
        p=l.split()
        if len(p)==6 and p[0]=='D' and p[1].isdigit():
            try: dec[(int(p[1]),int(p[2]))]=p[3]
            except ValueError: pass
    m=json.load(open(A+r['dir']+'/meta.json')); nm={c['id']:c['name'] for c in m['champions']}
    mp=json.load(open(A+'maps/'+r['mapHash']+'.json')); cross={tuple(t) for t in mp['holes']}|{tuple(t) for t in mp['altars']}
    R=json.load(gzip.open(A+r['dir']+'/rounds.json.gz')); C=collections.Counter()
    for c in R['champions']:
        if c['team']!=ct or nm[c['id']] not in DASH: continue
        slot=1 if nm[c['id']]!='Heart of Ruin' else 1
        for i in range(1,len(R['round'])):
            rd=R['round'][i]
            if dec.get((rd,c['id']))!='R' or not c['alive'][i] or c['x'][i] is None or c['x'][i-1] is None: continue
            C['R turns']+=1
            if (c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1]) or c['turn'][i]!=1: continue
            p=(c['x'][i],c['y'][i])
            beside=any((p[0]+dx,p[1]+dy) in cross for dx in (-1,0,1) for dy in (-1,0,1))
            cd=c['cd1'][i] if nm[c['id']]!='Vendetta' else c['cd1'][i]
            if beside and cd>0:
                C['unmoved beside crossing, dash cooling']+=1
                if i+1<len(R['round']) and c['alive'][i] and not all(c['alive'][j] for j in range(i,min(i+5,len(R['round'])))): C['  ... died within 5']+=1
                if c['hp'][i]<c['hp'][i-1]: C['  ... hit that round']+=1
    return C
if __name__=='__main__':
    idx=json.load(open(A+'index.json'))['games'][:N]
    with Pool(8) as p: res=[x for x in p.map(one,idx) if x is not None]
    T=collections.Counter()
    for c in res: T.update(c)
    print('games',len(res)); [print(k,v,round(v/len(res),3)) for k,v in T.items()]
