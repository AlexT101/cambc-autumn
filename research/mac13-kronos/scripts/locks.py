import json,gzip,glob,collections
A=collections.defaultdict(list)
for f in glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json'):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: continue
    d=f.rsplit('/',1)[0]
    mp=json.load(open('/home/ubuntu/wt/mac13-kronos/replays/.analysis/maps/'+m['mapFile'].split('/')[-1]))
    na=len(mp['altars']); key=min(na,4)
    w=m['result']['winner']
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    T=len(o['locks'])
    # lock-rounds by team: entries [team,x,y,hp]
    lr=[0,0]
    for x in o['locks']:
        for l in x: lr[l[0]]+=1
    A[(key,'lockrounds_winner')].append(lr[w]/T); A[(key,'lockrounds_loser')].append(lr[1-w]/T)
    A[(key,'rounds')].append(T)
    c=m['counts']; A[(key,'lock_place')].append(c.get('lock_place',0)); A[(key,'lock_destroyed')].append(c.get('lock_destroyed',0))
    A[(key,'n')].append(1)
for k in sorted(A): print(k, round(sum(A[k])/len(A[k]),3) if k[1]!='n' else len(A[k]))
