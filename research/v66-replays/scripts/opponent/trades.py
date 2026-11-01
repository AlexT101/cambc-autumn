# Champion damage dealt/taken per champion type and side (per opponent), from fightfeat dmg_pair.
import json, glob
from collections import defaultdict, Counter
S='replays/v66-analysis'
F=[json.load(open(p)) for p in glob.glob(S+'/opp/fightfeat/*.json')]
for o in ['Fish','Mite','UoS','PBG']:
    dealt=Counter(); taken=Counter(); games=Counter()
    for f in F:
        if f['opp']!=o: continue
        seen=set()
        for a,b,ro,v in f['dmg_pair']:
            other='them' if ro=='us' else 'us'
            dealt[(ro,a)]+=v; taken[(other,b)]+=v
    for ro in ('us','them'):
        rows=sorted({k for k in dealt if k[0]==ro}|{k for k in taken if k[0]==ro}, key=lambda k:-(dealt[k]+taken[k]))
        print(o,ro,' '.join(f"{k[1]}:{dealt[k]/1000:.0f}k/{taken[k]/1000:.0f}k={dealt[k]/max(1,taken[k]):.2f}" for k in rows if dealt[k]+taken[k]>50000))
