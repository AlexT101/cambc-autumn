"""Per champion type: gold earned, mean unspent gold while alive, max HP at r300/600, deaths, gems collected, camp dmg."""
import json, gzip, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
CH=json.load(open(ROOT+'/enums.json'))['champions']
def one(d):
    meta=json.load(open(d+'/meta.json')); w=meta['result']['winner']
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; ri={r:i for i,r in enumerate(rounds)}
    out=[]
    for c,m in zip(R['champions'],meta['champions']):
        al=[i for i in range(len(rounds)) if c['alive'][i]]
        if not al: continue
        ug=st.mean(c['gold'][i] for i in al)
        hp3=c['maxHp'][ri[300]] if 300 in ri else None; hp6=c['maxHp'][ri[600]] if 600 in ri else None
        s=m['stats']
        out.append((CH[m['type']],m['team']==w,m['earnedGold'],ug,hp3,hp6,m['deaths'],s.get('collectedGems',0),s.get('monsterDamageDone',0),len(rounds)))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    tab=collections.defaultdict(list)
    for x in S: tab[x[0]].append(x)
    print('%-14s %5s %7s %7s %6s %6s %6s %7s %8s'%('type','n','earned','unspent','hp300','hp600','deaths','gems','campdmg'))
    for t,xs in sorted(tab.items(),key=lambda kv:-len(kv[1])):
        f=lambda j:[x[j] for x in xs if x[j] is not None]
        print('%-14s %5d %7.0f %7.0f %6.0f %6.0f %6.2f %7.0f %8.0f'%(t,len(xs),st.mean(f(2)),st.mean(f(3)),st.mean(f(4)) if f(4) else 0,st.mean(f(5)) if f(5) else 0,st.mean(f(6)),st.mean(f(7)),st.mean(f(8))))
