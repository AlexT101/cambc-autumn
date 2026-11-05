"""Fit only the inspected discovery cohort and preserve every tested route score."""
import argparse
import collections
import gzip
import itertools
import json
from pathlib import Path
from fit_decisions import fit_tree
from routes_model import features, route


def main(source,out):
    data=collections.defaultdict(list); routes=[]
    with gzip.open(source,'rt') as f:
        for line in f:
            r=json.loads(line);k=r['kind'];x=r['x'];y=r['y']
            if k=='route':
                if x['reason']!='opening' and y['status']=='hit':routes.append((x,y['targets'][0]))
            elif k=='trip':
                if x['reason']=='opening' or y['status'] not in ('home','farm','tribute'):continue
                for label in ('home','tribute'):
                    data['trip_'+label].append((features(k,x),y['status']==label))
            elif k=='early_home':
                if y['outcome']!='censored':data[k].append((features(k,x),y['outcome']=='arrive'))
            elif k=='incoming':
                data[k].append((features(k,x),y['joined']))
                if y['settled'] is not None:data['incoming_settled'].append((features(k,x),y['settled']))
    fitted={k:fit_tree(v,depth=3,min_leaf=60) for k,v in data.items()}
    sweep=[]
    for pars in itertools.product([0,4,12,32],[0,.25,1],[0,4,12,32],[0,8]):
        sweep.append((sum(route(x,'fitted',pars)==y for x,y in routes),pars))
    # Prefer smaller coefficients on an exact accuracy tie.
    sweep.sort(key=lambda z:(-z[0],z[1]));fitted['route']=sweep[0][1]
    with Path(out).open('x') as f:json.dump(fitted,f,indent=2);f.write('\n')
    with Path(out).with_suffix('.sweep.json').open('x') as f:
        json.dump(dict(source=source,counts={k:len(v) for k,v in data.items()},routes=len(routes),grid=sweep),f,indent=2)
    print('fit counts',{k:len(v) for k,v in data.items()},'route',sweep[:5],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('out')
    a=p.parse_args();main(a.source,a.out)
