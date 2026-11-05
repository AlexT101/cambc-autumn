"""Post-evaluation summaries and paired group bootstrap; does not fit predictors."""
import argparse
import collections
import gzip
import json
import random
from pathlib import Path


def main(manifest,results,out):
    entries=json.loads(Path(manifest).read_text());j=json.loads(Path(results).read_text())
    groups=collections.defaultdict(list)
    for e in entries:groups[e['group']].append(e['sha256'][:16])
    comparisons={}
    for candidate,baseline in [('route/fitted','route/ready'),('incoming','incoming/rank'),
                               ('incoming_settled','incoming_settled/rank'),('trip','trip/always_farm')]:
        a=j['metrics'][candidate];b=j['metrics'][baseline];counts=[]
        for keys in groups.values():
            num=den=0
            for k in keys:
                ac,an=a['games'].get(k,[0,0]);bc,bn=b['games'].get(k,[0,0]);assert an==bn
                num+=ac-bc;den+=an
            counts.append((num,den))
        rng=random.Random(42);samples=[]
        for _ in range(10000):
            selected=rng.choices(counts,k=len(counts));d=sum(n for _,n in selected)
            if d:samples.append(sum(v for v,_ in selected)/d)
        samples.sort()
        comparisons[candidate]=dict(baseline=baseline,delta=a['accuracy']-b['accuracy'],
            group_bootstrap_95=[samples[int(len(samples)*.025)],samples[int(len(samples)*.975)]],
            group_counts=counts)
    examples=[];seen=collections.Counter()
    wanted={'route/fitted','incoming','incoming_settled','early_home','trip/payout'}
    with gzip.open(Path(results).with_suffix('.errors.jsonl.gz'),'rt') as f:
        for line in f:
            r=json.loads(line);metric=r['metric']
            if metric not in wanted:continue
            key=(metric,str(r['actual']),str(r['predicted'])) if metric!='route/fitted' else (metric,)
            if seen[key] < (3 if metric=='route/fitted' else 1):examples.append(r);seen[key]+=1
    with Path(out).open('x') as f:
        json.dump(dict(groups=len(groups),comparisons=comparisons,examples=examples,
            note='Percentile paired bootstrap resamples ten match groups, not individual turns. Small-cluster interval is descriptive. All examples are failures of the frozen predictors.'),f,indent=2);f.write('\n')
    print(json.dumps(comparisons,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('manifest','results','out'):p.add_argument(a)
    a=p.parse_args();main(a.manifest,a.results,a.out)
