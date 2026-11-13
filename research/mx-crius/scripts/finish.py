"""Winning bags (a champion whose tribute alone wins: tributed + its bag >= 1000), both teams: what happens from the
first such round. Per episode: rounds to the first tribute start, starts, cancels by cause, death, outcome."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); w=m['result']['winner']; end=m['result']['rounds']
    typ={c['id']:CH[c['type']] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rr=R['round']
    first={}
    for i,r in enumerate(rr):
        for c in R['champions']:
            if c['id'] in first: continue
            b=c['gems'][i] or 0
            if b and R['gems'][c['team']][i]+b>=1000: first[c['id']]=(r,b,R['gems'][1-c['team']][i])
    if not first: return []
    ev=collections.defaultdict(lambda: dict(starts=0,cancel=collections.Counter(),died=None,start1=None,ends=0,lockcancel=0))
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); r=e['r']; k=e['k']
        a=e.get('a', e.get('v'))
        if a not in first or r<first[a][0]: continue
        x=ev[a]
        if k=='tribute_start': x['starts']+=1; x['start1']=x['start1'] or r
        elif k=='tribute_cancel': x['cancel'][e.get('cause')]+=1
        elif k=='tribute_end': x['ends']+=1
        elif k=='death' and e.get('v')==a and x['died'] is None: x['died']=r
    out=[]
    for cid,(r,b,E) in first.items():
        x=ev[cid]
        out.append(dict(ty=typ[cid],won=w==team[cid],r=r,b=b,E=E,end=end,**{k:x[k] for k in ('starts','died','start1','ends')},cancel=dict(x['cancel'])))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    P=[s for s in S if s['ty']=='Prism' and s['b']>=300]
    print('Prism winning bags >=300:',len(P),'won %.1f%%'%(100*sum(s['won'] for s in P)/len(P)))
    L=[s for s in P if not s['won']]; W=[s for s in P if s['won']]
    for lab,X in (('won',W),('lost',L)):
        n=len(X)
        st=[s['start1']-s['r'] for s in X if s['start1']]
        st.sort()
        print(lab,n,'start a tribute %.0f%%'%(100*len(st)/n),'delay q',st[len(st)//4] if st else '-',st[len(st)//2] if st else '-',st[3*len(st)//4] if st else '-',
              'starts/ep %.2f'%(sum(s['starts'] for s in X)/n),'died %.0f%%'%(100*sum(1 for s in X if s['died'])/n),
              'cancel causes',dict(sum((collections.Counter(s['cancel']) for s in X),collections.Counter())),
              'bag q',sorted(s['b'] for s in X)[n//2],'enemy tributed q',sorted(s['E'] for s in X)[n//2])
    # lost: what came first, death or never started
    c=collections.Counter()
    for s in L:
        if s['died'] and (not s['start1'] or s['died']<=s['start1']): c['died before any start']+=1
        elif not s['start1']: c['never started, alive']+=1
        elif s['died']: c['started, later died']+=1
        else: c['started, alive, lost the race']+=1
    print('lost episodes:',c.most_common())
    T=[s for s in L if not s['died'] and s['start1']]
    print('  alive-started losses: rounds left after first start q',sorted(s['end']-s['start1'] for s in T)[len(T)//2] if T else '-', 'channel need q',sorted((s['b']+9)//10 for s in T)[len(T)//2] if T else '-')
    for lab,X in (('won',W),('lost',L)):
        q=sorted(s['end']-s['r'] for s in X); n=len(q)
        print(lab,'rounds from winning bag to game end q',q[n//4],q[n//2],q[3*n//4],'p90',q[9*n//10])
    # winners: did the Prism's own tribute end the game?
    print('won by the Prism tribute completing: %.0f%%'%(100*sum(1 for s in W if s['ends'])/len(W)))
    # by bag size: win rate and endgame length
    for lo,hi in ((300,500),(500,700),(700,900),(900,3000)):
        X=[s for s in P if lo<=s['b']<hi]
        if X: print('bag [%d,%d) n=%d win %.0f%% median end-r %d'%(lo,hi,len(X),100*sum(s['won'] for s in X)/len(X),sorted(s['end']-s['r'] for s in X)[len(X)//2]))
