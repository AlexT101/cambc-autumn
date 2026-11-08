# Per-map correlation with live (v86-89 vs Fish+Mite) of every replays/ab/bigl-ladder-* run, pooled, and split-half.
import json,collections,numpy as np,glob,os
G=[json.loads(l) for l in open('research/ladder-scrims-2026-11-06/data/games.jsonl')]
G=[g for g in G if g.get('status')=='finished' and g['version']>=86 and g['opp_name'] in ('Intercontinental Fish','Mite')]
live=collections.defaultdict(list); lf=collections.defaultdict(list); lm=collections.defaultdict(list)
for g in G:
    live[g['map']].append(g['result']=='win'); (lf if 'Fish' in g['opp_name'] else lm)[g['map']].append(g['result']=='win')
loc={}
for f in sorted(glob.glob('replays/ab/bigl-ladder-*/summary.json')):
    s=json.load(open(f)); r=json.load(open(s['suites'][0]['batch']+'/results.json')); d=collections.defaultdict(list)
    for m in r['matches']: d[os.path.basename(m['map']).replace('.map26a','')].append(m['winner']==0)
    loc[s['name']]=(d,s['cand_win_pct'])
ms=[m for m in live if all(m in d for d,_ in loc.values())]; L=np.array([np.mean(live[m]) for m in ms])
for n,(d,w) in loc.items(): print(f'{n:28s} {w:5.1f}%  r {np.corrcoef(L,[np.mean(d[m]) for m in ms])[0,1]:+.2f}')
names=[n for n in loc if 'fish' not in n]; A,Bn=names[::2],names[1::2]
agg=lambda grp,m: np.mean([x for n in grp for x in loc[n][0][m]])
a=np.array([agg(A,m) for m in ms]); b=np.array([agg(Bn,m) for m in ms])
print('maps',len(ms),'pooled r',np.corrcoef((a+b)/2,L)[0,1].round(2),'half vs half',np.corrcoef(a,b)[0,1].round(2),
      'live Fish vs Mite',np.corrcoef([np.mean(lf[m]) for m in ms],[np.mean(lm[m]) for m in ms])[0,1].round(2))
