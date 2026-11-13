# Deaths r<=500 to the enemy Prism: in the 3 rounds before, an ally of the victim with a ready stun within 4 of the
# killer? Was the killer stunned in the 5 rounds before? (array index = round - 1)
import json,gzip,glob,collections
from multiprocessing import Pool
STUN={'Ryth':'cd0','Prism':'cd0','Marcella':'cd0','Tavi':'cd1','Ren':'cd0','Heart of Ruin':'cd1','Cassi':'cd1'}
def ch(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}; tm={c['id']:c['team'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz')); C={c['id']:c for c in o['champions']}
    out=[]; seen=set()
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['r']>500: break
        if e['k']!='death': continue
        k=e.get('by'); v=e['v']; t=tm[v]
        if not isinstance(k,int) or k not in C or names[k]!='Prism' or tm[k]==t: continue
        if (e['r'],t) in seen: continue
        seen.add((e['r'],t))
        K=C[k]; r=e['r']; ready=False; near_any=False; stunned=False
        for i in range(max(0,r-4),r-1):
            if K['x'][i] is None: continue
            if K['stun'][i]: stunned=True
            for c in o['champions']:
                if c['team']!=t or c['id']==v or not c['alive'][i] or c['x'][i] is None: continue
                if names[v] in('Cassi','Issac') and names[c['id']] in('Cassi','Issac'): continue
                if ch((c['x'][i],c['y'][i]),(K['x'][i],K['y'][i]))<=4:
                    near_any=True
                    s=STUN.get(names[c['id']])
                    if s and c[s][i]==0: ready=True
        for i in range(max(0,r-7),r-4):
            if K['stun'][i]: stunned=True
        out.append((ready,near_any,stunned,names[v]))
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for r in p.map(one,fs,chunksize=4) if r for x in r]
    print('Prism kills r<=500',len(R))
    print('an ally (not the victim) within 4 of the killer in the 3 rounds before',sum(x[1] for x in R))
    print('... one with a ready stun',sum(x[0] for x in R))
    print('killer stunned in the 6 rounds before',sum(x[2] for x in R),'; ready stun near but no stun on it',sum(x[0] and not x[2] for x in R))
