# Tribute attempts by bag size: completed / cancelled (lock, stun, other) / died within 40 rounds after a cancel.
# usage: tribsize.py ANA_DIR [GAMES_JSON]  (no games json: local batch, side = team named in argv[3])
import json,gzip,os,sys,collections,numpy as np
ana=sys.argv[1]; games=json.load(open(sys.argv[2])) if len(sys.argv)>2 and sys.argv[2]!='-' else None
ourname=sys.argv[3] if len(sys.argv)>3 else None
idx=json.load(open(ana+'/index.json'))['games']; done=set()
B=[0,20,40,80,150,250,400,10000]
st=collections.defaultdict(lambda:collections.Counter())
for g in idx:
    if g['dir'] in done: continue
    if games is not None:
        m=os.path.basename(g['source']).split('.')[0]; gm=games.get(m)
        if not gm: continue
        us=0 if gm['side']=='a' else 1
    else:
        if ourname not in g['source']: continue
        us=0 if g['source'].endswith('-12.repl26a') else 1  # local batch: bot 1 (CAND) is team A in -12 files
    done.add(g['dir']); d=ana+'/'+g['dir']
    try: meta=json.load(open(d+'/meta.json'))
    except: continue
    team={c['id']:c['team'] for c in meta['champions']}
    open_={}; deaths=collections.defaultdict(list); res=[]
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    for e in ev:
        if e['k']=='death': deaths[e['v']].append(e['r'])
    for e in ev:
        k=e['k']
        if k=='tribute_start': open_[e['a']]=(e['r'],e['gems'])
        elif k=='tribute_end' and e['a'] in open_:
            r0,gm_=open_.pop(e['a']); res.append((team[e['a']]==us,gm_,'done',e['a'],e['r']))
        elif k=='tribute_cancel' and e['a'] in open_:
            r0,gm_=open_.pop(e['a']); res.append((team[e['a']]==us,gm_,e.get('cause'),e['a'],e['r']))
    for ours,gm_,how,a,r in res:
        b=next(i for i in range(len(B)-1) if gm_<B[i+1])
        died=any(r<=x<=r+40 for x in deaths[a]) if how!='done' else False
        key=('ours' if ours else 'opp',B[b])
        st[key][how if how in ('done','lock','stun','manual') else 'other']+=1
        if died: st[key]['died40']+=1
print(f"{'side':5s} {'bag':>5s} {'n':>6s} {'done%':>6s} {'lock%':>6s} {'stun%':>6s} {'manual%':>7s} {'other%':>6s} {'died40/cancel':>13s}")
for key in sorted(st):
    c=st[key]; n=sum(v for k,v in c.items() if k!='died40'); ca=n-c['done']
    print(f"{key[0]:5s} {key[1]:5d} {n:6d} {100*c['done']/n:6.1f} {100*c['lock']/n:6.1f} {100*c['stun']/n:6.1f} {100*c['manual']/n:7.1f} {100*c['other']/n:6.1f} {c['died40']/max(ca,1):13.2f}")
