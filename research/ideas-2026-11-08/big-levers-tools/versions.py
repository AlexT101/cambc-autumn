# Paired live deltas between scrim versions, by (map, side, opponent) cell, bootstrap CI.
import json,collections,numpy as np
G=[json.loads(l) for l in open('research/ladder-scrims-2026-11-06/data/games.jsonl')]
G=[g for g in G if g.get('status')=='finished' and g['opp_name'] in ('Intercontinental Fish','Mite')]
c=collections.defaultdict(lambda:collections.defaultdict(list))
for g in G: c[g['version']][(g['map'],g['side'],g['opp_name'])].append(g['result']=='win')
def paired(a,b,boot=4000):
    ks=[k for k in c[a] if k in c[b]]
    d=np.array([np.mean(c[b][k])-np.mean(c[a][k]) for k in ks])
    rng=np.random.default_rng(1); bs=[rng.choice(d,len(d)).mean() for _ in range(boot)]
    return len(ks),d.mean(),np.percentile(bs,2.5),np.percentile(bs,97.5)
for a,b in ((83,86),(85,86),(86,87),(87,88),(88,89),(86,89),(83,89)):
    n,m,lo,hi=paired(a,b); print(f'v{a}->v{b}: {n} cells, paired diff {100*m:+.1f} pts (CI {100*lo:+.1f}..{100*hi:+.1f})')
