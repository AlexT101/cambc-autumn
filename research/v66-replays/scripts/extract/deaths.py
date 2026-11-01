import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); ev=events(d); R=rounds(d); mp=mapj(m)
    C={c['id']:c for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    ri={rn:i for i,rn in enumerate(R['round'])}
    ch={c['id']:c for c in R['champions']}
    def pos(cid,rn):
        i=ri.get(rn); 
        if i is None: return None
        c=ch[cid]; 
        return (c['x'][i],c['y'][i]) if c['alive'][i] else None
    def hp(cid,rn):
        i=ri.get(rn); c=ch[cid]; return c['hp'][i]/c['maxHp'][i] if i is not None and c['alive'][i] else None
    sp=mp['spawn']
    # damage timeline per victim
    dmg=defaultdict(list) # cid -> (r, src_kind, src, amt)
    farm=defaultdict(list)
    for e in ev:
        if e['k'] in('attack','cast'):
            for v,a in e.get('dmg',[]) or []: dmg[v].append((e['r'],'champ',e['a'],a))
            if e.get('cdmg'): farm[e['a']].append(e['r'])
        elif e['k']=='camp_attack':
            if e.get('tgt') is not None: dmg[e['tgt']].append((e['r'],'camp',e['camp'],e['dmg']))
            for v,a in e.get('xdmg',[]) or []: dmg[v].append((e['r'],'camp',e['camp'],a))
    out=[]
    for e in ev:
        if e['k']!='death' or e.get('linked') is not None: continue
        v=e['v']; rn=e['r']; side='us' if team[v]==r['us'] else 'them'
        at=tuple(e['at'])
        def near(rr,rad):
            a=n=0
            for cid in C:
                p=pos(cid,rr)
                if p and cheb(p,at)<=rad:
                    if team[cid]==team[v]: a+=1
                    else: n+=1
            return a,n
        a1,n1=near(rn-1,6); a5,n5=near(rn-5,8)
        alive_a=sum(1 for c in C if team[c]==team[v] and pos(c,rn-1)); alive_n=sum(1 for c in C if team[c]!=team[v] and pos(c,rn-1))
        dd=[x for x in dmg[v] if rn-15<=x[0]<=rn]
        cd=sum(x[3] for x in dd if x[1]=='camp'); hd=sum(x[3] for x in dd if x[1]=='champ')
        first=min([x[0] for x in dd if x[1]=='champ'],default=None)
        fr=[x for x in farm[v] if rn-15<=x<=rn]
        out.append(dict(key=r['dir'],src=r['source'],map=r['map'],opp=r['opp'],won=r['won'],side=side,r=rn,victim=C[v]['name'],killer=(C[e['by']]['name'] if e.get('by') is not None else 'camp'),
            gems=e['gems'],near1=(a1,n1),near5=(a5,n5),alive=(alive_a,alive_n),campdmg=cd,champdmg=hd,engage_len=(rn-first if first else None),farmed=len(fr),
            hp5=hp(v,rn-5),hp15=hp(v,rn-15), assists=len(e.get('assists') or [])))
    return out
if __name__=='__main__':
    G=games()
    with ProcessPoolExecutor(48) as ex: res=[x for o in ex.map(one,G) for x in o]
    json.dump(res,open(sys.argv[1]+'/deaths.json','w'))
    print(len(res))
