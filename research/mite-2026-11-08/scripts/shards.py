import json,gzip,collections,datetime
G='/home/ubuntu/tmp-offload/gaps/analysis/'
F=['Monster','Power','Durability','Treasure','Jungle','Home','Bruiser','Tribute','Capture','Prospector','Hunter','Skirmish','Greed','Collectors']
ix=json.load(open('mite_index.json'))
H=lambda o: datetime.datetime.utcfromtimestamp(int(o['mid'].replace('-','')[:12],16)/1000).strftime('%m-%d %H')
S=[o for o in ix if '11-07 05'<=H(o)<='11-07 14']
seqs=collections.defaultdict(list); par=collections.Counter(); firstfam=collections.defaultdict(collections.Counter)
def items(it): 
    d={}
    for k,v in (zip(it[0::2],it[1::2]) if it and not isinstance(it[0],list) else it): d[k]=v
    return d
for o in S:
    r=json.load(gzip.open(G+o['dir']+'/rounds.json.gz')); m=json.load(open(G+o['dir']+'/meta.json'))
    nm={c['id']:c['name'] for c in m['champions']}
    for c in r['champions']:
        if c['team']!=o['side']: continue
        prev={}; buys=[]
        for t,it in enumerate(c['items']):
            cur=items(it)
            # shards bought: count increases of shard index, plus 5 per new emblem formed (5 shards consumed)
            for k in set(cur)|set(prev):
                dv=cur.get(k,0)-prev.get(k,0)
                if k%2==0 and dv>0: buys+= [(r['round'][t],F[k//6]+'-'+'SFH'[(k%6)//2])]*dv
                if k%2==1 and dv>0: buys+= [(r['round'][t],F[k//6]+'-'+'SFH'[(k%6)//2])]*(5*dv)
            prev=cur
        # a 5th shard turning into an emblem shows as shard count drop + emblem: approximate
        fams=[b[1] for b in buys]
        seqs[nm[c['id']]].append(fams)
        if fams: firstfam[nm[c['id']]][fams[0]]+=1
        # parallel: number of distinct families among the first 10 shards
        if len(fams)>=10: par[(nm[c['id']],len(set(fams[:10])))]+=1
for n in seqs:
    print(n, 'first shard:',firstfam[n].most_common(4))
    print('    distinct families in first 10 shards:',sorted((k[1],v) for k,v in par.items() if k[0]==n))
    ex=[s[:14] for s in seqs[n] if len(s)>=14][:2]
    for e in ex: print('    e.g.',' '.join(x.split('-')[0][:4]+x[-1] for x in e))
