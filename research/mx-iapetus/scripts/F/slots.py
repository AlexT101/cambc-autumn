# For our deaths to an enemy Prism whose first hit our threat read missed (DX bound 0 at our turn before it):
# did the Prism take two turns before our next one (after us in round x, before us in x+1), and how many
# enemies were nearer our turn start than it (pick_second fills the room before our slot by distance)?
import json,gzip,collections,sys
A='replays/.an-F1/'; G=json.load(open('/tmp/mxi-F1-deaths.json'))
idx={r['source'].split('/')[-1]:r['dir'] for r in json.load(open(A+'index.json'))['games']}
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
C=collections.Counter()
for g in G:
    cases=[]
    for d in g['deaths']:
        if not d['ours'] or d['camp'] or d['byname']!='Prism': continue
        s=d.get('seq') or {}; dxs=d.get('dx') or {}
        per=collections.Counter()
        for rr,a,ab,am in d['dmg']:
            if str(a)==str(d['by']): per[rr]+=am
        if not per: continue
        rk=min(per); x=next((x for x in range(rk-1,rk-4,-1) if str(x) in dxs),None)
        if x is None or s.get(str(x))=='E': continue
        cases.append((d,x,rk,dxs[str(x)][3]==0))
    if not cases: continue
    dr=idx[g['src']]
    R=json.load(gzip.open(A+dr+'/rounds.json.gz')); ri={v:i for i,v in enumerate(R['round'])}; ch={c['id']:c for c in R['champions']}
    need={(x,) for d,x,rk,z in cases}|{(x+1,) for d,x,rk,z in cases}|{(rk,) for d,x,rk,z in cases}
    T=collections.defaultdict(dict)
    for e in gzip.open(A+dr+'/events.jsonl.gz','rt'):
        e=json.loads(e)
        if (e['r'],) in need and 'a' in e and e['t']>=0: T[e['r']].setdefault(e['a'],e['t'])
    for d,x,rk,zero in cases:
        v=d['v']; k=d['by']
        tv=T[x].get(v); tk=T[x].get(k)
        if None in (tv,tk) or rk!=x+1: C['no slots']+=1; continue
        two = tk>tv
        tk1=T[x+1].get(k); tv1=sum(1 for o,t in T[x+1].items() if ch[o]['team']==ch[v]['team'] and t<99)
        i=ri.get(x-1)
        if i is None: continue
        pv=(ch[v]['x'][i],ch[v]['y'][i]); pk=(ch[k]['x'][i],ch[k]['y'][i])
        if None in pv or None in pk: continue
        dk=cheb(pv,pk)
        nearer=sum(1 for o in ch if ch[o]['team']!=ch[v]['team'] and o!=k and ch[o]['alive'][i] and ch[o]['x'][i] is not None and cheb(pv,(ch[o]['x'][i],ch[o]['y'][i]))<=dk)
        room=None
        key='zero' if zero else 'read'
        C[(key,'two turns' if two else 'one turn')]+=1
        if two: C[(key,'two: nearer %d'%min(nearer,4))]+=1; C[(key,'two: killer slot in x+1 %s'%tk1)]+=1
for k,v in sorted(C.items(),key=str): print(k,v)
