# Per-map win rate (v86-89 scrims vs Fish+Mite) against draftlab map features.
import json,collections,numpy as np,sys,os
F={}
for l in open(os.path.expanduser('~/tmp-offload/bigl/maps.jsonl')):
    r=json.loads(l); F[r['name']]=dict(r['f'],picks=r['picks'],W=r['W'],H=r['H'])
G=[json.loads(l) for l in open('research/ladder-scrims-2026-11-06/data/games.jsonl')]
G=[g for g in G if g.get('status')=='finished' and g['version']>=86 and g['opp_name'] in ('Intercontinental Fish','Mite')]
bym=collections.defaultdict(list)
for g in G: bym[g['map']].append(g['result']=='win')
names=[m for m in bym if m in F]; print(len(names),'maps matched')
wr=np.array([np.mean(bym[m]) for m in names])
keys=[k for k in F[names[0]] if isinstance(F[names[0]][k],(int,float))]
res=[]
for k in keys:
    x=np.array([F[m][k] for m in names],float)
    if x.std()==0: continue
    from scipy.stats import spearmanr
    c=spearmanr(x,wr)[0]; res.append((c,k))
print(' '.join(f'{k}:{c:+.2f}' for c,k in sorted(res)))
cols=['area','picks','spawn_dist','altars','groups_side','shared_groups','gems_side','gold_side','monoliths','golems','contested_share','big_groups','max_group','camp_near','altar_near']
print('map'.ljust(23),' '.join(c[:7].rjust(7) for c in cols))
srt=sorted(names,key=lambda m:np.mean(bym[m]))
for m in srt[:20]+['---']+srt[-10:]:
    if m=='---': print('---');continue
    print(f'{m[:18]:18s} {np.mean(bym[m]):.2f}',' '.join(f'{F[m][c]:7.2f}' if isinstance(F[m][c],float) else f'{F[m][c]:7d}' for c in cols))
# bins
for k in ['picks','altars','spawn_dist','area']:
    x=np.array([F[m][k] for m in names],float); qs=np.quantile(x,[0,.25,.5,.75,1])
    print(k,[ (round(qs[i]),round(qs[i+1]), round(wr[(x>=qs[i])&(x<=qs[i+1])].mean(),3)) for i in range(4)])
