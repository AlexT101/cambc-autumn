"""oofcount.py TAG...: play turns after round 1 that used the whole 100k (ran out), from the .fuel traces (bench json)."""
import json,sys
for t in sys.argv[1:]:
    d=json.load(open(f'/home/ubuntu/tmp-offload/nooof/{t}.json'))
    n=sum(sum(1 for x in g['play'][g['bodies']:] if x>=100000) for g in d['games'])
    turns=sum(len(g['play'])-g['bodies'] for g in d['games'])
    r1=sum(sum(1 for x in g['play'][:g['bodies']] if x>=200000) for g in d['games'])
    print(f"{t}: {n} of {turns} play turns ran out ({1000*n/turns:.3f} per 1k); round 1 at 200k: {r1}; games {len(d['games'])}")
