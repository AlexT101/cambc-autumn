import sys,json,gzip,pickle,collections
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
WE=True
def run(pk,tag,maxr=250,gap=6):
    G=pickle.load(open(pk,'rb')); seen=set(); S=collections.defaultdict(collections.Counter)
    for g in G:
        if g['match'] in seen: continue
        seen.add(g['match']); d0=g['dir']; us=g['us']
        meta=json.load(open(d0+'/meta.json')); R=json.load(gzip.open(d0+'/rounds.json.gz'))
        ch=R['champions']; team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:c['name'] for c in meta['champions']}
        hits=[]; deaths=[]; camph=collections.defaultdict(set); stuns=collections.defaultdict(list)
        for l in gzip.open(d0+'/events.jsonl.gz','rt'):
            e=json.loads(l)
            if e['r']>maxr+30: break
            if e['k'] in('attack','cast'):
                for t,dm in e.get('dmg',[]): hits.append((e['r'],e['a'],t,dm,e['k'],e.get('ab')))
                if 'cdmg' in e or 'camp' in e: camph[e['r']].add(e['a'])
                for t in e.get('stun',[]) or []: stuns[e['r']].append((e['a'],t))
            if e['k']=='death' and 'camp' not in e and e.get('by') is not None: deaths.append((e['r'],e['v']))
        E=[]; cur=None
        for h in hits:
            if h[0]>maxr and (not cur or h[0]-cur['r1']>gap): break
            if cur and h[0]-cur['r1']<=gap: cur['hits'].append(h); cur['r1']=h[0]
            else: cur=dict(r0=h[0],r1=h[0],hits=[h]); E.append(cur)
        for en in E:
            r0,r1=en['r0'],en['r1']; i=max(r0-2,0)
            a0,t0=en['hits'][0][1],en['hits'][0][2]
            if (team[a0]==us)!=WE: continue
            c0=(ch[t0]['x'][i],ch[t0]['y'][i])
            if c0[0] is None: continue
            mine=[c for c in ch if c['team']==us and c['alive'][i] and cheb((c['x'][i],c['y'][i]),c0)<=8]
            theirs=[c for c in ch if c['team']!=us and c['alive'][i] and cheb((c['x'][i],c['y'][i]),c0)<=8]
            if (len(mine)<=len(theirs) if WE else len(theirs)<=len(mine)): continue
            k=[0,0]
            for r,v in deaths:
                if r0<=r<=r1+1 and typ[v]!='Issac': k[0 if team[v]!=us else 1]+=1
            s=S[(tag,g['opp'])]; s['n']+=1; s['ourk']+=k[0]; s['theirk']+=k[1]
            s['mine']+=len(mine); s['theirs']+=len(theirs); s['dur']+=r1-r0+1
            s['hp_mine']+=sum(c['hp'][i]/c['maxHp'][i] for c in mine)/max(1,len(mine)); s['hp_theirs']+=sum(c['hp'][i]/c['maxHp'][i] for c in theirs)/len(theirs)
            s['hp_tgt']+=ch[t0]['hp'][i]/ch[t0]['maxHp'][i]
            s['tgt_hurt']+= ch[t0]['hp'][i]/ch[t0]['maxHp'][i]<0.6
            s['busy']+= any(t0 in camph[rr] for rr in range(r0-3,r0+1))
            s['first_stun']+= any(t==t0 for rr in range(r0,r0+2) for a,t in stuns[rr])
            s['first_cast']+= en['hits'][0][4]=='cast'
            s['their_attackers']+=len({h[1] for h in en['hits'] if team[h[1]]!=us}); s['our_attackers']+=len({h[1] for h in en['hits'] if team[h[1]]==us})
            s['dmg_them']+=sum(h[3] for h in en['hits'] if team[h[1]]!=us); s['dmg_us']+=sum(h[3] for h in en['hits'] if team[h[1]]==us)
            s['dmg_on_first']+=sum(h[3] for h in en['hits'] if h[2]==t0)
            s['first_tgt_died']+= any(v==t0 and r0<=r<=r1+1 for r,v in deaths)
            s['round']+=r0
            s['d_spawn']+=cheb(c0,((g_sp:=json.load(open('/dev/null')) if False else 0),0)) if False else 0
            S[(tag,g['opp'],'tgt')][typ[t0]]+=1; S[(tag,g['opp'],'init')][typ[a0]]+=1
    for k in sorted(S,key=str):
        s=S[k]
        if len(k)==3: print(k,dict(s.most_common(8))); continue
        n=s['n']
        print(k,'n %d | kills us %.3f them %.3f | near us %.2f them %.2f | hp us %.2f them %.2f target %.2f (hurt<0.6: %.2f) | target busy on camp %.2f | stun on target within 2 rounds %.2f | first hit is a cast %.2f | attackers them %.2f us %.2f | dmg them %.0f (on first target %.0f) us %.0f | first target died %.2f | dur %.1f | round %.0f'%(n,s['ourk']/n,s['theirk']/n,s['mine']/n,s['theirs']/n,s['hp_mine']/n,s['hp_theirs']/n,s['hp_tgt']/n,s['tgt_hurt']/n,s['busy']/n,s['first_stun']/n,s['first_cast']/n,s['their_attackers']/n,s['our_attackers']/n,s['dmg_them']/n,s['dmg_on_first']/n,s['dmg_us']/n,s['first_tgt_died']/n,s['dur']/n,s['round']/n))
run('deaths.pkl','live'); run('deaths_local.pkl','local')
