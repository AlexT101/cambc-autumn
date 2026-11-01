"""Q2 trace: our champions that die within 60 rounds of a respawn. Their farm_pick modes over the turns between
respawn and death (S alone, J join an ally's claim, C crew, H help, ...), compared with respawns that survive 60
rounds; the share of turns with no ally within 8 (extract) on the way; and the want_home answer on their last turn."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
Q=json.load(open(CACHE+'/../q2.json'))
RES=defaultdict(list)
for x in Q:
    for r in x['resp']:
        if r['side']=='us': RES[r['dir']].append(r)
def one(arg):
    key,g=arg; T=tload(key); out=[]
    if g['dir'] not in RES: return out
    G=Game(g)
    for x in RES[g['dir']]:
        R=x['R']; died=x['gap'] is not None and x['gap']<=60; end=R+(x['gap'] if died else 60)
        if end>T['trust']: continue
        modes=Counter(); br=Counter(); alone=0; n=0; last=None
        for r in range(R+1,end+1):
            L=T['turns'].get((r,x['c']))
            if not L or 'tt' not in L or L['tt'].get('a')!='1': continue
            n+=1; br[L['tt'].get('d')]+=1
            for e in L['te']:
                if e['k']=='farm_pick': modes[e.get('m')]+=1
                if e['k']=='home': last=(e.get('v'),e.get('why'))
            i=G.idx.get(r); p=G.pos(x['c'],i) if i else None
            if p and not G.on_spawn(G.us,p):
                if not any(G.pos(d,i) and C.cheb(G.pos(d,i),p)<=8 for d in G.units[G.us] if d!=x['c']): alone+=1
        out.append(dict(died=died,modes=dict(modes),br=dict(br),alone=alone,n=n,last=last))
    return out
if __name__=='__main__':
    res=[y for o in pmap(one,trace_keys()) for y in o]
    for d in (True,False):
        Z=[x for x in res if x['died']]; Z=[x for x in res if x['died']==d]
        m=Counter(); b=Counter()
        for x in Z: m.update(x['modes']); b.update(x['br'])
        n=sum(x['n'] for x in Z)
        print('died<=60' if d else 'survived 60',len(Z),'farm modes',{k:round(v/sum(m.values()),2) for k,v in m.most_common(6)},'branches',{k:round(v/n,2) for k,v in b.most_common(6)},'alone share %.2f'%(sum(x['alone'] for x in Z)/n))
