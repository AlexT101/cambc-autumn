# Debug A/B batch + its extraction: for each REF tribute of 100+ gems, whether CAND relayed it, whether CAND bodies
# ran STOP-ENDER at it, how it ended, and the CAND deaths while stopping.
# Usage: enders.py BATCH_DIR EXTRACT_DIR CAND_NAME
import json,gzip,sys,os,re,zipfile,collections
B,A,cand=sys.argv[1],sys.argv[2].rstrip('/')+'/',sys.argv[3]
idx=json.load(open(A+'index.json'))['games']
T=collections.Counter(); ex=[]
for r in idx:
    src=os.path.basename(r['source']); f=os.path.join(B,src)
    if not os.path.exists(f): continue
    ct=r['teams'].index(cand); side='ab'[ct]
    out=zipfile.ZipFile(f).read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    posts=collections.defaultdict(list); stops=collections.defaultdict(list)
    for l in out:
        p=l.split()
        if l.startswith('RELAY-POST'): posts[int(p[3][1:])].append((int(p[1]),int(p[-1])))
        elif l.startswith('STOP-ENDER'): stops[int(p[3][1:])].append((int(p[1]),int(p[2]),p[4],int(p[6]),int(p[-1])))
    d=r['dir']
    m=json.load(open(A+d+'/meta.json')); R=json.load(gzip.open(A+d+'/rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    ch={int(c['id']):c for c in R['champions']}
    # enemy index = order among REF champions by id
    ref_ids=sorted(i for i,c in ch.items() if c['team']!=ct); eidx={x:k for k,x in enumerate(ref_ids)}
    deaths=[(e['r'],e['v']) for e in ev if e['k']=='death' and ch[e['v']]['team']==ct]
    open_={}
    T['games']+=1; T['wins']+=m['result']['winner']==ct
    for e in ev:
        if e['k']=='tribute_start' and ch[e['a']]['team']!=ct: open_[e['a']]=e
        elif e['k'] in ('tribute_end','tribute_cancel') and e['a'] in open_:
            s=open_.pop(e['a']); g=s.get('gems',0)
            if g<100: continue
            k=eidx[s['a']]; r0,r1=s['r'],e['r']
            fin=e['k']=='tribute_end' and e.get('total',0)>=1000
            relayed=any(r0<=t<=r1 for t,_ in posts[k]); win=any(r0<=t<=r1 and c==7 for t,c in posts[k])
            st=[x for x in stops[k] if r0<=x[0]<=r1+1]
            stoppers={x[1] for x in st}
            died=sum(1 for t,_ in deaths if r0<=t<=r1+5)
            key=('final' if fin else 'done' if e['k']=='tribute_end' else 'cancel:'+str(e.get('cause')))
            T['n']+=1; T[key]+=1
            if win:
                T['win_class']+=1; T['win_class '+key]+=1
                T['win_class stopped_by_us' if st else 'win_class no_stop']+=1
                if st: T['win_class stop '+key]+=1; T['win_class stop unseen']+=any(x[2]=='unseen' for x in st); T['win_class stop deaths']+=died
            if fin: ex.append((src,r0,r1,g,relayed,win,len(st),len(stoppers)))
for k in sorted(T): print(k,T[k])
for x in ex[:40]: print(x)
