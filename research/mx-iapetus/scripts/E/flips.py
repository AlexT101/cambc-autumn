# Paired results of two train batches (CAND is bot 0 in both): flips by map family and by game length.
import json,glob,collections,re,sys
def load(n):
    d=json.load(open(glob.glob(f'replays/batch-*{n}-train/results.json')[0]))
    out={}
    for x in d['matches']:
        key=(x['map'].split('/')[-1],tuple(x['order']))
        cand_side=x['order'].index(0)
        out[key]=(int(x['winner']==0) if x['winner'] in (0,1) else 0.5, x['rounds'])
    return out
a=load(sys.argv[1]); b=load(sys.argv[2])
keys=sorted(set(a)&set(b))
fam=collections.defaultdict(lambda:[0,0,0]); L=collections.defaultdict(lambda:[0,0,0])
for k in keys:
    f=re.sub(r'-\d+\.map26a$','',k[0])
    wa,ra=a[k]; wb,rb=b[k]
    for D,g in ((fam,f),(L,'<400' if ra<400 else '<800' if ra<800 else '<1500' if ra<1500 else '1500+')):
        D[g][0]+=1; D[g][1]+=wa; D[g][2]+=wb
print('games',len(keys),'A %.3f B %.3f'%(sum(a[k][0] for k in keys)/len(keys),sum(b[k][0] for k in keys)/len(keys)))
for D in (fam,L):
    for g,(n,x,y) in sorted(D.items(),key=lambda t:-t[1][0]): print('%-28s n=%5d A %.3f B %.3f d %+.3f'%(g,n,x/n,y/n,(y-x)/n))
