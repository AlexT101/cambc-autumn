import json,gzip,glob,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
TYPE=sys.argv[2] if len(sys.argv)>2 else 'Prism'
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    meta=json.load(open(d+'/meta.json'))
    mp=json.load(open(os.path.join(ROOT,d.split('/')[-1],meta['mapFile'])) if False else open(os.path.normpath(os.path.join(d,meta['mapFile']))))
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    out=collections.Counter(); segs=[]
    camp_group={c['id']:c['group'] for c in mp['camps']}
    gpos={g['id']:[(c['x'],c['y']) for c in mp['camps'] if c['group']==g['id']] for g in mp['groups']}
    # group state forward fill
    nr=len(R['round']); rid={r:i for i,r in enumerate(R['round'])}
    gstate={}
    st=collections.defaultdict(dict)
    for row in R['groups']:
        st[row[1]][row[0]]=row[2]
    def state_at(g,r):
        best=None
        for rr,s in st[g].items():
            if rr<=r and (best is None or rr>best[0]): best=(rr,s)
        return best[1] if best else 1
    for ci,c in enumerate(R['champions']):
        t=en[meta['champions'][ci]['type']]
        if t!=TYPE: continue
        cid=c['id']; team=c['team']
        hit={} # round -> group
        trib=set(); 
        for e in ev:
            if e.get('a')!=cid: continue
            if e['k'] in('attack','cast') and e.get('cdmg'):
                hit.setdefault(e['r'],camp_group.get(e['cdmg'][0][0]))
            if e['k']=='tribute_start': trib.add(e['r'])
        rounds=R['round']
        last_work=None
        walk_start=None
        for i,r in enumerate(rounds):
            if r>600: break
            if not c['alive'][i]: out['dead']+=1; continue
            moved = i>0 and c['x'][i-1] is not None and (c['x'][i]!=c['x'][i-1] or c['y'][i]!=c['y'][i-1])
            tele = moved and i>0 and cheb((c['x'][i],c['y'][i]),(c['x'][i-1],c['y'][i-1]))>2
            if r in hit:
                out['hit']+=1
                if walk_start is not None:
                    g=hit[r]; p=(c['x'][walk_start[0]],c['y'][walk_start[0]])
                    # nearest group with monsters up at departure
                    dg=min(cheb(p,q) for q in gpos[g]) if g in gpos else -1
                    near=min((min(cheb(p,q) for q in gpos[h]) for h in gpos if state_at(h,walk_start[1])==1),default=-1)
                    segs.append((r-walk_start[1], dg, near, gpos and mp['groups'][g]['gems'] if g is not None and g<len(mp['groups']) else 0))
                walk_start=None; last_work=r
            elif c['chan'][i]==2: out['tribute']+=1
            elif c['chan'][i]==1 and c['chanT'][i]<4: out['recall']+=1
            elif tele: out['arrive']+=1
            elif moved:
                out['walk']+=1
                if walk_start is None: walk_start=(i,r)
            else: out['still']+=1
    return out,segs
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    tot=collections.Counter(); S=[]
    with ProcessPoolExecutor(48) as ex:
        for o,s in ex.map(one,ds,chunksize=4): tot+=o; S+=s
    n=sum(tot.values()); print(TYPE,{k:f"{100*v/n:.1f}%" for k,v in tot.most_common()})
    import statistics
    print('walk segments ending in a hit:',len(S),'mean len',statistics.mean(x[0] for x in S))
    long=[x for x in S if x[0]>=10]
    print('>=10 rounds:',len(long),'share of seg rounds',sum(x[0] for x in long)/sum(x[0] for x in S))
    print('target cheb dist mean',statistics.mean(x[1] for x in S),'nearest up-group dist mean',statistics.mean(x[2] for x in S if x[2]>=0))
    farther=[x for x in S if x[2]>=0 and x[1]>x[2]+5]
    print('target >5 farther than nearest up group:',len(farther)/len(S), 'rounds share', sum(x[0] for x in farther)/sum(x[0] for x in S))
