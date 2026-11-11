import sys,pickle,collections,json,os
sys.path.insert(0,'/home/ubuntu/tmp-offload/badmaps/an')
import lib2
EXT=sys.argv[1]; OUT=sys.argv[2]; US=sys.argv[3]
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
out=[]
for g in lib2.loadx(EXT):
    meta,R,ev,mp=lib2.load(EXT,g['dir'])
    us=g['teams'].index(US)
    ch=R['champions']; team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:c['name'] for c in meta['champions']}
    n=len(R['round'])
    sp=mp['spawn'][us]; spc=((sp['minX']+sp['maxX'])//2,(sp['minY']+sp['maxY'])//2)
    esp=mp['spawn'][1-us]; espc=((esp['minX']+esp['maxX'])//2,(esp['minY']+esp['maxY'])//2)
    last_resp={c['id']:0 for c in meta['champions']}
    D=[]
    for e in ev:
        if e['k']=='respawn': last_resp[e['a']]=e['r']
        if e['k']!='death': continue
        r=e['r']; i=min(max(r-2,0),n-1)
        v=e['v']; at=tuple(e['at'])
        def near(t,rad):
            c=0;hp=0
            for x in ch:
                if x['team']!=t or x['id']==v or not x['alive'][i]: continue
                if cheb((x['x'][i],x['y'][i]),at)<=rad: c+=1;hp+=x['hp'][i]
            return c,hp
        alive=[sum(1 for x in ch if x['team']==t and x['alive'][i]) for t in (0,1)]
        vt=team[v]
        D.append(dict(r=r,v=v,typ=typ[v],ours=vt==us,at=at,gems=e.get('gems',0),camp='camp' in e or e.get('by') is None,
            by=typ.get(e.get('by')),cause=e.get('cause'),
            ally6=near(vt,6),enemy6=near(1-vt,6),ally10=near(vt,10),enemy10=near(1-vt,10),
            alive_own=alive[vt],alive_opp=alive[1-vt],
            d_altar=min(cheb(at,a) for a in mp['altars']),d_own_spawn=cheb(at,spc if vt==us else espc),d_opp_spawn=cheb(at,espc if vt==us else spc),
            since_resp=r-last_resp[v],maxhp=ch[v]['maxHp'][i],assists=len(e.get('assists',[]))))
    gold={}
    for rr in (100,200,300,500):
        i=min(rr,n)-1
        gold[rr]=[sum(x['earned'][i] for x in ch if x['team']==t) for t in (us,1-us)]
    opp=g['teams'][1-us]
    picks=meta['draft']['picks']
    out.append(dict(match=g['dir'],map=os.path.basename(g['source']).split('-',1)[1].rsplit('-',1)[0],opp='Inte' if 'Fl' in opp else 'Mite',side='ab'[us],win=g['winner']==us,rounds=n,
        cls=None,D=D,gold=gold,our_picks=picks[us],opp_picks=picks[1-us],
        gems=[R['gems'][us][-1],R['gems'][1-us][-1]],dir=EXT+'/'+g['dir'],us=us,W=mp['width'],H=mp['height'],naltar=len(mp['altars']),
        spawn_dist=cheb(spc,espc)))
pickle.dump(out,open(OUT,'wb'))
print(len(out))
