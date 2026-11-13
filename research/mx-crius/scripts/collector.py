"""Ally (non-Prism) captures, by gems: Prism's walk distance (Chebyshev) to the group's tiles at payout-6 and payout-3,
and Prism state then. Prism's share of team captured gems."""
import json, gzip, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
CH=json.load(open(ROOT+'/enums.json'))['champions']
def one(d):
    meta=json.load(open(d+'/meta.json')); team={c['id']:c['team'] for c in meta['champions']}
    typ={c['id']:CH[c['type']] for c in meta['champions']}
    mp=json.load(open(os.path.join(d,meta['mapFile']))); groups={g['id']:g for g in mp['groups']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; ri={r:i for i,r in enumerate(rounds)}
    prism={t:[c for c in R['champions'] if c['team']==t and typ[c['id']]=='Prism'] for t in (0,1)}
    out=[]; share=collections.Counter()
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='capture': continue
        t=e['team']; G=groups.get(e['g'])
        if not prism[t] or not G: continue
        P=prism[t][0]; gm=sum(s[1] for s in e['shares'])
        pg=sum(s[1] for s in e['shares'] if s[0]==P['id'])
        share['team']+=gm; share['prism']+=pg
        if pg>0 or gm==0: continue
        res=[]
        for lag in (6,3):
            i=ri.get(e['r']-lag)
            if i is None or not P['alive'][i] or P['x'][i] is None: res.append(None); continue
            x,y=P['x'][i],P['y'][i]
            dd=min(max(abs(x-a),abs(y-b)) for a,b in G['tiles'])
            res.append((dd,P['chan'][i]))
        out.append((gm,e['r'],res))
    return out,share
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    S=[];sh=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o,s in ex.map(one,ds,chunksize=8): S+=o; sh.update(s)
    print('Prism share of captured gems (Prism teams): %.3f'%(sh['prism']/sh['team']))
    N=len(ds)
    print('ally captures without Prism per team-game %.1f, gems %.0f'%(len(S)/(2*N), sum(s[0] for s in S)/(2*N)))
    for lim in (4,6,8,12):
        x=[s for s in S if s[2][0] and s[2][0][0]<=lim]
        print(' Prism within %2d at payout-6: %.2f caps/team-game, %.0f gems/team-game; dead/channelling share %.2f'%(lim,len(x)/(2*N),sum(s[0] for s in x)/(2*N),sum(1 for s in x if s[2][0][1])/max(1,len(x))))
