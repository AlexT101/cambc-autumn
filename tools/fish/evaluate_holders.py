"""Evaluate the partial holder rule, retaining both classes and abstentions."""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
from holder_model import predict_leave

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('features');p.add_argument('out');a=p.parse_args()
with gzip.open(a.features) as f:rows=json.load(f)['rows']
counts=collections.Counter();bytype=collections.defaultdict(lambda:[0,0]);pairs=collections.defaultdict(lambda:[0,0]);pergame=collections.defaultdict(lambda:[0,0]);errors=[]
for r in rows:
    counts['opportunities']+=1;counts['observed_leave' if r['left'] else 'observed_stay']+=1
    if len(r['allies'])==1:pairs[str(r['me']['type'])+','+str(r['allies'][0]['type'])][r['left']]+=1
    pred=predict_leave(r['me'],r['allies'])
    if pred is None:counts['abstain']+=1;continue
    ok=pred==r['left'];counts['predicted']+=1;counts['correct']+=ok
    bytype[r['me']['type']][0]+=ok;bytype[r['me']['type']][1]+=1
    pergame[r['game']][0]+=ok;pergame[r['game']][1]+=1
    if not ok:errors.append(dict(predicted=pred,actual=r['left'],observation=r))
model=Path(__file__).with_name('holder_model.py')
out=dict(features=a.features,counts=counts,bytype=bytype,pairs=pairs,per_game=pergame,model_sha256=hashlib.sha256(model.read_bytes()).hexdigest())
Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
with gzip.open(str(Path(a.out).with_suffix('.errors.json.gz')),'wt') as f:json.dump(errors,f,separators=(',',':'))
print(json.dumps(dict(counts=counts,bytype=bytype),indent=2))
