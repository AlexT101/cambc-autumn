"""Enemy captures and our nearest alive champion's distance to the group's tiles at hold start (payout-6) and at
the clear; gems/gold of those captures; whether our side saw the group."""
import gzip,json,sys,collections,os,statistics as st
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    tiles={x['id']:x['tiles'] for x in mp['groups']}; gems={x['id']:x['gems'] for x in mp['groups']}; gold={x['id']:x['gold'] for x in mp['groups']}
    ch=R['champions']; out=[]
    names={int(c['id']):c['name'] for c in meta['champions']}
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='capture': continue
        t=e['team']; gid=e['g']; r=e['r']
        holders=[s[0] for s in e['shares']]
        for back in (6,12):
            i=max(0,r-1-back)
            best=99; who=None
            for c in ch:
                if int(c['team'])==t or not c['alive'][i]: continue
                dd=min(max(abs(c['x'][i]-x),abs(c['y'][i]-y)) for x,y in tiles[gid])
                if dd<best: best,who=dd,names[int(c['id'])]
            out.append((back,best,gems.get(gid,0),gold.get(gid,0),r,names.get(holders[0]) if holders else None))
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res=[x for r in ex.map(g,dirs,chunksize=8) for x in r]
    G=len(dirs)*2
    for back in (6,12):
        S=[x for x in res if x[0]==back]
        print(f'at payout-{back}: captures per team-game {len(S)/G:.1f}, gems {sum(x[2] for x in S)/G:.0f}')
        for lo,hi in [(0,3),(4,6),(7,9),(10,14),(15,99)]:
            T=[x for x in S if lo<=x[1]<=hi]
            print(f'  opp nearest {lo}-{hi}: {len(T)/G:.1f} a team-game, {sum(x[2] for x in T)/G:.0f} gems, {sum(x[3] for x in T)/G:.0f} gold; holder Prism {sum(x[5]=="Prism" for x in T)/max(1,len(T)):.2f}')
