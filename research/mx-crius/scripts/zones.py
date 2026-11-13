"""Captured gems by zone of the group (share s = d_ownspawn/(d_own+d_enemy), Chebyshev from spawn centres: own <0.4,
middle 0.4-0.6, enemy >0.6), winner vs loser, by round T. usage: py zones.py EXTRACT [T...]"""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; TS=[int(x) for x in sys.argv[2:]] or [150,300,600]
def one(d):
    m=json.load(open(d+'/meta.json')); w=m['result']['winner']; team={c['id']:c['team'] for c in m['champions']}
    mp=json.load(open(os.path.join(d,m['mapFile']))); camps={c['id']:c for c in mp['camps']}
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    cen={}
    for t in (0,1):
        xs=[(c['x'][0],c['y'][0]) for c in R['champions'] if c['team']==t and c['x'][0] is not None]
        cen[t]=(sum(a for a,b in xs)/len(xs),sum(b for a,b in xs)/len(xs))
    gpos={}
    for g in mp['groups']:
        ps=[(camps[c]['x'],camps[c]['y']) for c in g['camps'] if c in camps and 'x' in camps[c]]
        if not ps: ps=[tuple(camps[c]['pos']) for c in g['camps'] if c in camps and 'pos' in camps[c]]
        if ps: gpos[g['id']]=(sum(a for a,b in ps)/len(ps),sum(b for a,b in ps)/len(ps))
    out=collections.Counter()
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='capture': continue
        g=e['g']
        if g not in gpos: continue
        x,y=gpos[g]
        for cid,gm,gd in e['shares']:
            t=team[cid]
            do=max(abs(x-cen[t][0]),abs(y-cen[t][1])); de=max(abs(x-cen[1-t][0]),abs(y-cen[1-t][1]))
            s=do/max(1e-9,do+de); z='own' if s<0.4 else 'mid' if s<=0.6 else 'enemy'
            for T in TS:
                if e['r']<=T: out[(T,'W' if t==w else 'L',z)]+=gm
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    c0=json.load(open(ds[0]+'/meta.json')); mp=json.load(open(os.path.join(ds[0],c0['mapFile']))); print('camp keys',list(mp['camps'][0].keys()))
    tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one,ds,chunksize=8): tot.update(o)
    n=len(ds)
    for T in TS:
        print('r%d per game:'%T,' '.join('%s W %.1f L %.1f (diff %.1f)'%(z,tot[(T,'W',z)]/n,tot[(T,'L',z)]/n,(tot[(T,'W',z)]-tot[(T,'L',z)])/n) for z in ('own','mid','enemy')))
