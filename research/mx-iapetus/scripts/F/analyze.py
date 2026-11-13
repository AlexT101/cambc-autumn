# Death audit stage 2 over collect.py's records. Usage: analyze.py RECORDS.json [--dump CLASS N]
import json,sys,collections
G=json.load(open(sys.argv[1])); n=len(G)
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def commit(rec):
    s=rec.get('seq') or {}
    for x in range(rec['r0']-1,rec['r0']-6,-1):
        c=s.get(str(x),'.')
        if c!='.': return c
    return '?'
def near(rec,key,c,team,R):
    S=rec[key]; me=S.get(str(c))
    if not me or me['x'] is None: return 0
    return sum(1 for o,s in S.items() if s and s['al'] and s['x'] is not None and rec['team'][o]==team and o!=str(c) and cheb((s['x'],s['y']),(me['x'],me['y']))<=R)
C=collections.defaultdict(lambda:collections.Counter()); K=collections.defaultdict(lambda:collections.Counter()); ex=collections.defaultdict(list)
tot=collections.Counter()
for g in G:
    ct=g['ct']
    for d in g['deaths']:
        if d['ours']:
            c=commit(d); kind='camp' if d['camp'] else 'champ'
            key=(kind,c)
            X=C[key]; X['lives']+=1; X['gems']+=d['gems']; X['win']+=g['win']
            dx=(d.get('dx') or {}).get(str(d['r0']-1))
            if dx:
                X['traced']+=1; X['seen']+=dx[5]>0; X['lethal_read']+=dx[3]>=dx[0]; X['hit_read']+=dx[2]>0
            v=d['v']; s0=d['s0'].get(str(v))
            if s0 and s0['x'] is not None:
                ne=near(d,'s0',v,1-ct,8); na=near(d,'s0',v,ct,8)
                X['outnum']+=ne>na+1; X['bag50']+=d['gems']>=50; X['hp_frac']+=s0['hp']/max(1,s0['mx'])
                X['dur']+=d['round']-d['r0']
            tot['lives']+=1; tot['gems']+=d['gems']
            ex[key].append(d)
        elif d['by'] is not None and d['team'][str(d['by'])]==ct:
            c=commit(d); Y=K[c]; Y['kills']+=1; Y['gems']+=d['gems']
            tot['kills']+=1; tot['kgems']+=d['gems']
        elif d['team'][str(d['v'])]!=ct:
            tot['enemy_other']+=1
print(f"games {n}  our deaths {tot['lives']/n:.2f}/game, bag gems lost {tot['gems']/n:.1f}/game; our kills {tot['kills']/n:.2f}/game, gems {tot['kgems']/n:.1f}/game; enemy other deaths {tot['enemy_other']/n:.2f}")
print('class (kind,commit)  lives/g gems/g | %traced %seenEnemy %hitRead %lethalRead %outnumbered(e>a+1 in 8) %bag50 mean-hp@commit mean-dur')
for k,X in sorted(C.items(),key=lambda kv:-kv[1]['gems']):
    L=X['lives']; t=max(1,X['traced'])
    print(f"  {k[0]:5} {k[1]}  {L/n:.3f} {X['gems']/n:6.1f} | {100*X['traced']/L:3.0f} {100*X['seen']/t:3.0f} {100*X['hit_read']/t:3.0f} {100*X['lethal_read']/t:3.0f} {100*X['outnum']/L:3.0f} {100*X['bag50']/L:3.0f} {X['hp_frac']/L:.2f} {X['dur']/L:4.1f}  n={L}")
print('kills by our killer branch at the victim\'s engagement start-1:')
for k,Y in sorted(K.items(),key=lambda kv:-kv[1]['kills']): print(f"  {k} {Y['kills']/n:.3f} gems {Y['gems']/n:.1f}")
if '--dump' in sys.argv:
    i=sys.argv.index('--dump'); kind,c,N=sys.argv[i+1],sys.argv[i+2],int(sys.argv[i+3])
    L=sorted(ex[(kind,c)],key=lambda d:-d['gems'])
    import random; random.seed(1); L=L[:N//2]+random.sample(L[N//2:],min(N-N//2,len(L)-N//2))
    for d in L:
        s=d.get('seq') or {}
        print(f"\n{d['src']} r{d['round']} {d['vname']} bag{d['gems']} by {d['byname']} camp={d['camp']} r0={d['r0']} seq={''.join(s.get(str(x),'.') for x in range(d['round']-15,d['round']+1))}")
        for x in range(d['r0']-3,d['round']+1):
            if str(x) in (d.get('dx') or {}): print('   DX',x,d['dx'][str(x)])
        v=str(d['v']); s0=d['s0'][v]
        print('   me@r0-1',s0)
        for o,st in d['s0'].items():
            if st and st['al'] and st['x'] is not None and o!=v and cheb((st['x'],st['y']),(s0['x'],s0['y']))<=9:
                print('    ',('ally ' if d['team'][o]==d['team'][v] else 'ENEMY'),d['names'][o],f"d{cheb((st['x'],st['y']),(s0['x'],s0['y']))} hp{st['hp']:.0f}/{st['mx']:.0f} g{st['g']} cd{st['cd']} chan{st['chan']}")
        print('   dmg',d['dmg'][-12:])
