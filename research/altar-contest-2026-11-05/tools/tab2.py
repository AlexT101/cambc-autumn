import json,sys,collections
names=json.load(open(sys.argv[2]))
rows=[json.loads(l) for l in open(sys.argv[1])]
for r in rows: r['who']=names.get(r['d'],['?','?'])[r['team']]
T=[r for r in rows if r['kind']=='trib']; D=[r for r in rows if r['kind']=='bagdeath']
def db(d): return '1-8' if d<=8 else '9-20' if d<=20 else '21+'
def tab(title,key,sub,rows=T,minn=25):
    print('\n##',title)
    c=collections.defaultdict(lambda:[0,0,0,0,0])
    for r in rows:
        if not sub(r): continue
        x=c[key(r)]; x[0]+=1; x[1]+=r['res']=='end'; x[2]+=r['res'] in('cancel:stun','cancel:lock','cancel:death'); x[3]+=r['died']; x[4]+=r['gems']
    for k in sorted(c,key=str):
        x=c[k]
        if x[0]>=minn: print(f"  {str(k):45s} n={x[0]:5d} done={100*x[1]/x[0]:5.1f}% enemy-cancel={100*x[2]/x[0]:5.1f}% died={100*x[3]/x[0]:4.1f}% meanbag={x[4]/x[0]:5.1f}")
L=lambda r:r['dur']>=9
ctd=lambda r:'1zone' if r['nz']==1 else ('cont' if r['oth']-r['own']<5 else 'safe')
tab('long channels: enemies within 8 at start x zone/margin class',lambda r:(min(r['en8'],2),ctd(r)),L)
tab('long channels, no enemy within 8 at start: allies within 4',lambda r:(ctd(r),min(r['al4'],2)),lambda r:L(r) and r['en8']==0)
tab('long channels, enemy within 8: allies within 4 vs enemies within 8',lambda r:(min(r['en8'],3),min(r['al4'],3)),lambda r:L(r) and r['en8']>=1)
tab('long channels by team',lambda r:r['who'],L)
tab('Pantheon vs rest: long channels by class',lambda r:(r['who']=='Pantheon',ctd(r),db(r['dur'])),L)
tab('Pantheon vs rest: start with an enemy within 8 (share), long',lambda r:(r['who']=='Pantheon',r['en8']>0),L)
# gems lost per game
g=collections.defaultdict(lambda:collections.Counter())
games=collections.defaultdict(set)
for r in T: games[r['who']].add(r['d'])
for r in D:
    if r['bycamp']: continue
    p='altar<=3' if r['altd']<=3 else 'near<=8' if r['altd']<=8 else 'away'
    g[r['who']=='Pantheon'][p]+=r['gems']
print('\n## gems lost to champion kills per game (altar distance at death)')
for k,v in g.items():
    n=len(games['Pantheon']) if k else sum(len(s) for w,s in games.items() if w!='Pantheon')
    print(' Pantheon' if k else ' others', n, {p:round(x/n,1) for p,x in v.items()})
