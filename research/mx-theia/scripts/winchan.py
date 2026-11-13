# Winning-size tribute channels (score + bag >= 1000 at start) by side: outcome (done / cancel cause / still running
# at the end), and for completed ones: the other side's alive bodies, nearest one's distance to the channeller at the
# start and its minimum during the channel, whether any was within 4 at any time. Args: DIR -12.
import json,gzip,sys,os,collections,statistics
ROOT=sys.argv[1]
idx=json.load(open(ROOT+'/index.json')); rows={}
for g in idx['games']: rows.setdefault(g['dir'],g)
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
C=collections.Counter(); dmin=collections.defaultdict(list); d0=collections.defaultdict(list); alive=collections.defaultdict(list)
for dn,row in rows.items():
    src=row['source']; ci=0 if src.endswith('-12.repl26a') else 1
    d=os.path.join(ROOT,dn); meta=json.load(open(d+'/meta.json')); team={x['id']:x['team'] for x in meta['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rd={r:i for i,r in enumerate(R['round'])}; CH={c['id']:c for c in R['champions']}
    open_={}
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='tribute_start':
            t=team[e['a']]; i=rd.get(e['r'])
            if i is not None and R['gems'][t][i]+e['gems']>=1000: open_[e['a']]=(e['r'],t)
        elif e['k'] in ('tribute_end','tribute_cancel') and e['a'] in open_:
            r0,t=open_.pop(e['a']); side='CAND' if t==ci else 'REF'
            out='done' if e['k']=='tribute_end' else e.get('cause')
            C[(side,out)]+=1
            if out=='done':
                foes=[c for c in R['champions'] if c['team']!=t]
                i0=rd[r0]; i1=rd.get(e['r'],len(R['round'])-1); me=CH[e['a']]
                ds=[cheb((c['x'][i0],c['y'][i0]),(me['x'][i0],me['y'][i0])) for c in foes if c['alive'][i0]]
                alive[side].append(len(ds)); d0[side].append(min(ds) if ds else 99)
                m=min([cheb((c['x'][j],c['y'][j]),(me['x'][j],me['y'][j])) for j in range(i0,i1+1) for c in foes if c['alive'][j]] or [99])
                dmin[side].append(m)
    for a,(r0,t) in open_.items(): C[('CAND' if t==ci else 'REF','running at end')]+=1
for side in ('CAND','REF'):
    print(side,'winning channels:',{k[1]:v for k,v in C.items() if k[0]==side})
    if dmin[side]: print('  completed: foes alive mean %.1f; nearest foe at start median %d; min during channel median %d; within 4 at some point %.2f; none alive %.2f'%(statistics.mean(alive[side]),statistics.median(d0[side]),statistics.median(dmin[side]),sum(x<=4 for x in dmin[side])/len(dmin[side]),sum(a==0 for a in alive[side])/len(alive[side])))
