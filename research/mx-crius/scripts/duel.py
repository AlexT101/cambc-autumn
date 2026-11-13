"""Prism duels: encounters (the two Prisms within 6, none in the 10 rounds before), what follows within 30 rounds
(one Prism kills the other, or neither), by the bag ratio and HP at onset; and Prism-on-Prism kills by bag order."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json'))
    typ={c['id']:CH[c['type']] for c in m['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rr=R['round']; ri={r:i for i,r in enumerate(rr)}
    P=[c for c in R['champions'] if typ[c['id']]=='Prism']
    if len(P)!=2: return []
    a,b=P
    kills=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e['v'] in (a['id'],b['id']) and e.get('by') in (a['id'],b['id']): kills.append((e['r'],e['by']))
    out=[]; last=-99
    for i,r in enumerate(rr):
        if not (a['alive'][i] and b['alive'][i]) or a['x'][i] is None or b['x'][i] is None: continue
        dd=max(abs(a['x'][i]-b['x'][i]),abs(a['y'][i]-b['y'][i]))
        if dd<=6:
            if r-last>10:
                ga,gb=a['gems'][i] or 0,b['gems'][i] or 0
                ha,hb=a['hp'][i]/a['maxHp'][i],b['hp'][i]/b['maxHp'][i]
                k=[x for x in kills if r<=x[0]<=r+30]
                res='none' if not k else ('a' if k[0][1]==a['id'] else 'b')
                # orient: s = richer
                if ga>=gb: out.append((ga,gb,ha,hb,{'a':'rich','b':'poor','none':'none'}[res],r))
                else: out.append((gb,ga,hb,ha,{'a':'poor','b':'rich','none':'none'}[res],r))
            last=r
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    print('encounters',len(S),collections.Counter(s[4] for s in S).most_common())
    def tab(lab,f,bins):
        print(lab)
        for lo,hi in bins:
            X=[s for s in S if lo<=f(s)<hi]
            if X:
                c=collections.Counter(s[4] for s in X); print('  [%s,%s) n=%6d richer kills %.1f%% poorer kills %.1f%% none %.1f%%'%(lo,hi,len(X),100*c['rich']/len(X),100*c['poor']/len(X),100*c['none']/len(X)))
    tab('by bag ratio poor/rich',lambda s:s[1]/max(1,s[0]),[(0,.25),(.25,.5),(.5,.75),(.75,.9),(.9,1.01)])
    tab('by bag gap rich-poor',lambda s:s[0]-s[1],[(0,10),(10,30),(30,60),(60,120),(120,250),(250,9999)])
    tab('near-equal bags (gap<30): by hp diff rich-poor',lambda s:(s[2]-s[3]) if s[0]-s[1]<30 else 99,[(-1,-.3),(-.3,-.1),(-.1,.1),(.1,.3),(.3,1.01)])
