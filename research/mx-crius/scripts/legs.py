"""Walking legs of one champion type (default Prism), rounds <= END: each moving round is attributed to the leg it is in,
by what started the leg (spawn: recall end or respawn or round 1; camp: a hit on a camp; altar: tribute end/cancel) and
what ends it (camp hit, tribute start, recall end). usage: py legs.py EXTRACT [END] [TYPE]"""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; END=int(sys.argv[2]) if len(sys.argv)>2 else 600; TY=sys.argv[3] if len(sys.argv)>3 else 'Prism'
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); typ={c['id']:CH[c['type']] for c in m['champions']}
    ids=[c['id'] for c in m['champions'] if typ[c['id']]==TY]
    R=json.load(gzip.open(d+'/rounds.json.gz')); rr=R['round']; ri={r:i for i,r in enumerate(rr)}
    ch={c['id']:c for c in R['champions']}
    marks=collections.defaultdict(list)
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); r=e['r']
        if r>END: break
        k=e['k']; a=e.get('a')
        if k in ('attack','cast') and e.get('cdmg') and a in ids: marks[a].append((r,'camp'))
        elif k=='tribute_start' and a in ids: marks[a].append((r,'tribute'))
        elif k in ('tribute_end','tribute_cancel') and a in ids: marks[a].append((r,'altar'))
        elif k=='recall_end' and a in ids: marks[a].append((r,'spawn'))
        elif k=='respawn' and e.get('a',e.get('c')) in ids: marks[e.get('a',e.get('c'))].append((r,'spawn'))
    out=collections.Counter()
    for cid in ids:
        c=ch.get(cid)
        if not c: continue
        mk=sorted(marks[cid]); j=0; prev='spawn'
        if not mk: continue
        for i,r in enumerate(rr):
            if r>END: break
            while j<len(mk) and mk[j][0]<r: prev=mk[j][1]; j+=1
            if i==0 or not c['alive'][i] or c['x'][i] is None or c['x'][i-1] is None: continue
            if (c['x'][i],c['y'][i])==(c['x'][i-1],c['y'][i-1]): continue
            nxt=mk[j][1] if j<len(mk) else 'end'
            if prev=='tribute': prev='altar'
            out[(prev,nxt)]+=1
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one,ds,chunksize=8): tot.update(o)
    T=sum(tot.values())
    print(TY,'moving rounds a game %.1f'%(T/len(ds)))
    for k,v in tot.most_common(12): print('  %-8s -> %-8s %.1f%%  (%.1f a game)'%(k[0],k[1],100*v/T,v/len(ds)))
