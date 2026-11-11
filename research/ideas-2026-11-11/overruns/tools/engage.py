import sys,json,gzip,pickle,collections
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def engagements(g,maxr=300,gap=6):
    d0=g['dir']; us=g['us']
    meta=json.load(open(d0+'/meta.json')); R=json.load(gzip.open(d0+'/rounds.json.gz'))
    ch=R['champions']; team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:c['name'] for c in meta['champions']}
    hits=[]; deaths=[]
    for l in gzip.open(d0+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>maxr: break
        if e['k'] in('attack','cast') and e.get('dmg'):
            for t,dm in e['dmg']: hits.append((e['r'],e['a'],t,dm))
        if e['k']=='death' and 'camp' not in e and e.get('by') is not None: deaths.append((e['r'],e['v']))
    E=[]; cur=None
    for h in hits:
        if cur and h[0]-cur['r1']<=gap: cur['hits'].append(h); cur['r1']=h[0]
        else:
            cur=dict(r0=h[0],r1=h[0],hits=[h]); E.append(cur)
    out=[]
    for en in E:
        r0,r1=en['r0'],en['r1']; i=max(r0-2,0)
        part=set()
        for r,a,t,dm in en['hits']: part.add(a); part.add(t)
        # centroid of first-hit pair
        a0,t0=en['hits'][0][1],en['hits'][0][2]
        c0=(ch[t0]['x'][i],ch[t0]['y'][i])
        if c0[0] is None: continue
        near=[0,0];
        for c in ch:
            if c['alive'][i] and c['x'][i] is not None and cheb((c['x'][i],c['y'][i]),c0)<=8: near[0 if c['team']==us else 1]+=1
        dmg=[0,0]
        for r,a,t,dm in en['hits']: dmg[0 if team[a]==us else 1]+=dm
        k=[0,0]
        for r,v in deaths:
            if r0<=r<=r1+1 and typ[v]!='Issac': k[0 if team[v]!=us else 1]+=1   # k[0]=kills by us
        first_us=team[a0]==us
        out.append(dict(r0=r0,r1=r1,near=near,dmg=dmg,kills=k,first_us=first_us,npart=[sum(1 for p in part if team[p]==us),sum(1 for p in part if team[p]!=us)]))
    return out
if __name__=='__main__':
    for pk,tag in(('deaths.pkl','live'),('deaths_local.pkl','local')):
        G=pickle.load(open(pk,'rb')); seen=set(); S=collections.defaultdict(collections.Counter)
        for g in G:
            if g['match'] in seen: continue
            seen.add(g['match'])
            for en in engagements(g):
                if sum(en['dmg'])<150: continue
                a,b=min(en['near'][0],5),min(en['near'][1],5)
                rel='even' if a==b else ('we+' if a>b else 'they+')
                for k in ((tag,g['opp'],rel),(tag,g['opp'],'ALL')):
                    s=S[k]; s['n']+=1; s['ourk']+=en['kills'][0]; s['theirk']+=en['kills'][1]; s['ourdmg']+=en['dmg'][0]; s['theirdmg']+=en['dmg'][1]; s['first_us']+=en['first_us']
                    s['we_start_n']+=en['near'][0]; s['they_start_n']+=en['near'][1]
        ng=len(seen)
        for k in sorted(S):
            s=S[k]; print(k,'n/game %.2f kills us %.3f them %.3f per eng | dmg us %.0f them %.0f | we hit first %.2f | near us %.2f them %.2f'%(s['n']/ng*2,s['ourk']/s['n'],s['theirk']/s['n'],s['ourdmg']/s['n'],s['theirdmg']/s['n'],s['first_us']/s['n'],s['we_start_n']/s['n'],s['they_start_n']/s['n']))
