"""Middle groups (zone 0.4-0.6), each cycle from availability (round 1 or group_respawn) to its capture: who woke it
(team), who captured, contested resets, enemy champions within 8 of the group at the wake and at the capture, and the
lag from availability to wake. Winner's view. usage: py midcycle.py EXTRACT [END]"""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; END=int(sys.argv[2]) if len(sys.argv)>2 else 600
def one(d):
    m=json.load(open(d+'/meta.json')); w=m['result']['winner']; team={c['id']:c['team'] for c in m['champions']}
    mp=json.load(open(os.path.join(d,m['mapFile']))); camps={c['id']:c for c in mp['camps']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rr=R['round']; ri={r:i for i,r in enumerate(rr)}
    cen={}
    for t in (0,1):
        xs=[(c['x'][0],c['y'][0]) for c in R['champions'] if c['team']==t and c['x'][0] is not None]
        cen[t]=(sum(a for a,b in xs)/len(xs),sum(b for a,b in xs)/len(xs))
    mid={}; gpos={}; gems={}
    for g in mp['groups']:
        ps=[(camps[c]['x'],camps[c]['y']) for c in g['camps']]
        x=sum(a for a,b in ps)/len(ps); y=sum(b for a,b in ps)/len(ps); gpos[g['id']]=(x,y)
        do=max(abs(x-cen[w][0]),abs(y-cen[w][1])); de=max(abs(x-cen[1-w][0]),abs(y-cen[1-w][1]))
        s=do/max(1e-9,do+de)
        if 0.4<=s<=0.6: mid[g['id']]=s
    def near(i,g,t):
        x,y=gpos[g]; n=0
        for c in R['champions']:
            if c['team']==t and c['alive'][i] and c['x'][i] is not None and max(abs(c['x'][i]-x),abs(c['y'][i]-y))<=8: n+=1
        return n
    avail={g:1 for g in mid}; woke={}; resets=collections.Counter(); out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); r=e['r']
        if r>END: break
        g=e.get('g')
        if g not in mid: continue
        k=e['k']
        if k=='group_respawn': avail[g]=r; woke.pop(g,None); resets[g]=0
        elif k=='group_wake' and g not in woke:
            i=ri.get(r)
            woke[g]=(r,team.get(e.get('by'),-1),near(i,g,w) if i is not None else 0,near(i,g,1-w) if i is not None else 0)
        elif k=='capture_reset' and e.get('contested'): resets[g]+=1
        elif k=='capture':
            i=ri.get(r); wk=woke.get(g,(r,-1,0,0))
            out.append(dict(cap=e['team']==w, woke=wk[1]==w, wakeW=wk[2], wakeL=wk[3], lag=wk[0]-avail.get(g,1),
                            capW=near(i,g,w) if i is not None else 0, capL=near(i,g,1-w) if i is not None else 0, res=resets[g], gems=sum(s[1] for s in e['shares'])))
            woke.pop(g,None)
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    n=len(S); G=sum(s['gems'] for s in S)
    print('middle captures',n,'winner took %.1f%% of them, %.1f%% of gems'%(100*sum(s['cap'] for s in S)/n,100*sum(s['gems'] for s in S if s['cap'])/G))
    print('waker captured: %.1f%%'%(100*sum(1 for s in S if s['cap']==s['woke'])/n))
    print('winner woke %.1f%%'%(100*sum(s['woke'] for s in S)/n))
    for lab,f in (('no enemy of the waker within 8 at wake',lambda s:(s['wakeL'] if s['woke'] else s['wakeW'])==0),('enemy of the waker present at wake',lambda s:(s['wakeL'] if s['woke'] else s['wakeW'])>0)):
        X=[s for s in S if f(s)]; print('  %s: n=%d (%.0f%%) waker captured %.1f%%'%(lab,len(X),100*len(X)/n,100*sum(1 for s in X if s['cap']==s['woke'])/max(1,len(X))))
    X=[s for s in S if s['res']>0]; print('with contested resets: %d (%.0f%%), winner took %.1f%%'%(len(X),100*len(X)/n,100*sum(s['cap'] for s in X)/max(1,len(X))))
    print('stolen (waker lost it): %.1f%% of gems'%(100*sum(s['gems'] for s in S if s['cap']!=s['woke'])/G))
    q=sorted(s['lag'] for s in S); print('lag availability->wake q',q[n//4],q[n//2],q[3*n//4])
