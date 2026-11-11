import gzip, json, sys, collections
from pathlib import Path
an=Path(sys.argv[1]); c=collections.Counter()
for d in sorted(p.parent for p in an.glob('*/meta.json')):
    meta=json.loads((d/'meta.json').read_text()); names={x['id']:x['name'] for x in meta['champions']}
    win=meta['result']['winner']
    R=json.load(gzip.open(d/'rounds.json.gz')); ch=R['champions']
    pr={c_['team']:c_ for c_ in ch if names[c_['id']]=='Prism'}
    if len(pr)<2: c['nomirror']+=1; c[('nomirror_win_t0')]+= win==0; continue
    n=len(R['round'])
    # time-integrated: share of rounds 100..end where team0 prism bag > team1
    for r in (200,400,600):
        if r>=n: continue
        a=pr[0]['gems'][r] if pr[0]['alive'][r] else 0; b=pr[1]['gems'][r] if pr[1]['alive'][r] else 0
        if a==b: continue
        c[(r,'n')]+=1; c[(r,'bigger wins')]+= (a>b)==(win==0)
        # tributed lead
        ga,gb=R['gems'][0][r],R['gems'][1][r]
        tot_a=a+ga; tot_b=b+gb
        if tot_a!=tot_b: c[(r,'n_tot')]+=1; c[(r,'bigger total(score+prismbag) wins')]+= (tot_a>tot_b)==(win==0)
print(sorted(c.items(), key=str))
