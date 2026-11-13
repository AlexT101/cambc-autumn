# Channels of 200+ gems: who started them (winner/loser team), cause of cancel, turns left, nearest enemy at start.
import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    team={c['id']:c['team'] for c in m['champions']}; names={c['id']:c['name'] for c in m['champions']}
    w=m['result']['winner']
    o=json.load(gzip.open(d+'/rounds.json.gz')); T=len(o['round'])
    C={c['id']:c for c in o['champions']}
    starts={}; out=[]
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k']=='tribute_start':
            if e['gems']>=200:
                r=min(e['r'],T-1); P=C[e['a']]
                nd=min([max(abs(c['x'][r]-P['x'][r]),abs(c['y'][r]-P['y'][r])) for c in o['champions'] if c['team']!=team[e['a']] and c['alive'][r] and c['x'][r] is not None and P['x'][r] is not None] or [99])
                starts[e['a']]=(e,nd)
        elif e['k'] in('tribute_end','tribute_cancel'):
            s=starts.pop(e['a'],None)
            if not s: continue
            st,nd=s
            out.append((team[e['a']]==w, names[e['a']], e['k'][8:], e.get('cause','-'), st['dur'], e.get('left',0), e['r']-st['r'], nd))
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for r in p.map(one,fs,chunksize=4) if r for x in r]
    print('200+ channels',len(R),'by winner',sum(x[0] for x in R))
    print('outcome x cause',collections.Counter((x[2],x[3]) for x in R).most_common())
    for wn in (True,False):
        S=[x for x in R if x[0]==wn]
        print('winner' if wn else 'loser', len(S), collections.Counter((x[2],x[3]) for x in S).most_common())
        c=[x for x in S if x[2]=='cancel']
        if c: print('  cancelled: median progress (turns run)',statistics.median(x[6] for x in c),'of dur',statistics.median(x[4] for x in c))
    print('by champion',collections.Counter((x[1],x[2]) for x in R).most_common(12))
    for b in ((0,4),(5,8),(9,12),(13,99)):
        S=[x for x in R if b[0]<=x[7]<=b[1]]
        if S: print('nearest enemy',b,len(S),'complete',round(sum(x[2]=='end' for x in S)/len(S),3), collections.Counter(x[3] for x in S if x[2]=='cancel').most_common())
