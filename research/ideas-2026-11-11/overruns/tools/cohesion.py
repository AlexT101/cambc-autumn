import sys,json,gzip,pickle,collections
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def biggest(ps,lim=5):
    n=len(ps); seen=[0]*n; best=0
    for s in range(n):
        if seen[s]: continue
        st=[s]; seen[s]=1; c=0
        while st:
            u=st.pop(); c+=1
            for v in range(n):
                if not seen[v] and cheb(ps[u],ps[v])<=lim: seen[v]=1; st.append(v)
        best=max(best,c)
    return best
def run(pk,tag):
    G=pickle.load(open(pk,'rb')); seen=set()
    S=collections.defaultdict(lambda:collections.Counter())
    for g in G:
        if g['match'] in seen: continue
        seen.add(g['match'])
        R=json.load(gzip.open(g['dir']+'/rounds.json.gz')); ch=R['champions']; n=len(R['round'])
        npick=len(g['our_picks'])
        for lo,hi in ((30,100),(100,250),(250,600)):
            for i in range(lo,min(hi,n),5):
                for t,lab in ((g['us'],'us'),(1-g['us'],g['opp'])):
                    ps=[(c['x'][i],c['y'][i]) for c in ch if c['team']==t and c['alive'][i]]
                    if len(ps)<2: continue
                    k=(tag,lab,lo,npick)
                    S[k]['n']+=1; S[k]['big']+=biggest(ps); S[k]['alive']+=len(ps)
                    # contact: any enemy within 8 of any of ours
                    es=[(c['x'][i],c['y'][i]) for c in ch if c['team']!=t and c['alive'][i]]
                    for p in ps:
                        ne=sum(1 for e in es if cheb(p,e)<=6); na=sum(1 for q in ps if cheb(p,q)<=6)  # incl self
                        if ne>0:
                            S[k]['contact']+=1; S[k]['c_allies']+=na; S[k]['c_enemies']+=ne; S[k]['c_outnum']+= ne>na; S[k]['c_adv']+= na>ne
    for k in sorted(S):
        s=S[k]; 
        print(k,'bodies_alive %.2f biggest_cluster %.2f | in contact: per-sample %.2f allies %.2f enemies %.2f outnumbered %.2f advantage %.2f'%(s['alive']/s['n'],s['big']/s['n'],s['contact']/s['n'],s['c_allies']/max(1,s['contact']),s['c_enemies']/max(1,s['contact']),s['c_outnum']/max(1,s['contact']),s['c_adv']/max(1,s['contact'])))
run('deaths.pkl','live'); run('deaths_local.pkl','local')
