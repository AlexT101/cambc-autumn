import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); ev=events(d); R=rounds(d)
    C={c['id']:c for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    ri={rn:i for i,rn in enumerate(R['round'])}; ch={c['id']:c for c in R['champions']}
    def st(cid,rn):
        i=ri.get(rn); c=ch[cid]
        if i is None or not c['alive'][i]: return None
        return dict(p=(c['x'][i],c['y'][i]),hp=c['hp'][i],mh=c['maxHp'][i],g=c['gems'][i],str=c['str'][i])
    # champion-champion damage
    hits=[]
    campatk=defaultdict(list); campdmg_taken=defaultdict(list)
    for e in ev:
        if e['k'] in ('attack','cast'):
            for v,a in (e.get('dmg') or []):
                if v in team and team[v]!=team[e['a']]:
                    hits.append((e['r'],e['a'],v,a,tuple(e['f']),e['k'],e.get('ab')))
            if e.get('cdmg'): campatk[e['a']].append(e['r'])
        elif e['k']=='camp_attack':
            if e.get('tgt') is not None: campdmg_taken[e['tgt']].append((e['r'],e['dmg']))
    deaths=[e for e in ev if e['k']=='death']
    fights=[]
    for h in hits:
        rn,a,v,amt,f,k,ab=h
        best=None
        for F in fights:
            if rn-F['last']<=5 and min(cheb(f,p) for p in F['pts'])<=8: best=F
        if best is None:
            best=dict(start=rn,last=rn,pts=[],hits=[],part=set()); fights.append(best)
        best['last']=rn; best['pts'].append(f); best['hits'].append(h); best['part'].update([a,v])
        best['pts']=best['pts'][-30:]
    out=[]
    us=r['us']
    for F in fights:
        s=F['start']; e_=F['last']
        dd=[x for x in deaths if s<=x['r']<=e_+2 and (x['v'] in F['part']) and x.get('linked') is None]
        kills_us=sum(1 for x in dd if team[x['v']]!=us); kills_them=sum(1 for x in dd if team[x['v']]==us)
        gems_lost_us=sum(x['gems'] for x in dd if team[x['v']]==us); gems_lost_them=sum(x['gems'] for x in dd if team[x['v']]!=us)
        first=F['hits'][0]; init='us' if team[first[1]]==us else 'them'
        center=F['hits'][0][4]
        # champions present within 8 of first-hit location at s-1
        pres={'us':[], 'them':[]}
        for cid in C:
            z=st(cid,s-1)
            if z and cheb(z['p'],center)<=8: pres['us' if team[cid]==us else 'them'].append((C[cid]['name'],z['hp'],z['mh'],z['g'],z['str'],cid))
        part={'us':[C[c]['name'] for c in F['part'] if team[c]==us],'them':[C[c]['name'] for c in F['part'] if team[c]!=us]}
        dmg={'us':sum(x[3] for x in F['hits'] if team[x[1]]==us),'them':sum(x[3] for x in F['hits'] if team[x[1]]!=us)}
        # were our participants farming (camp attack) in the 5 rounds before start, and camp dmg taken during fight
        farm_us=sum(1 for c in F['part'] if team[c]==us and any(s-5<=x<=s for x in campatk[c]))
        farm_them=sum(1 for c in F['part'] if team[c]!=us and any(s-5<=x<=s for x in campatk[c]))
        cdt_us=sum(a for c in F['part'] if team[c]==us for (x,a) in campdmg_taken[c] if s-5<=x<=e_)
        cdt_them=sum(a for c in F['part'] if team[c]!=us for (x,a) in campdmg_taken[c] if s-5<=x<=e_)
        # first hitter type and whether first hit was by a range>=3 on melee
        out.append(dict(key=d,src=r['source'],map=r['map'],opp=r['opp'],won=r['won'],start=s,end=e_,init=init,first=(C[first[1]]['name'],C[first[2]]['name'],first[5],first[6]),
            pres=pres,part=part,dmg=dmg,ku=kills_us,kt=kills_them,glu=gems_lost_us,glt=gems_lost_them,farm_us=farm_us,farm_them=farm_them,cdt_us=cdt_us,cdt_them=cdt_them,nh=len(F['hits'])))
    return out
if __name__=='__main__':
    G=games()
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,G) for x in o]
    json.dump(res,open(sys.argv[1]+'/fights.json','w'))
    print(len(res))
