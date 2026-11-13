import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    P=[c for c in o['champions'] if names[c['id']]=='Prism']
    if len(P)!=2: return None
    a,b=P; T=len(a['x']); w=m['result']['winner']
    for r in range(T):
        if a['alive'][r] and b['alive'][r] and max(a['foc'][r]/b['foc'][r], b['foc'][r]/a['foc'][r])>=2:
            s,v=(a,b) if a['foc'][r]>b['foc'][r] else (b,a)
            if s['team']==w: return ('won',)
            if any(not s['alive'][q] for q in range(r,T)) or any(not v['alive'][q] for q in range(r,T)): return ('lost_death',)
            st=s['team']; sc=o['gems']
            bags=sum(c['gems'][-1] for c in o['champions'] if c['team']==st and c['alive'][-1])
            return ('lost_race', r, T, sc[st][r], s['gems'][r], sc[1-st][r], sc[st][-1], s['gems'][-1], bags, sc[1-st][-1])
    return None
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=8) if x]
    print(collections.Counter(x[0] for x in R))
    L=[x for x in R if x[0]=='lost_race']
    for i,nm in enumerate(['r','T','our_score_r','prism_bag_r','enemy_score_r','our_score_end','prism_bag_end','our_bags_end','enemy_score_end'],1):
        print(nm, statistics.median(x[i] for x in L))
    print('end: our score+bags>=1000', sum(1 for x in L if x[6]+x[8]>=1000), 'of', len(L))
