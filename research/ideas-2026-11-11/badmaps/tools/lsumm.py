from lib2 import *
import sys
def cls_of(g):
    tys=set(x.split()[0] for x in g['types'])
    return 'Mono' if 'Monolith' in tys else 'Golem' if 'Golem' in tys else 'Elk' if 'Elk' in tys else 'Wolf' if 'Wolf' in tys else 'Clus'
def summ(ext,mapname,flt=None):
    print('#####',mapname)
    for g in sorted(local_games(ext),key=lambda g:g['src']):
        if g['map'].replace('-','_')!=mapname.replace('-','_'): continue
        if flt and flt not in g['src']: continue
        meta,R,ev,mp=load(ext,g['dir']); us=g['us']
        A,team,typ=acct(meta,R,ev,us)
        G={x['id']:x for x in mp['groups']}
        cls=collections.defaultdict(lambda:[0,0,0,0])
        for e in ev:
            if e['k']=='capture':
                gg=G[e['g']]; t=0 if e['team']==us else 1
                side='mid' if gg['side']==-1 else ('own' if gg['side']==us else 'enemy')
                k=(side,cls_of(gg)); cls[k][t]+=1; cls[k][2+t]+=sum(s[1] for s in e['shares'])
        s=' | '.join(f"{k[0]}-{k[1]} {v[0]}({v[2]}g)/{v[1]}({v[3]}g)" for k,v in sorted(cls.items(),key=lambda kv:-(kv[1][2]+kv[1][3])) if v[2]+v[3]>0)
        opp='Mt3q' if 'Mt3q' in g['src'] else 'Flp4' if 'Flp4' in g['src'] else '?'
        picks=meta['draft']['picks']
        print(f"  {opp} {'ab'[us]} {'W' if g['win'] else 'L'} {g['rounds']:4d} us[{','.join(p[:4] for p in picks[us])}] them[{','.join(p[:4] for p in picks[1-us])}] :: {s}")
if __name__=='__main__':
    for m in sys.argv[2:]: summ(sys.argv[1],m)
