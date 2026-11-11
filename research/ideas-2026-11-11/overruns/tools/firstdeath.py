import sys,json,gzip,pickle,collections
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def analyse(g,maxr=200,only_first=True):
    d0=g['dir']; us=g['us']
    meta=json.load(open(d0+'/meta.json')); R=json.load(gzip.open(d0+'/rounds.json.gz'))
    ch=R['champions']; team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:c['name'] for c in meta['champions']}
    hits=collections.defaultdict(list); camphit=collections.defaultdict(set); stunned=collections.defaultdict(set)
    deaths=[]
    for l in gzip.open(d0+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>maxr: break
        if e['k'] in('attack','cast'):
            for t,dm in e.get('dmg',[]): hits[e['r']].append((e['a'],t,dm))
            for t in e.get('stun',[]) or []:
                if isinstance(t,int): stunned[e['r']].add(t)
            if 'cdmg' in e or 'camp' in e: camphit[e['r']].add(e['a'])
        if e['k']=='death' and 'camp' not in e and e.get('by') is not None and typ[e['v']]!='Issac': deaths.append(e)
    out=[]; done=set()
    for e in deaths:
        v=e['v']; vt=team[v]
        if only_first and vt in done: continue
        done.add(vt)
        r=e['r']
        # the victim's (or its pair's) fight: walk back while champion damage involving victim side near exists with gap<=4
        pair={v}
        if typ[v]=='Cassi': pair|={c['id'] for c in meta['champions'] if c['team']==vt and c['name']=='Issac'}
        r0=r; last=r
        for rr in range(r,max(r-40,0),-1):
            if any((a in pair or t in pair) for a,t,dm in hits[rr]): r0=rr; last=rr
            elif last-rr>4: break
        first=None
        for rr in range(r0,r+1):
            for a,t,dm in hits[rr]:
                if a in pair or t in pair: first=(a,t); break
            if first: break
        vict_init = first is not None and first[0] in pair
        i=max(r0-2,0)
        pos=lambda c,i:(c['x'][i],c['y'][i])
        vp=pos(ch[v],i)
        if vp[0] is None: continue
        na=[c for c in ch if c['team']==vt and c['id'] not in pair and c['alive'][i] and cheb(pos(c,i),vp)<=8]
        ne=[c for c in ch if c['team']!=vt and c['alive'][i] and cheb(pos(c,i),vp)<=8]
        # bystanders: allies near at start that dealt no champion damage in [r0,r]
        dealt=collections.Counter()
        for rr in range(r0,r+1):
            for a,t,dm in hits[rr]: dealt[a]+=dm
        by=[c for c in na if dealt[c['id']]==0]
        bycamp=[c for c in by if any(c['id'] in camphit[rr] for rr in range(r0,r+1))]
        stun_rounds=sum(1 for rr in range(r0,r+1) if any(p in stunned[rr] for p in pair))
        hp0=sum(ch[p]['hp'][i] for p in pair)/sum(ch[p]['maxHp'][i] for p in pair)
        out.append(dict(ours=vt==us,r=r,dur=r-r0,vict_init=vict_init,na=len(na)+len(pair),ne=len(ne),by=len(by),bycamp=len(bycamp),stun=stun_rounds,hp0=hp0,typ=typ[v],
            enemies_engaged=len({a for rr in range(r0,r+1) for a,t,dm in hits[rr] if t in pair})))
    return out
if __name__=='__main__':
    for pk,tag in(('deaths.pkl','live'),('deaths_local.pkl','local')):
        G=pickle.load(open(pk,'rb')); seen=set(); S=collections.defaultdict(collections.Counter)
        for g in G:
            if g['match'] in seen: continue
            seen.add(g['match'])
            for o in analyse(g):
                for k in ((tag,g['opp'],'our' if o['ours'] else 'their'),)+(((tag,'OVERRUN','our' if o['ours'] else 'their'),) if g.get('cls')=='overrun' and not g['win'] else ()):
                    s=S[k]; s['n']+=1; s['init']+=o['vict_init']; s['na']+=o['na']; s['ne']+=o['ne']; s['by']+=o['by']; s['bycamp']+=o['bycamp']; s['stun']+=o['stun']; s['hp0']+=o['hp0']; s['dur']+=o['dur']; s['eng']+=o['enemies_engaged']
                    s['init_out']+= o['vict_init'] and o['ne']>o['na']-0; s['outn']+=o['ne']>o['na']; s['stunned_any']+=o['stun']>0
        for k in sorted(S):
            s=S[k]; n=s['n']
            print(k,'n %d | victim hit first %.2f | own bodies near %.2f enemies near %.2f (outnumbered %.2f) | attackers on victim %.2f | bystander allies %.2f (on camp %.2f) | stunned %.2f (rounds %.2f) | hp at start %.2f | dur %.1f'%(n,s['init']/n,s['na']/n,s['ne']/n,s['outn']/n,s['eng']/n,s['by']/n,s['bycamp']/n,s['stunned_any']/n,s['stun']/n,s['hp0']/n,s['dur']/n))
