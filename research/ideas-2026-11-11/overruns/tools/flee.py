# For enemy-initiated engagements with enemy numbers: did the first target move away from the attackers before/after the first hit?
import sys,json,gzip,pickle,collections
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def run(pk,tag,maxr=250,gap=6):
    G=pickle.load(open(pk,'rb')); seen=set(); S=collections.defaultdict(collections.Counter); ex=[]
    for g in G:
        if g['match'] in seen: continue
        seen.add(g['match']); d0=g['dir']; us=g['us']
        meta=json.load(open(d0+'/meta.json')); R=json.load(gzip.open(d0+'/rounds.json.gz'))
        ch=R['champions']; team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:c['name'] for c in meta['champions']}
        hits=[]; deaths=[]; stuns=collections.defaultdict(set); own_hits=collections.defaultdict(set)
        for l in gzip.open(d0+'/events.jsonl.gz','rt'):
            e=json.loads(l)
            if e['r']>maxr+30: break
            if e['k'] in('attack','cast'):
                for t,dm in e.get('dmg',[]): hits.append((e['r'],e['a'],t,dm)); own_hits[e['r']].add(e['a'])
                for t in e.get('stun',[]) or []: stuns[e['r']].add(t)
            if e['k']=='death' and 'camp' not in e and e.get('by') is not None: deaths.append((e['r'],e['v']))
        E=[]; cur=None
        for h in hits:
            if cur and h[0]-cur['r1']<=gap: cur['hits'].append(h); cur['r1']=h[0]
            else:
                if h[0]>maxr: break
                cur=dict(r0=h[0],r1=h[0],hits=[h]); E.append(cur)
        for en in E:
            r0,r1=en['r0'],en['r1']; i=max(r0-2,0)
            a0,t0=en['hits'][0][1],en['hits'][0][2]
            if team[a0]==us: continue
            P=lambda c,i:(c['x'][i],c['y'][i])
            c0=P(ch[t0],i)
            if c0[0] is None: continue
            mine=[c for c in ch if c['team']==us and c['alive'][i] and cheb(P(c,i),c0)<=8]
            theirs=[c for c in ch if c['team']!=us and c['alive'][i] and cheb(P(c,i),c0)<=8]
            if len(theirs)<=len(mine): continue
            died=any(v==t0 and r0<=r<=r1+1 for r,v in deaths)
            s=S[(tag,g['opp'],'died' if died else 'lived')]; s['n']+=1
            # approach: nearest enemy distance to target at r0-6..r0-1 (end of round indices)
            def nd(j):
                es=[cheb(P(c,j),P(ch[t0],j)) for c in ch if c['team']!=us and c['alive'][j] and c['x'][j] is not None]
                return min(es) if es and ch[t0]['x'][j] is not None else None
            def n_within(j,rad):
                return sum(1 for c in ch if c['team']!=us and c['alive'][j] and c['x'][j] is not None and cheb(P(c,j),P(ch[t0],j))<=rad)
            j4=max(r0-5,0)
            if ch[t0]['x'][j4] is not None:
                s['m']+=1; s['nd4']+=nd(j4); s['nw6_4']+=n_within(j4,6); s['nw8_4']+=n_within(j4,8)
                # target's movement in the 4 rounds before first hit: toward or away from enemy centroid
                ex_=[P(c,j4) for c in theirs if c['x'][j4] is not None]
                if ex_:
                    cx=sum(p[0] for p in ex_)/len(ex_); cy=sum(p[1] for p in ex_)/len(ex_)
                    d_before=max(abs(ch[t0]['x'][j4]-cx),abs(ch[t0]['y'][j4]-cy)); d_after=max(abs(c0[0]-cx),abs(c0[1]-cy))
                    s['toward']+= d_after<d_before-0.5; s['away']+= d_after>d_before+0.5; s['still']+= P(ch[t0],j4)==c0
            # after first hit: did target hit back in first 2 rounds; was it stunned in first 2 rounds
            s['hitback']+= any(t0 in own_hits[rr] for rr in (r0,r0+1,r0+2))
            s['stun2']+= any(t0 in stuns[rr] for rr in (r0,r0+1))
            s['hp']+=ch[t0]['hp'][i]/ch[t0]['maxHp'][i]
    for k in sorted(S):
        s=S[k]; n=s['n']; m=max(1,s['m'])
        print(k,'n %d | 4 rounds before: nearest enemy %.1f, enemies within 6: %.2f, within 8: %.2f | target moved toward pack %.2f away %.2f stood still %.2f | hit back within 2 rounds %.2f | stunned within 1 round %.2f | hp %.2f'%(n,s['nd4']/m,s['nw6_4']/m,s['nw8_4']/m,s['toward']/m,s['away']/m,s['still']/m,s['hitback']/n,s['stun2']/n,s['hp']/n))
run('deaths.pkl','live'); run('deaths_local.pkl','local')
