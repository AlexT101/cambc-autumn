# The rounds before an enemy-started, enemy-outnumbering engagement: pack strength in the first target's sight and its steps.
import sys, json, gzip, pickle, collections
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def run2(pk,opp,maxr=250,gap=6):
    G=pickle.load(open(pk,'rb')); seen=set(); rows=[]
    for g in G:
        if g['match'] in seen or (opp and g['opp']!=opp): continue
        seen.add(g['match']); d0=g['dir']; us=g['us']
        meta=json.load(open(d0+'/meta.json')); R=json.load(gzip.open(d0+'/rounds.json.gz'))
        ch=R['champions']; team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:c['name'] for c in meta['champions']}
        hits=[]; deaths=[]; act=collections.defaultdict(lambda:collections.defaultdict(str))
        for l in gzip.open(d0+'/events.jsonl.gz','rt'):
            e=json.loads(l)
            if e['r']>maxr+30: break
            if e['k'] in('attack','cast'):
                for t,dm in e.get('dmg',[]): hits.append((e['r'],e['a'],t,dm))
                act[e['r']][e['a']]+=('C' if ('cdmg' in e or 'camp' in e) else ('H' if e.get('dmg') else 'c'))
            if e['k']=='death' and 'camp' not in e and e.get('by') is not None: deaths.append((e['r'],e['v']))
        E=[]; cur=None
        for h in hits:
            if h[0]>maxr and (not cur or h[0]-cur['r1']>gap): break
            if cur and h[0]-cur['r1']<=gap: cur['hits'].append(h); cur['r1']=h[0]
            else: cur=dict(r0=h[0],r1=h[0],hits=[h]); E.append(cur)
        P=lambda c,i:(c['x'][i],c['y'][i])
        sp=[None,None]
        for t in (0,1):
            xs=[P(c,0) for c in ch if c['team']==t]; sp[t]=(sum(p[0] for p in xs)/len(xs),sum(p[1] for p in xs)/len(xs))
        for en in E:
            r0,r1=en['r0'],en['r1']; i=max(r0-2,0)
            a0,t0=en['hits'][0][1],en['hits'][0][2]
            if team[a0]==us: continue
            T=ch[t0]; c0=P(T,i)
            if c0[0] is None: continue
            mine=[c for c in ch if c['team']==us and c['alive'][i] and cheb(P(c,i),c0)<=8]
            theirs=[c for c in ch if c['team']!=us and c['alive'][i] and cheb(P(c,i),c0)<=8]
            if len(theirs)<=len(mine): continue
            died=any(v==t0 and r0<=r<=r1+1 for r,v in deaths)
            k=[0,0]
            for r,v in deaths:
                if r0<=r<=r1+1 and typ[v]!='Issac': k[0 if team[v]!=us else 1]+=1
            row=dict(map=g['map'],side=g['side'],opp=g['opp'],r0=r0,tgt=typ[t0],died=died,net=k[0]-k[1],steps=[],dir=d0,us=us)
            for kk in range(0,6):
                j=i-kk
                if j<1 or not T['alive'][j] or not T['alive'][j-1]: break
                p=P(T,j); pp=P(T,j-1)
                es=[c for c in ch if c['team']!=us and c['alive'][j]]
                al=[c for c in ch if c['team']==us and c['alive'][j] and cheb(P(c,j),p)<=6 and (c['id']==t0 or c['id'] in T['sees'][j])]
                ah=sum(c['hp'][j]+c['shield'][j] for c in al); ad=sum(c['str'][j] for c in al)
                st=dict(k=kk,p=p,home=cheb(p,sp[us])<=cheb(p,sp[1-us]),hp=T['hp'][j]/T['maxHp'][j],na=len(al),act=act[r0-1-kk][t0])
                for Rr in (5,6,7,8):
                    ne=[c for c in es if cheb(P(c,j),p)<=Rr and c['id'] in T['sees'][j]]
                    st['n%d'%Rr]=len(ne)
                    st['q%d'%Rr]=(sum(c['hp'][j]+c['shield'][j] for c in ne)*sum(c['str'][j] for c in ne))/max(1.0,ah*ad)
                # movement during round r0-1-kk relative to the pack (enemies within 8 at the hit) positions at j-1
                ex=[P(c,j-1) for c in theirs if c['alive'][j-1]]
                if ex:
                    cx=sum(q[0] for q in ex)/len(ex); cy=sum(q[1] for q in ex)/len(ex)
                    d1=max(abs(p[0]-cx),abs(p[1]-cy)); d0_=max(abs(pp[0]-cx),abs(pp[1]-cy))
                    st['mv']='T' if d1<d0_-0.5 else 'A' if d1>d0_+0.5 else ('S' if p==pp else 'L')
                else: st['mv']='?'
                row['steps'].append(st)
            rows.append(row)
    return rows
if __name__=='__main__':
    pk,opp=sys.argv[1:3]
    rows=run2(pk,opp); n=len(rows)
    print(opp,n)
    for kk in range(0,4):
        rs=[r for r in rows if len(r['steps'])>kk]; m=len(rs)
        f=lambda fn: sum(1 for r in rs if fn(r['steps'][kk]))/m
        mv=collections.Counter(r['steps'][kk]['mv'] for r in rs)
        print(' k=%d m %d seen-only: '%(kk,m)+' '.join('R%d n %.2f q>2.17 %.2f home& %.2f |'%(R,sum(r['steps'][kk]['n%d'%R] for r in rs)/m,f(lambda s:s['q%d'%R]>2.17),f(lambda s:s['home'] and s['q%d'%R]>2.17)) for R in (5,6,7,8)),'move in that round:',{a:round(b/m,2) for a,b in mv.items()},'acts',dict(collections.Counter('camp' if 'C' in r['steps'][kk]['act'] else 'champ' if 'H' in r['steps'][kk]['act'] else '-' for r in rs)))
    # when the zone (seen, R) covered at k: movement that round and the next (k-1), outcome
    for R in (5,6,7,8):
        a=[r for r in rows if len(r['steps'])>2 and r['steps'][2]['home'] and r['steps'][2]['q%d'%R]>2.17]
        if a:
            print('  home, seen q%d>2.17 at k=2: n %d | net %.2f died %.2f | moves k=1: %s k=0: %s | camp-hitting at k<=1: %.2f'%(R,len(a),sum(r['net'] for r in a)/len(a),sum(r['died'] for r in a)/len(a),dict(collections.Counter(r['steps'][1]['mv'] for r in a)),dict(collections.Counter(r['steps'][0]['mv'] for r in a)),sum(1 for r in a if 'C' in r['steps'][0]['act']+r['steps'][1]['act'])/len(a)))
    pickle.dump(rows,open('rows-%s-%s.pkl'%(pk.split('/')[-1].split('.')[0],opp),'wb'))
