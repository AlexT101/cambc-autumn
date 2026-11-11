# branch.py TAG US: the first target's decisions (D lines) in the rounds before enemy-started outnumbering engagements.
import sys,json,gzip,collections,os
P0='/home/ubuntu/tmp-offload/packgive'
tag,usname=sys.argv[1:3]; oppf=sys.argv[3] if len(sys.argv)>3 else ''
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
DL={}
for l in gzip.open('%s/dlines-%s.jsonl.gz'%(P0,tag),'rt'):
    r=json.loads(l); d=collections.defaultdict(dict); z=collections.defaultdict(dict)
    for x in r['lines']:
        f=x.split()
        if f[0]=='D': d[int(f[1])][int(f[2])]=f[3]
        elif f[0] in('PGZ','PGP'): z[int(f[1])][int(f[2])]=f[0][2]+(f[3] if len(f)>3 else '')
    DL[(r['batch'],r['file'])]=(d,z)
idx=json.load(open('%s/ext-%s/index.json'%(P0,tag)))['games']
C=collections.Counter(); tw=collections.Counter(); pre=collections.Counter(); n=0; fired=collections.Counter(); tot=collections.Counter(); games=0
for g in idx:
    if usname not in g['teams'] or (oppf and oppf not in g['teams'][1-g['teams'].index(usname)]): continue
    us=g['teams'].index(usname); key=tuple(g['source'].split('/')[-2:])
    if key not in DL: continue
    games+=1
    D,Z=DL[key]
    for r in Z:
        for h,v in Z[r].items():
            if r<=250: tot[v]+=1
    d0='%s/ext-%s/%s'%(P0,tag,g['dir'])
    meta=json.load(open(d0+'/meta.json')); R=json.load(gzip.open(d0+'/rounds.json.gz')); ch=R['champions']
    team={c['id']:c['team'] for c in meta['champions']}
    hits=[]
    for l in gzip.open(d0+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>310: break
        if e['k'] in('attack','cast'):
            for t,dm in e.get('dmg',[]): hits.append((e['r'],e['a'],t,dm))
    E=[];cur=None
    for h in hits:
        if cur and h[0]-cur['r1']<=6: cur['r1']=h[0]
        elif h[0]>250: break
        else: cur=dict(r0=h[0],r1=h[0],h=h); E.append(cur)
    Pp=lambda c,i:(c['x'][i],c['y'][i])
    for en in E:
        r0=en['r0']; i=max(r0-2,0); a0,t0=en['h'][1],en['h'][2]
        if team[a0]==us: continue
        T=ch[t0]; c0=Pp(T,i)
        if c0[0] is None: continue
        mine=[c for c in ch if c['team']==us and c['alive'][i] and cheb(Pp(c,i),c0)<=8]
        theirs=[c for c in ch if c['team']!=us and c['alive'][i] and cheb(Pp(c,i),c0)<=8]
        if len(theirs)<=len(mine): continue
        n+=1; any_f=''
        for k in range(1,5):   # round r0-k, moving from index r0-k-2 to r0-k-1
            r=r0-k; j=r-1
            if j<1 or not T['alive'][j] or not T['alive'][j-1]: break
            dec=D.get(r,{}).get(t0,'?'); C[(k,dec)]+=1
            ex=[Pp(c,j-1) for c in theirs if c['alive'][j-1]]
            if ex:
                cx=sum(q[0] for q in ex)/len(ex); cy=sum(q[1] for q in ex)/len(ex)
                p,pp=Pp(T,j),Pp(T,j-1)
                d1=max(abs(p[0]-cx),abs(p[1]-cy)); d0_=max(abs(pp[0]-cx),abs(pp[1]-cy))
                if d1<d0_-0.5: tw[(k,dec)]+=1; tw[(k,'*')]+=1
            zz=Z.get(r,{}).get(t0)
            if zz: fired[(k,zz)]+=1; any_f=any_f or zz
        pre[any_f or '-']+=1
print(tag,oppf,'games',games,'they-did-they-had',n)
for k in range(1,5):
    print(' round r0-%d decisions:'%k,' '.join('%s %d'%(d,c) for (kk,d),c in sorted(C.items(),key=lambda x:-x[1]) if kk==k),'| stepped toward: %d ='%tw[(k,'*')],' '.join('%s %d'%(d,c) for (kk,d),c in sorted(tw.items(),key=lambda x:-x[1]) if kk==k and d!='*'))
print(' rule fired on the target in the 4 rounds before (Z0 zone beyond the old radius, Z1 inside it, P home pursuit):',dict(pre),'| by round',dict(fired))
print(' rule firings per game, rounds<=250:',{k:round(v/games,2) for k,v in tot.items()})
