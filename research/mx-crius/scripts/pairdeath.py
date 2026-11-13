import json,gzip,glob,os,collections,statistics as st,sys
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]; CH=json.load(open(R+'/enums.json'))['champions']
def one(p):
    d=os.path.dirname(p); m=json.load(open(p)); typ={c['id']:CH[c['type']] for c in m['champions']}
    RR=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(RR['round'])}; ci={c['id']:c for c in RR['champions']}
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('linked') or typ[e['v']] not in ('Cassi','Issac'): continue
        v=e['v']; partner=[c for c in m['champions'] if c['team']==ci[v]['team'] and typ[c['id']] in ('Cassi','Issac') and c['id']!=v]
        i=ri.get(e['r']-1)
        if not partner or i is None: continue
        P=ci[partner[0]['id']]; V=ci[v]
        if V['x'][i] is None or P['x'][i] is None: continue
        dd=max(abs(V['x'][i]-P['x'][i]),abs(V['y'][i]-P['y'][i]))
        out.append((typ[v],dd,'camp' if e.get('by') is None else typ.get(e['by']),e.get('gems',0)+(P['gems'][i] or 0),V['hp'][i]/V['maxHp'][i]))
    return out
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json')
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ps,chunksize=8) for x in o]
    N=len(ps); print('pair deaths/game (both teams) %.2f'%(len(S)/N))
    print('first body to die',collections.Counter(s[0] for s in S))
    D=sorted(s[1] for s in S); n=len(D); print('body distance quartiles',D[n//4],D[n//2],D[3*n//4],' >=6: %.2f'%(sum(1 for x in D if x>=6)/n))
    print('killers',collections.Counter(s[2] for s in S).most_common(6))
    print('bags lost mean %.1f'%st.mean(s[3] for s in S))
