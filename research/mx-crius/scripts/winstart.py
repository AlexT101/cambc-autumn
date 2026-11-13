"""Each winning tribute start (tributed + bag >= 1000) by a Prism: completes or how it ends, by channel length, allies
and enemies near the altar at the start. usage: py winstart.py EXTRACT"""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; WIN=len(sys.argv)<3
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json'))
    typ={c['id']:CH[c['type']] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    open_={}; out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); k=e['k']
        if k=='tribute_start' and typ[e['a']]=='Prism':
            i=ri.get(e['r'])
            if i is None: continue
            t=team[e['a']]
            if (R['gems'][t][i]+e['gems']>=1000)!=WIN: continue
            ax,ay=e['altar']; al=en=enf=0; dead=0; alive=0
            for c in R['champions']:
                if c['team']!=t and c['id']!=e['a']:
                    if c['alive'][i]: alive+=1
                    else: dead+=1
                if c['id']==e['a'] or not c['alive'][i] or c['x'][i] is None: continue
                dd=max(abs(c['x'][i]-ax),abs(c['y'][i]-ay))
                if c['team']==t: al+=dd<=5
                else: en+=dd<=8; enf+=dd<=16
            open_[e['a']]=dict(r=e['r'],dur=e['dur'],al=al,en=en,enf=enf,ealive=alive,edead=dead)
        elif k in ('tribute_end','tribute_cancel') and e['a'] in open_:
            x=open_.pop(e['a']); x['end']='done' if k=='tribute_end' else e.get('cause'); x['ran']=e['r']-x['r']; out.append(x)
        elif k=='death' and e['v'] in open_:
            x=open_.pop(e['v']); x['end']='death'; x['ran']=e['r']-x['r']; out.append(x)
    for x in open_.values(): x['end']='gameover'; x['ran']=0; out.append(x)
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    n=len(S); print('winning Prism starts',n,collections.Counter(s['end'] for s in S).most_common())
    def tab(lab,f,bins):
        print(lab)
        for lo,hi in bins:
            X=[s for s in S if lo<=f(s)<hi]
            if X:
                c=collections.Counter(s['end'] for s in X)
                print('  [%s,%s) n=%5d done %.1f%% stun %.1f%% lock %.1f%% manual %.1f%% death %.1f%%'%(lo,hi,len(X),*(100*c[k]/len(X) for k in ('done','stun','lock','manual','death'))))
    tab('by channel turns',lambda s:s['dur'],[(1,20),(20,40),(40,60),(60,80),(80,100),(100,999)])
    tab('by enemies within 8 of the altar',lambda s:s['en'],[(0,1),(1,2),(2,3),(3,9)])
    tab('enemies within 16 (none within 8)',lambda s:s['enf'] if s['en']==0 else -1,[(0,1),(1,2),(2,3),(3,9)])
    tab('by allies within 5',lambda s:s['al'],[(0,1),(1,2),(2,3),(3,9)])
    tab('by enemies alive at start',lambda s:s['ealive'],[(0,1),(1,2),(2,3),(3,4),(4,9)])
    X=[s for s in S if s['end']!='done']; q=sorted(s['ran'] for s in X); print('failed starts: turns run q',q[len(q)//4],q[len(q)//2],q[3*len(q)//4])
