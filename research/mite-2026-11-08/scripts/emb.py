import json,gzip,collections,random,datetime
G='/home/ubuntu/tmp-offload/gaps/analysis/'
F=['Monster','Power','Durability','Treasure','Jungle','Home','Bruiser','Tribute','Capture','Prospector','Hunter','Skirmish','Greed','Collectors']
name=lambda k: f"{F[k//6]}-{'SFH'[(k%6)//2]}"
ix=json.load(open('mite_index.json'))
ts=lambda o:int(o['mid'].replace('-','')[:12],16)/1000
random.seed(2)
for lab,cond in (('11-05',lambda o:o['src']=='a1105'),('11-06/07',lambda o:o['src']=='cap')):
    S=[o for o in ix if cond(o)]; S=random.sample(S,min(250,len(S)))
    seq=collections.defaultdict(collections.Counter); first=collections.defaultdict(collections.Counter); ng=collections.Counter(); spent=collections.defaultdict(list)
    cons=collections.defaultdict(list)
    for o in S:
        r=json.load(gzip.open(G+o['dir']+'/rounds.json.gz')); m=json.load(open(G+o['dir']+'/meta.json'))
        nm={c['id']:c['name'] for c in m['champions']}
        for c in r['champions']:
            if c['team']!=o['side']: continue
            n=nm[c['id']]; ng[n]+=1; order=[]
            for it in c['items']:
                for k,v in zip(it[0::2],it[1::2]) if it and not isinstance(it[0],list) else [(a,b) for a,b in it]:
                    if k%2==1 and name(k) not in order: order.append(name(k))
            seq[n][tuple(order[:4])]+=1
            if order: first[n][order[0]]+=1
            mc=[x for x in m['champions'] if x['id']==c['id']][0]
            spent[n].append(mc['stats']['spentGold']); cons[n].append(mc['stats']['consumablesBought'])
    print('=====',lab)
    for n in ng:
        print(f"{n:14} games={ng[n]} spent={sum(spent[n])/len(spent[n]):.0f} cons/game={[round(sum(x[i] for x in cons[n])/len(cons[n]),2) for i in range(4)]}")
        print('    first:',first[n].most_common(4)); print('    top4 orders:',seq[n].most_common(3))
