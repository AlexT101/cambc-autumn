"""Non-Prism captures: distance from the group to the team's living Prism at payout, by round phase."""
import gzip, json, sys
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    d=Path(d)
    try:
        meta=json.loads((d/'meta.json').read_text()); mp=json.loads((d/meta['mapFile']).resolve().read_text())
        R=json.load(gzip.open(d/'rounds.json.gz')); ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    except Exception: return None
    typ={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    idx={c['id']:i for i,c in enumerate(R['champions'])}
    tiles={g['id']:g['tiles'] for g in mp['groups']}
    out=Counter()
    for e in ev:
        if e['k']!='capture': continue
        r=e['r']; ix=min(r,len(R['round']))-1
        for cid,gm,gd in e['shares']:
            if gm<=0: continue
            ph='r1-150' if r<=150 else 'r151-300' if r<=300 else 'r301-600' if r<=600 else 'r601+'
            if typ[cid]=='Prism':
                out[(ph,'prism')]+=gm; continue
            pr=[c for c in typ if typ[c]=='Prism' and team[c]==team[cid]]
            if not pr: out[(ph,'noprism')]+=gm; continue
            p=pr[0]; c=R['champions'][idx[p]]
            if not c['alive'][ix]: out[(ph,'prism_dead')]+=gm; continue
            pp=(c['x'][ix],c['y'][ix]); dd=min(cheb(pp,t) for t in tiles[e['g']])
            b='<=6' if dd<=6 else '7-12' if dd<=12 else '13-20' if dd<=20 else '21+'
            out[(ph,b)]+=gm
    return out
if __name__=='__main__':
    dirs=[p.parent for p in Path(sys.argv[1]).glob('*/meta.json')]
    tot=Counter(); n=0
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one,[str(x) for x in dirs],chunksize=8):
            if r: tot.update(r); n+=1
    print(n,'games; captured gems per team-game by holder and distance from Prism to group at payout')
    for ph in ['r1-150','r151-300','r301-600','r601+']:
        print(ph, ' '.join(f"{k}:{tot[(ph,k)]/(2*n):.1f}" for k in ['prism','<=6','7-12','13-20','21+','prism_dead','noprism']))
