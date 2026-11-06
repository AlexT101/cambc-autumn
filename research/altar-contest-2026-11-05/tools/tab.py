import json,sys,collections
rows=[json.loads(l) for l in open(sys.argv[1])]
T=[r for r in rows if r['kind']=='trib']; D=[r for r in rows if r['kind']=='bagdeath']
print('tributes',len(T),'bagdeaths',len(D))
print('causes',collections.Counter(r['res'] for r in T).most_common())
def mb(r):
    m=r['oth']-r['own']
    return '<=-6' if m<=-6 else '-5..-1' if m<0 else '0..4' if m<=4 else '5..14' if m<=14 else '15+'
def db(d): return '1-2' if d<=2 else '3-8' if d<=8 else '9-20' if d<=20 else '21+'
def show(title,key,sub=lambda r:True,rows=T):
    print('\n##',title)
    c=collections.defaultdict(lambda:[0,0,0,0,0,0])
    for r in rows:
        if not sub(r): continue
        k=key(r); x=c[k]; x[0]+=1; x[1]+=r['res']=='end'; x[2]+=r['res']=='cancel:stun'; x[3]+=r['res']=='cancel:lock'; x[4]+=r['died']; x[5]+=r['gems']*(r['res']=='end')
    print(f"{'key':28s} {'n':>6s} {'done%':>6s} {'stun%':>6s} {'lock%':>6s} {'died%':>6s} {'gems/start':>10s}")
    for k in sorted(c, key=str):
        x=c[k]
        if x[0]<30: continue
        print(f"{str(k):28s} {x[0]:6d} {100*x[1]/x[0]:6.1f} {100*x[2]/x[0]:6.1f} {100*x[3]/x[0]:6.1f} {100*x[4]/x[0]:6.1f} {x[5]/x[0]:10.1f}")
show('by channel turns',lambda r:db(r['dur']))
show('margin (enemy walk - own walk) x dur, dur>=9',lambda r:(mb(r),db(r['dur'])),lambda r:r['dur']>=9)
show('margin, all dur',lambda r:mb(r))
show('zones x dur>=9',lambda r:(min(r['nz'],4),db(r['dur'])),lambda r:r['dur']>=9)
show('altars x dur>=9',lambda r:(min(r['n'],6),db(r['dur'])),lambda r:r['dur']>=9)
show('allies within 4 at start, dur>=9',lambda r:(min(r['al4'],3),db(r['dur'])),lambda r:r['dur']>=9)
show('allies within 4 x margin<5 (contested), dur>=9',lambda r:(min(r['al4'],2),'contested' if r['oth']-r['own']<5 else 'ours'),lambda r:r['dur']>=9)
show('enemies within 8 at start, dur>=9',lambda r:(min(r['en8'],3)),lambda r:r['dur']>=9)
show('nearest own altar? multi-altar, dur>=9',lambda r:(r['nearest_own'],db(r['dur'])),lambda r:r['n']>1 and r['dur']>=9)
show('winning bag',lambda r:(r['winbag'],db(r['dur'])),lambda r:r['winbag'])
print('\n## bag deaths (>=10 gems)')
c=collections.Counter()
for r in D:
    c[('camp' if r['bycamp'] else 'champ', 'at altar<=3' if r['altd']<=3 else 'near<=8' if r['altd']<=8 else 'away', mb(r))]+=r['gems']
for k,v in sorted(c.items()): print(k,v)
