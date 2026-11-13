import json,gzip,collections,os
A='/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
idx=json.load(open(A+'index.json'))['games']
C=collections.Counter(); T=0
for d in sorted({r["dir"] for r in idx})[:400]:
    m=json.load(open(A+d+'/meta.json')); team={c['id']:c['team'] for c in m['champions']}
    R=json.load(gzip.open(A+d+'/rounds.json.gz'))
    ch=R['champions']; n=len(R['round'])
    for t in (0,1):
        ids=[c for c in ch if int(c['team'])==t]
        for i in range(n):
            k=sum(1 for c in ids if not c['alive'][i]); C[k]+=1; T+=1
print({k:'%.3f'%(v/T) for k,v in sorted(C.items())})
