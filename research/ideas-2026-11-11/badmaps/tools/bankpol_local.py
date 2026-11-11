from lib2 import *
import pickle,sys
ext=sys.argv[1]; outp=sys.argv[2]
out=[]
for g in local_games(ext):
    meta,R,ev,mp=load(ext,g['dir']); us=g['us']
    team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:c['name'] for c in meta['champions']}
    opp='Mite' if 'Mt3q' in g['src'] else 'Inte'
    alt=mp['altars']; ch={c['id']:c for c in R['champions']}; pend={}
    for e in ev:
        k=e['k']
        if k=='capture':
            for cid,gg,go in e['shares']:
                if gg<=0: continue
                if cid in pend: pend[cid]['next']='capture'; out.append(pend.pop(cid))
                i=min(e['r']-1,len(R['round'])-1); c=ch[cid]
                if not c['alive'][i]: continue
                pos=(c['x'][i],c['y'][i])
                dmin=min(max(abs(pos[0]-a[0]),abs(pos[1]-a[1])) for a in alt)
                pend[cid]=dict(us=team[cid]==us,opp=opp,typ=typ[cid],bag=c['gems'][i],d=dmin,r=e['r'],map=g['map'],next=None)
        elif k=='tribute_start' and e['a'] in pend:
            pend[e['a']]['next']='tribute'; out.append(pend.pop(e['a']))
        elif k=='death' and e['v'] in pend:
            pend[e['v']]['next']='death'; out.append(pend.pop(e['v']))
pickle.dump(out,open(outp,'wb')); print(len(out))
