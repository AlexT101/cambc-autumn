# Death audit: every CAND body death (and every kill CAND makes) classed by the decision branch on the turn before
# the fatal exchange began (commit) and the branches of the last 10 turns, with the bot's own threat read (DX).
# Usage: deaths.py BATCH_DIR EXTRACT_DIR CAND_NAME [--dump N]
import json,gzip,sys,os,zipfile,collections
B,A,cand=sys.argv[1],sys.argv[2].rstrip('/')+'/',sys.argv[3]
dump=int(sys.argv[sys.argv.index('--dump')+1]) if '--dump' in sys.argv else 0
idx=json.load(open(A+'index.json'))['games']
GAP=3
cls=collections.defaultdict(lambda:[0,0,0,0,0]) # lives, gems, visible-at-commit, lethal-read-at-commit, bag>=50
last=collections.defaultdict(lambda:[0,0]); kills=collections.defaultdict(lambda:[0,0]); kcommit=collections.defaultdict(lambda:[0,0])
types=collections.defaultdict(lambda:[0,0]); samples=collections.defaultdict(list)
games=0; mapchk=collections.Counter()
for r in idx:
    src=os.path.basename(r['source']); f=os.path.join(B,src)
    if not os.path.exists(f) or cand not in r['teams']: continue
    ct=r['teams'].index(cand); side='ab'[ct]
    try: out=zipfile.ZipFile(f).read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    except KeyError: continue
    dec={}; dx={}
    for l in out:
        p=l.split()
        if len(p)>=4 and p[0]=='D' and p[1].lstrip('-').isdigit(): dec[(int(p[1]),int(p[2]))]=p[3]
        elif p and p[0]=='DX' and len(p)==9:
            dx[(int(p[1]),int(p[2]))]=(float(p[4][2:]),int(p[5][1:]),*map(float,p[6][1:].split('/')),int(p[7][1:]),int(p[8][1:]))
    d=r['dir']; games+=1
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); ri={x:i for i,x in enumerate(R['round'])}
    ch={int(c['id']):c for c in R['champions']}
    m=json.load(open(A+d+'/meta.json')); name={c['id']:c['name'] for c in m['champions']}
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    # champion damage rounds per victim
    hit=collections.defaultdict(list)
    for e in ev:
        if e['k'] in ('attack','cast') and 'dmg' in e:
            for v,a in e['dmg']:
                if v in ch and a>0 and ch[v]['team']!=ch[e['a']]['team']: hit[v].append(e['r'])
        elif e['k']=='camp_attack' and e.get('tgt') in ch: hit[e['tgt']].append(e['r'])
    # handle check: handle == engine id?
    for (rd,h),v in list(dx.items())[:20]:
        i=ri.get(rd)
        if i is not None and h in ch: mapchk['hp-match' if abs(ch[h]['hp'][i]-v[0])<1.5 else 'hp-mismatch']+=1
    def seq(h,r0,r1): return ''.join(dec.get((x,h),'.') for x in range(r0,r1+1))
    for e in ev:
        if e['k']!='death' or e.get('linked') is not None: continue
        v=e['v']; rd=e['r']; vt=ch[v]['team']
        gems=e.get('gems',0)+sum(x.get('gems',0) for x in ev if x['k']=='death' and x.get('linked')==v and x['r']==rd)
        hs=sorted(set(x for x in hit[v] if x<=rd))
        r0=rd
        for x in reversed(hs):
            if r0-x<=GAP: r0=x
            else: break
        if vt==ct:
            commit=dec.get((v,),None)
            cr=r0-1; c=dec.get((cr,v),'?')
            lastd=next((dec[(x,v)] for x in range(rd,rd-6,-1) if (x,v) in dec),'?')
            camp='camp' if e.get('camp') is not None else 'champ'
            k=(camp,c)
            info=dx.get((cr,v))
            vis=info is not None and info[5]>0; lethal=info is not None and info[3]>=info[0]
            L=cls[k]; L[0]+=1; L[1]+=gems; L[2]+=vis; L[3]+=lethal; L[4]+=gems>=50
            last[(camp,lastd)][0]+=1; last[(camp,lastd)][1]+=gems
            types[(name[v],c)][0]+=1; types[(name[v],c)][1]+=gems
            samples[k].append((src,rd,name[v],gems,rd-r0,seq(v,rd-10,rd),info))
        elif e.get('by') in ch and ch[e['by']]['team']==ct:
            kk=e['by']; kd=next((dec[(x,kk)] for x in range(rd,rd-3,-1) if (x,kk) in dec),'?')
            kills[kd][0]+=1; kills[kd][1]+=gems
            kc=dec.get((r0-1,kk),'?'); kcommit[kc][0]+=1; kcommit[kc][1]+=gems
print('games',games,'handle check',dict(mapchk))
tot=sum(v[0] for v in cls.values()); tg=sum(v[1] for v in cls.values())
print(f'our deaths {tot} ({tot/games:.2f}/game) gems {tg} ({tg/games:.1f}/game)')
print('by (killer kind, commit branch): lives/game gems/game  %seen-enemy-at-commit %lethal-read  %bag50+')
for k,v in sorted(cls.items(),key=lambda kv:-kv[1][1]):
    print(f'  {k[0]:5} {k[1]}  {v[0]/games:.3f}  {v[1]/games:6.1f}  vis {100*v[2]/v[0]:3.0f}%  lethal {100*v[3]/v[0]:3.0f}%  bag50 {100*v[4]/v[0]:3.0f}%  n={v[0]}')
print('by last branch:'); [print(f'  {k} {v[0]/games:.3f} {v[1]/games:.1f}') for k,v in sorted(last.items(),key=lambda kv:-kv[1][1])[:15]]
print('by champion, commit (top 25 by gems):'); [print(f'  {k} {v[0]/games:.3f} {v[1]/games:.1f}') for k,v in sorted(types.items(),key=lambda kv:-kv[1][1])[:25]]
k2=sum(v[0] for v in kills.values()); g2=sum(v[1] for v in kills.values())
print(f'our kills {k2} ({k2/games:.2f}/game) gems {g2/games:.1f}/game; killer branch at kill:')
[print(f'  {k} {v[0]/games:.3f} {v[1]/games:.1f}') for k,v in sorted(kills.items(),key=lambda kv:-kv[1][0])]
print('killer branch at victim engagement start-1:'); [print(f'  {k} {v[0]/games:.3f} {v[1]/games:.1f}') for k,v in sorted(kcommit.items(),key=lambda kv:-kv[1][0])]
if dump:
    for k,v in sorted(cls.items(),key=lambda kv:-kv[1][1])[:6]:
        print('==',k)
        for s in sorted(v and samples[k],key=lambda s:-s[3])[:dump]: print('  ',s)
