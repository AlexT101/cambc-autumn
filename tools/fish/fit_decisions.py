"""Fit bounded, interpretable surrogates on inspected data only; never run on confirmation."""
import argparse
import collections
import gzip
import itertools
import json
from pathlib import Path

from breadth import RANGED
from decision_model import destination, features, lower_holder


def fit_tree(rows, depth=3, min_leaf=60):
    positives=sum(y for _,y in rows); n=len(rows)
    leaf=dict(prediction=positives > n/2, count=n, positive=positives)
    if not depth or n < 2*min_leaf or positives in (0,n):
        return leaf
    best=None
    for feature in rows[0][0]:
        ordered=sorted((x[feature],y) for x,y in rows)
        left=0
        for i,(value,y) in enumerate(ordered[:-1],1):
            left+=y
            if i < min_leaf or n-i < min_leaf or value==ordered[i][0]:
                continue
            # Weighted Gini, with deterministic feature/threshold tie breaking.
            loss=left*(i-left)/i+(positives-left)*(n-i-positives+left)/(n-i)
            choice=(loss,feature,value)
            if best is None or choice < best:
                best=choice
    if best is None or best[0] >= positives*(n-positives)/n:
        return leaf
    _,feature,threshold=best
    a=[r for r in rows if r[0][feature]<=threshold]; b=[r for r in rows if r[0][feature]>threshold]
    return dict(feature=feature,threshold=threshold,count=n,positive=positives,
                left=fit_tree(a,depth-1,min_leaf),right=fit_tree(b,depth-1,min_leaf))


def main(source,out):
    data=collections.defaultdict(list)
    with gzip.open(source,'rt') as f:
        for line in f:
            r=json.loads(line);k=r['kind'];x=r['x'];y=r['y']
            if k=='destination':
                if x['reason']!='opening' and y['status']=='hit':
                    data[k].append((x,y['targets'][0]))
                continue
            if k=='holder' and not lower_holder(x):continue
            if k=='enemy_attack' and x['type'] not in RANGED:continue
            label={'holder':'left','recall_final':'keep','enemy_attack':'attack','heal':'cast','damage_spell':'cast'}[k]
            data[k].append((features(k,x),y[label]))
    fitted={k:fit_tree(v) for k,v in data.items() if k!='destination'}
    candidates=[]
    for pars in itertools.product([0.25,1,4],[50,200,800],[0,1,3],[0,1]):
        correct=sum(destination(x,pars)==y for x,y in data['destination'])
        candidates.append((correct,pars))
    candidates.sort(reverse=True)
    fitted['destination']=candidates[0][1]
    Path(out).write_text(json.dumps(fitted,indent=2)+'\n')
    sweep=Path(out).with_suffix('.sweep.json')
    sweep.write_text(json.dumps(dict(source=source,counts={k:len(v) for k,v in data.items()},
                                    destination_grid=candidates),indent=2)+'\n')
    print(json.dumps(fitted,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('out')
    a=p.parse_args();main(a.source,a.out)
