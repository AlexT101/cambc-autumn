# Per-engagement rows for both directions (who hit first), from the overruns pickles' decoded games.
# usage: eng.py PKL OUT.pkl [maxr]
import sys, json, gzip, pickle, collections
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def rows_for(g,maxr=250,gap=6):
    d0=g['dir']; us=g['us']
    meta=json.load(open(d0+'/meta.json')); R=json.load(gzip.open(d0+'/rounds.json.gz'))
    ch=R['champions']; team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:c['name'] for c in meta['champions']}
    n=len(R['round'])
    hits=[]; deaths=[]; act=collections.defaultdict(lambda:collections.defaultdict(str)); stuns=collections.defaultdict(list)
    heals=collections.defaultdict(float); casts=collections.defaultdict(list)
    for l in gzip.open(d0+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>maxr+40: break
        if e['k'] in('attack','cast'):
            for t,dm in e.get('dmg',[]): hits.append((e['r'],e['a'],t,dm,e['k'],e.get('ab'),tuple(e['f'])))
            act[e['r']][e['a']]+=('C' if ('cdmg' in e or 'camp' in e) else '')+('H' if e.get('dmg') else '')+('D' if e.get('ab')=='Dash' else '')
            for t in e.get('stun',[]) or []: stuns[e['r']].append((e['a'],t))
            for t,h in e.get('heal',[]) or []: heals[(e['r'],t)]+=h
        if e['k']=='death' and 'camp' not in e and e.get('by') is not None: deaths.append((e['r'],e['v']))
    E=[]; cur=None
    for h in hits:
        if h[0]>maxr and (not cur or h[0]-cur['r1']>gap): break
        if cur and h[0]-cur['r1']<=gap: cur['hits'].append(h); cur['r1']=h[0]
        else: cur=dict(r0=h[0],r1=h[0],hits=[h]); E.append(cur)
    P=lambda c,j:(c['x'][j],c['y'][j])
    sp=[None,None]
    for t in (0,1):
        xs=[P(c,0) for c in ch if c['team']==t]; sp[t]=(sum(p[0] for p in xs)/len(xs),sum(p[1] for p in xs)/len(xs))
    out=[]
    for en in E:
        r0,r1=en['r0'],en['r1']; i=max(r0-2,0)
        a0,t0=en['hits'][0][1],en['hits'][0][2]
        A=team[a0]; T=ch[t0]; c0=P(T,i)
        if c0[0] is None or not T['alive'][i]: continue
        att=[c for c in ch if c['team']==A and c['alive'][i] and cheb(P(c,i),c0)<=8]
        dfn=[c for c in ch if c['team']!=A and c['alive'][i] and cheb(P(c,i),c0)<=8]
        k=[0,0]
        for r,v in deaths:
            if r0<=r<=r1+1 and typ[v]!='Issac': k[0 if team[v]!=A else 1]+=1
        died=[r for r,v in deaths if v==t0 and r0<=r<=r1+1]
        row=dict(map=g['map'],side=g['side'],opp=g['opp'],win=g['win'],match=g['match'],dir=d0,us=us,by_us=(A==us),r0=r0,r1=r1,
                 nA=len(att),nD=len(dfn),tgt=typ[t0],init=typ[a0],first_kind=en['hits'][0][4],first_ab=en['hits'][0][5],
                 first_dist=cheb(en['hits'][0][6],c0),died=bool(died),die_off=(died[0]-r0 if died else None),
                 kA=k[0],kD=k[1],hp_t=T['hp'][i]/T['maxHp'][i],maxhp_t=T['maxHp'][i],
                 home_D=cheb(c0,sp[1-A])<=cheb(c0,sp[A]),
                 t_act=[act[r0-1-q][t0] for q in range(3)],t_chan=T['chan'][i],
                 nitems_t=len(T['items'][i]))
        # attackers on T0 and damage by round offset
        aset=[set() for _ in range(6)]; dmg=[0.0]*6
        for r,a,t,dm,kd,ab,f in en['hits']:
            o=r-r0
            if t==t0 and team[a]==A and o<6: aset[o].add(a); dmg[o]+=dm
        row['att_by_off']=[len(s) for s in aset]; row['dmg_by_off']=dmg
        cum=set(); row['att_cum']=[]
        for s in aset: cum|=s; row['att_cum'].append(len(cum))
        row['att_total']=len({h[1] for h in en['hits'] if team[h[1]]==A})
        row['att_on_t0']=len({h[1] for h in en['hits'] if team[h[1]]==A and h[2]==t0})
        row['dmg_on_t0']=sum(h[3] for h in en['hits'] if h[2]==t0)
        row['dmg_A']=sum(h[3] for h in en['hits'] if team[h[1]]==A); row['dmg_D']=sum(h[3] for h in en['hits'] if team[h[1]]!=A)
        row['def_hitters']=len({h[1] for h in en['hits'] if team[h[1]]!=A})
        row['stun_t0']=[sum(1 for a,t in stuns[r0+o] if t==t0) for o in range(4)]
        row['heal_t0']=sum(heals[(r0+o,t0)] for o in range(6))
        # per attacker-side body within 8: distances to T0 over time, what it did
        B=[]
        for c in att:
            b=dict(typ=typ[c['id']],hp=c['hp'][i]/c['maxHp'][i],cd0=c['cd0'][i],cd1=c['cd1'][i],nitems=len(c['items'][i]),str=c['str'][i],
                   d=[cheb(P(c,max(i-q,0)),P(T,max(i-q,0))) if c['alive'][max(i-q,0)] and T['alive'][max(i-q,0)] else None for q in (0,1,2,3,5,8)],
                   dafter=[cheb(P(c,min(i+q,n-1)),P(T,min(i+q,n-1))) if c['alive'][min(i+q,n-1)] and T['alive'][min(i+q,n-1)] else None for q in (1,2,3,4)],
                   pre=[act[r0-1-q][c['id']] for q in range(4)],post=[act[r0+q][c['id']] for q in range(5)],
                   seen_by_t=c['id'] in T['sees'][i],
                   first_hit_off=min([h[0]-r0 for h in en['hits'] if h[1]==c['id']],default=None),
                   first_hit_t0=min([h[0]-r0 for h in en['hits'] if h[1]==c['id'] and h[2]==t0],default=None),
                   dmg=sum(h[3] for h in en['hits'] if h[1]==c['id']))
            B.append(b)
        row['B']=B
        # late joiners: attackers not within 8 at i
        ids={c['id'] for c in att}
        row['late_join']=len({h[1] for h in en['hits'] if team[h[1]]==A and h[1] not in ids})
        # defenders
        Dd=[]
        for c in dfn:
            Dd.append(dict(typ=typ[c['id']],hp=c['hp'][i]/c['maxHp'][i],d=cheb(P(c,i),c0),
                           pre=[act[r0-1-q][c['id']] for q in range(3)],post=[act[r0+q][c['id']] for q in range(5)],
                           dmg=sum(h[3] for h in en['hits'] if h[1]==c['id']),
                           dafter=[cheb(P(c,min(i+q,n-1)),P(T,min(i+q,n-1))) if c['alive'][min(i+q,n-1)] and T['alive'][min(i+q,n-1)] else None for q in (1,2,3,4)]))
        row['Dd']=Dd
        # target flight: distance of T0 from its position at i after q rounds
        row['t_move']=[cheb(P(T,min(i+q,n-1)),c0) if T['alive'][min(i+q,n-1)] else None for q in (1,2,3,4)]
        row['t_hp']=[T['hp'][min(i+q,n-1)]/T['maxHp'][i] if T['alive'][min(i+q,n-1)] else 0 for q in (1,2,3,4,5,6)]
        out.append(row)
    return out
if __name__=='__main__':
    G=pickle.load(open(sys.argv[1],'rb')); seen=set(); out=[]
    maxr=int(sys.argv[3]) if len(sys.argv)>3 else 250
    for g in G:
        if g['match'] in seen: continue
        seen.add(g['match']); out+=rows_for(g,maxr)
    pickle.dump(dict(rows=out,ngames=collections.Counter(g['opp'] for g in G if g['match'] in seen and not seen.discard(g['match']))),open(sys.argv[2],'wb'))
    print(len(out))
