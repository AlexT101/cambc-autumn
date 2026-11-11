import sys
from lib import *
def bygroup(mapname,opp=None,ver=115):
    for d,gm in sorted(find(mapname,opp=opp,ver=ver),key=lambda x:(x[1]['opp_name'],x[1]['side'])):
        A,meta,R,ev,mp,us,team,typ=acct(d,gm)
        G={g['id']:g for g in mp['groups']}
        sym=mp['symmetry']
        print('==',mapname,gm['opp_name'][:4],gm['side'],gm['result'],gm['rounds'],'gems',gm['our_gems'],gm['opp_gems'])
        cap=collections.defaultdict(lambda:[0,0,0,0,[],[]])
        for e in ev:
            if e['k']=='capture':
                t=0 if e['team']==us else 1
                c=cap[e['g']]; c[t]+=1; c[2+t]+=sum(s[1] for s in e['shares']); c[4+t].append(e['r'])
        # label side relative to us: own / enemy / mid
        for gid,g in sorted(G.items(),key=lambda kv:-(cap[kv[0]][2]+cap[kv[0]][3])):
            c=cap[gid]
            if c[0]+c[1]==0 and g['gems']==0: continue
            side='mid' if g['side']==-1 else ('own' if g['side']==us else 'enemy')
            ty=collections.Counter(t.split()[0][:4] for t in g['types'])
            print(f"   g{gid:2d} {side:5s} {dict(ty)} gems {g['gems']:3d} gold {g['gold']:3d} resp {g['respawn']:3d} at {g['tiles'][0]} | caps us {c[0]} ({c[2]}g) them {c[1]} ({c[3]}g) | first us {c[4][:3]} them {c[5][:3]}")
if __name__=='__main__':
    bygroup(sys.argv[1], sys.argv[2] if len(sys.argv)>2 else None)
