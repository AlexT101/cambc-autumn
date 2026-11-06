import json,gzip,sys,collections,statistics
ana=sys.argv[1]; names=json.load(open(sys.argv[2]))
ix=json.load(open(f'{ana}/index.json'))['games']; seen=set()
pres=collections.defaultdict(list); campshare=[]
for x in ix:
    d=x['dir']
    if d in seen: continue
    seen.add(d)
    m=json.load(open(f'{ana}/{d}/meta.json')); mp=json.load(open(f"{ana}/maps/{m['map']['hash']}.json"))
    al=mp['altars']
    if not al: continue
    if max(max(abs(a[0]-b[0]),abs(a[1]-b[1])) for a in al for b in al)>10: continue  # one zone
    cx=sum(a[0] for a in al)/len(al); cy=sum(a[1] for a in al)/len(al)
    # share of group gems whose capture tiles lie within 10 of the altar zone
    tot=near=0
    for g in mp['groups']:
        tot+=g['gems']; 
        if any(max(abs(t[0]-cx),abs(t[1]-cy))<=10 for t in g['tiles']): near+=g['gems']
    if tot: campshare.append(near/tot)
    R=json.load(gzip.open(f'{ana}/{d}/rounds.json.gz')); N=len(R['round'])
    lo=min(N,600)
    sc=[]
    for t in (0,1):
        n=a=0
        for c in R['champions']:
            if c['team']!=t: continue
            for i in range(30,lo):
                if c['alive'][i] and c['x'][i] is not None:
                    a+=1; n+=max(abs(c['x'][i]-cx),abs(c['y'][i]-cy))<=8
        sc.append(n/max(a,1))
    w=m['result']['winner']
    who=names.get(d,['?','?'])
    # paired: did the side with more presence win?
    more=0 if sc[0]>sc[1] else 1
    pres['all'].append(more==w)
    for t in (0,1):
        k=who[t] if who[t] in ('astraeus','ocean','Pantheon') else 'others'
        pres[(k,'won' if w==t else 'lost')].append(sc[t])
print('one-zone games',len(pres['all']),'side with more altar presence (r30-600) won %',round(100*sum(pres['all'])/len(pres['all']),1))
for k,v in sorted((k,v) for k,v in pres.items() if k!='all'): print(k,len(v),'mean presence',round(statistics.mean(v),3))
print('share of map gems at camps within 10 of the altar: median',round(statistics.median(campshare),2),'p25',round(sorted(campshare)[len(campshare)//4],2),'p75',round(sorted(campshare)[3*len(campshare)//4],2))
