import json,gzip,glob,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; WHO=sys.argv[2]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx={g['dir']:g['teams'] for g in json.load(open(ROOT+'/index.json'))['games']}
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    meta=json.load(open(d+'/meta.json')); tn=idx.get(os.path.basename(d))
    if not tn or WHO not in tn: return None
    us=tn.index(WHO)
    pr={c['id']:c['team'] for c in meta['champions'] if en[c['type']]=='Prism'}
    if len(pr)!=2: return None
    typ={c['id']:en[c['type']] for c in meta['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rid={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    f=None
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e['v'] in pr: f=e; break
    if f is None or pr[f['v']]!=us: return None
    v=f['v']; o=[p for p in pr if p!=v][0]; i=rid.get(f['r']-1,0)
    ratio=C[v]['foc'][i]/max(1,C[o]['foc'][i])
    allies=sum(1 for c in R['champions'] if c['team']==us and c['id']!=v and c['alive'][i] and c['x'][i] is not None and C[v]['x'][i] is not None and cheb((c['x'][i],c['y'][i]),(C[v]['x'][i],C[v]['y'][i]))<=8)
    enem=sum(1 for c in R['champions'] if c['team']!=us and c['alive'][i] and c['x'][i] is not None and C[v]['x'][i] is not None and cheb((c['x'][i],c['y'][i]),(C[v]['x'][i],C[v]['y'][i]))<=8)
    return (f['r'],ratio,typ.get(f.get('by'),'camp/none'),f.get('gems',0),allies,enem, meta['result']['winner']==us)
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[s for s in ex.map(one,ds,chunksize=4) if s]
    n=len(S); print(WHO,'our Prism first deaths',n)
    print('round median',sorted(x[0] for x in S)[n//2],'ratio <0.8 %.2f 0.8-1.25 %.2f >1.25 %.2f'%(sum(x[1]<0.8 for x in S)/n,sum(0.8<=x[1]<=1.25 for x in S)/n,sum(x[1]>1.25 for x in S)/n))
    print('killer',collections.Counter(x[2] for x in S).most_common(5),'bag median',sorted(x[3] for x in S)[n//2])
    print('allies within 8: 0 -> %.2f; enemies>allies %.2f'%(sum(x[4]==0 for x in S)/n,sum(x[5]>x[4] for x in S)/n))
    print('before r300 %.2f'%(sum(x[0]<300 for x in S)/n))
