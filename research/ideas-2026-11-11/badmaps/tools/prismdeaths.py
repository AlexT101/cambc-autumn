from lib import *
import pickle
out=[]
for d,gm in find():
    if 'Prism' not in gm['our_picks']: continue
    A,meta,R,ev,mp,us,team,typ=acct(d,gm)
    ch={c['id']:c for c in R['champions']}; rr=R['round']
    pid=[c for c in ch if typ[c]=='Prism' and team[c]==us][0]
    P=ch[pid]
    sp=mp['spawn']; ctr=lambda s:((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2)
    own=ctr(sp[us]); en=ctr(sp[1-us])
    cheb=lambda a,b:max(abs(a[0]-b[0]),abs(a[1]-b[1]))
    # bag timeline stats
    bags=[P['gems'][i] for i in range(len(rr)) if P['alive'][i]]
    row=dict(match=gm['match'],map=gm['map'],opp=gm['opp_name'][:4],win=gm['result']=='win',rounds=gm['rounds'],meanbag=sum(bags)/max(1,len(bags)),maxbag=max(bags) if bags else 0,deaths=[])
    for e in ev:
        if e['k']=='death' and e['v']==pid:
            i=e['r']-1
            # seen enemies in previous rounds
            sees=[len(P['sees'][j]) for j in range(max(0,i-4),i+1)]
            hpfrac=[P['hp'][j]/max(1,P['maxHp'][j]) for j in range(max(0,i-4),i)]
            killer=e.get('by'); 
            row['deaths'].append(dict(r=e['r'],gems=e.get('gems',0),at=e['at'],d_own=cheb(e['at'],own),d_en=cheb(e['at'],en),sees=sees,hp=hpfrac,killer=typ.get(killer) if killer is not None and 'camp' not in e else 'camp',maxhp=P['maxHp'][max(0,i-1)]))
    out.append(row)
pickle.dump(out,open('prismdeaths.pkl','wb'))
