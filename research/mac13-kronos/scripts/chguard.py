import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz')); C={c['id']:c for c in o['champions']}
    starts={}; rows=[]
    def near(a,r,rad,same):
        x,y=C[a]['x'][r],C[a]['y'][r]; n=0
        if x is None: return 0
        for c in o['champions']:
            if c['id']==a or not c['alive'][r]: continue
            if (c['team']==team[a])!=same or c['x'][r] is None: continue
            if max(abs(c['x'][r]-x),abs(c['y'][r]-y))<=rad: n+=1
        return n
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k'] not in ('tribute_start','tribute_end','tribute_cancel'): continue
        a=e['a']
        if names.get(a)!='Prism': continue
        if e['k']=='tribute_start':
            if e['gems']>=300: starts[a]=e
        elif a in starts:
            s=starts.pop(a); r0=min(s['r'],len(o['round'])-1); r1=min(e['r'],len(o['round'])-1)
            res=e['k'] if e['k']!='tribute_cancel' else 'cancel_'+e.get('cause','')
            rows.append((res, near(a,r0,4,True), near(a,r0,8,False), near(a,r1,4,True), near(a,r1,8,False), near(a,r1,4,False)))
    return rows
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[r for x in p.map(one,fs,chunksize=8) if x for r in x]
    by=collections.defaultdict(list)
    for r in R: by[r[0]].append(r)
    for k,v in by.items():
        print(k,len(v),'start: allies<=4 %.2f enemies<=8 %.2f | end: allies<=4 %.2f enemies<=8 %.2f enemies<=4 %.2f'%tuple(statistics.mean(x[i] for x in v) for i in range(1,6)))
    # completion by enemies within 8 at start
    for e8 in range(4):
        sel=[r for r in R if min(r[2],3)==e8]; 
        if sel: print('enemies<=8 at start',e8,len(sel),'complete',round(sum(r[0]=='tribute_end' for r in sel)/len(sel),3))
    for a4 in range(4):
        sel=[r for r in R if min(r[1],3)==a4]
        if sel: print('allies<=4 at start',a4,len(sel),'complete',round(sum(r[0]=='tribute_end' for r in sel)/len(sel),3))
