import json,sys,collections,gzip
from pathlib import Path
E=collections.defaultdict(list)
for d in Path(sys.argv[1]).iterdir():
    if not (d/'meta.json').exists(): continue
    m=json.loads((d/'meta.json').read_text()); n=m['result']['rounds']
    R=json.load(gzip.open(d/'rounds.json.gz'))
    for c,rc in zip(m['champions'],R['champions']):
        s=c['stats']
        i=min(len(rc['gold'])-1,299)
        E[c['name']].append((s['earnedGold'],s.get('spentGold',0),c['gold'],n,s['collectedGems'],rc['earned'][i],rc['gold'][i]))
print(f"{'type':14s} {'n':>5s} {'earned':>7s} {'spent':>6s} {'unspent':>7s} {'earn/100r':>9s} {'gems':>5s} {'earned@300':>10s} {'held@300':>8s}")
for k,v in sorted(E.items(),key=lambda kv:-len(kv[1])):
    m=len(v)
    print(f"{k:14s} {m:5d} {sum(x[0] for x in v)/m:7.0f} {sum(x[1] for x in v)/m:6.0f} {sum(x[2] for x in v)/m:7.0f} {100*sum(x[0]/x[3] for x in v)/m:9.0f} {sum(x[4] for x in v)/m:5.0f} {sum(x[5] for x in v)/m:10.0f} {sum(x[6] for x in v)/m:8.0f}")
