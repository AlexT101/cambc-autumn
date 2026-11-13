# Stun/lock stops of winning enemy channels followed by our death: the events of the channeller and the dead body
# from the stop to the death, with the dead body's D decisions. Usage: story.py EXTRACT_DIR CAND N [cause]
import json,gzip,sys,zipfile,os
A=sys.argv[1].rstrip('/')+'/'; cand=sys.argv[2]; N=int(sys.argv[3]); want=sys.argv[4] if len(sys.argv)>4 else 'stun'
idx=json.load(open(A+'index.json'))['games']; shown=0
for r in idx:
    if shown>=N: break
    if cand not in r['teams']: continue
    ct=r['teams'].index(cand); d=r['dir']; m=json.load(open(A+d+'/meta.json'))
    team={c['id']:c['team'] for c in m['champions']}; name={c['id']:c['name'] for c in m['champions']}
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    total=[0,0]; open_={}; stops=[]
    for e in ev:
        if e['k']=='tribute_end': total[team[e['a']]]=e.get('total',0); open_.pop(e['a'],None)
        elif e['k']=='tribute_start' and team[e['a']]!=ct and total[team[e['a']]]+e['gems']>=1000: open_[e['a']]=e
        elif e['k']=='tribute_cancel' and e['a'] in open_ and e.get('cause')==want: stops.append((e['r'],e['a'],open_.pop(e['a'])))
    if not stops: continue
    dec={}
    try:
        out=zipfile.ZipFile(r['source']).read(f"team-{'ab'[ct]}.stdout").decode(errors='replace').splitlines()
        for l in out:
            p=l.split()
            if len(p)>=4 and p[0]=='D' and p[1].isdigit(): dec[(int(p[1]),int(p[2]))]=p[3]
    except Exception: pass
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); ri={x:i for i,x in enumerate(R['round'])}; ch={int(c['id']):c for c in R['champions']}
    for rr,c,st in stops:
        dead=[e for e in ev if e['k']=='death' and team[e['v']]==ct and rr-1<=e['r']<=rr+12 and e.get('linked') is None]
        if not dead or shown>=N: continue
        shown+=1; v=dead[0]['v']
        print(f"== {os.path.basename(r['source'])} stop r{rr} channeller {c}:{name[c]} bag {st['gems']} at {st['at']}; our {v}:{name[v]} dies r{dead[0]['r']} by {dead[0].get('by')} gems {dead[0].get('gems')}")
        for e in ev:
            if rr-3<=e['r']<=dead[0]['r'] and (e.get('a') in (c,v) or e.get('v') in (c,v)) and e['k'] not in ('move',):
                x={k:e[k] for k in e if k not in ('s',)}; print('   ',x)
        for x in range(rr-3,dead[0]['r']+1):
            i=ri.get(x)
            if i is None: continue
            pc=(ch[c]['x'][i],ch[c]['y'][i],round(ch[c]['hp'][i])); pv=(ch[v]['x'][i],ch[v]['y'][i],round(ch[v]['hp'][i]))
            print(f"    r{x} ch {pc} us {pv} dec {dec.get((x,v),'.')}")
