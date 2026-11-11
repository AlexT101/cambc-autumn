import json,sys,collections,re
for f in sys.argv[1:]:
    r=json.load(open(f)); c=collections.Counter(); n=collections.Counter()
    for m in r['matches']:
        mp=m.get('map',''); p=re.sub(r'-\d+.*','',mp.split('/')[-1])
        if m.get('winner') is None: continue
        n[p]+=1; c[p]+= m['winner']==0
    print(f.split('/')[0][-40:], ' '.join(f'{p}:{100*c[p]/n[p]:.1f}({n[p]})' for p in sorted(n)))
