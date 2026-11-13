# After a stun/lock stop of a winning enemy channel: is the stopper the one who dies, how soon, killed by the channeller?
# Channeller health at the stop; the stopper's distance; how many of ours were within 5 of the channeller.
# Usage: after.py EXTRACT_DIR CAND
import json,gzip,sys,collections
A=sys.argv[1].rstrip('/')+'/'; cand=sys.argv[2]
idx=json.load(open(A+'index.json'))['games']; c=collections.Counter(); hp=[]; games=0; dd=collections.Counter(); near=collections.Counter(); restart=collections.Counter()
for r in idx:
    if cand not in r['teams']: continue
    ct=r['teams'].index(cand); d=r['dir']; games+=1; m=json.load(open(A+d+'/meta.json'))
    team={x['id']:x['team'] for x in m['champions']}; name={x['id']:x['name'] for x in m['champions']}
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); ri={x:i for i,x in enumerate(R['round'])}; ch={int(x['id']):x for x in R['champions']}
    total=[0,0]; open_={}; stun_by={}; lock_by={}
    for i,e in enumerate(ev):
        k=e['k']
        if k=='cast' and e.get('stun'):
            for v in e['stun']: stun_by[v]=(e['a'],e['r'],e['t'])
        if k=='lock_place': lock_by[tuple(e['to'])]=(e['a'],e['r'],e['t'])
        if k=='tribute_end': total[team[e['a']]]=e.get('total',0); open_.pop(e['a'],None)
        elif k=='tribute_start' and team[e['a']]!=ct and total[team[e['a']]]+e['gems']>=1000: open_[e['a']]=e
        elif k=='tribute_cancel' and e['a'] in open_:
            st=open_.pop(e['a']); cause=e.get('cause'); chn=e['a']; rr=e['r']
            if cause not in ('stun','lock'): continue
            s=stun_by.get(chn) if cause=='stun' else lock_by.get(tuple(st['altar']))
            if not s or s[1]!=rr or team[s[0]]!=ct: c[cause+'_not_ours']+=1; continue
            stopper=s[0]; c[cause]+=1
            j=ri.get(rr)
            if j is not None and ch[chn]['hp'][j] is not None: hp.append(ch[chn]['hp'][j])
            if j is not None:
                cx,cy=ch[chn]['x'][j],ch[chn]['y'][j]
                if cx is not None:
                    n=sum(1 for o in ch if team[o]==ct and ch[o]['x'][j] is not None and ch[o]['alive'][j] and max(abs(ch[o]['x'][j]-cx),abs(ch[o]['y'][j]-cy))<=5)
                    near[(cause,min(n,4))]+=1
                    sx=ch[stopper]['x'][j]
                    if sx is not None: dd[(cause,max(abs(sx-cx),abs(ch[stopper]['y'][j]-cy)))]+=1
            # stopper death within 12 rounds; by the channeller?
            for e2 in ev[i:]:
                if e2['r']>rr+12: break
                if e2['k']=='death' and e2['v']==stopper:
                    c[cause+'_stopper_dead']+=1; c[cause+'_stopper_dead_by_ch']+=e2.get('by')==chn; c[cause+'_stopper_dead_r+%d'%min(e2['r']-rr,3)]+=1; c[cause+'_stopper_gems']+=e2.get('gems',0); break
            for e2 in ev[i:]:
                if e2['r']>rr+12: break
                if e2['k']=='tribute_start' and e2['a']==chn:
                    restart[(cause,'same' if e2['altar']==st['altar'] else 'other')]+=1; break
print('games',games)
for k in sorted(c): print(f'  {k:28} {c[k]/games:.3f} n={c[k]}')
hp.sort(); print('channeller hp quartiles', [hp[int(q*len(hp))] for q in (0.1,0.25,0.5,0.75,0.9)] if hp else None)
print('stopper distance', sorted(dd.items())); print('ours within 5', sorted(near.items())); print('restart within 12', sorted(restart.items()))
