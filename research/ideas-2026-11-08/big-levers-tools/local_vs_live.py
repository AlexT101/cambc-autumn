# Per ladder map: ocean (own draft) vs panel members locally against v86-89 scrims vs Fish+Mite.
import json,collections,numpy as np,glob,os
loc=collections.defaultdict(list)
# The panel-td runs (oc-base27 vs gp-panel-{astraeus,proteus}-td); their replays/ab summaries were overwritten later.
for b in ('replays/batch-20261108-163752-ab-bigl-ladder-astraeus-ladder','replays/batch-20261108-163752-ab-bigl-ladder-proteus-ladder'):
    r=json.load(open(b+'/results.json'))
    for m in r['matches']:
        mp=os.path.basename(m['map']).replace('.map26a','')
        loc[mp].append(m['winner']==0)
G=[json.loads(l) for l in open('research/ladder-scrims-2026-11-06/data/games.jsonl')]
G=[g for g in G if g.get('status')=='finished' and g['version']>=86 and g['opp_name'] in ('Intercontinental Fish','Mite')]
live=collections.defaultdict(list)
for g in G: live[g['map']].append(g['result']=='win')
ms=[m for m in live if m in loc]; print(len(ms),'maps matched of',len(live))
L=np.array([np.mean(live[m]) for m in ms]); Lo=np.array([np.mean(loc[m]) for m in ms])
print('corr live vs local',np.corrcoef(L,Lo)[0,1].round(2),' mean live',L.mean().round(3),'local',Lo.mean().round(3))
bad=[m for m in ms if np.mean(live[m])<=0.25]
print('live <=25% maps:',len(bad),'their local win%:',np.mean([np.mean(loc[m]) for m in bad]).round(2))
for m in sorted(bad,key=lambda m:np.mean(live[m])): print(f'  {m:22s} live {np.mean(live[m]):.2f} local {np.mean(loc[m]):.2f} ({len(loc[m])})')
good=[m for m in ms if np.mean(live[m])>=0.9]; print('live >=90% maps local:',np.mean([np.mean(loc[m]) for m in good]).round(2), len(good))
# local-bad maps
lb=[m for m in ms if np.mean(loc[m])<=0.25]; print('local<=25%:',[(m,round(np.mean(live[m]),2)) for m in lb])
