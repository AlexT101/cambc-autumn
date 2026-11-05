"""Evaluate frozen hypotheses, recording coverage, confusion and every failure."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
from routes_model import features,predict,route,tree


def main(source,model,out):
    fit=json.loads(Path(model).read_text());metrics={};counts=collections.Counter();outcomes=collections.Counter()
    with gzip.open(Path(out).with_suffix('.errors.jsonl.gz'),'xt') as errors:
        def check(name,r,p,y):
            m=metrics.setdefault(name,dict(n=0,correct=0,actual=collections.Counter(),
                confusion=collections.Counter(),games=collections.defaultdict(lambda:[0,0])))
            m['n']+=1;m['correct']+=p==y;m['actual'][str(y)]+=1
            m['confusion'][str(y)+'->'+str(p)]+=1
            m['games'][r['game']][0]+=p==y;m['games'][r['game']][1]+=1
            if p!=y:errors.write(json.dumps(dict(metric=name,predicted=p,actual=y,observation=r),separators=(',',':'))+'\n')
        with gzip.open(source,'rt') as f:
            for line in f:
                r=json.loads(line);k=r['kind'];x=r['x'];y=r['y'];counts[k]+=1
                if k=='route':
                    outcomes['route/'+x['reason']+'/'+y['status']]+=1
                    if x['reason']=='opening' or y['status']!='hit':continue
                    for mode in ('ready','known','visited','home_side','repeat','fitted'):
                        p=route(x,mode,fit['route']);actual=y['targets'][0]
                        check('route/'+mode,r,p,actual);check('route/'+mode+'/'+x['reason'],r,p,actual)
                        if any(c['route_count'] for c in x['candidates']):check('route/'+mode+'/prior_transition',r,p,actual)
                elif k=='trip':
                    outcomes['trip/'+x['reason']+'/'+y['status']]+=1
                    if x['reason']=='opening' or y['status'] not in ('farm','home','tribute'):continue
                    p=predict(k,x,fit);check(k,r,p,y['status']);check(k+'/'+x['reason'],r,p,y['status'])
                    check('trip/always_farm',r,'farm',y['status'])
                    check('trip/home_binary',r,p=='home',y['status']=='home')
                    check('trip/tribute_binary',r,p=='tribute',y['status']=='tribute')
                elif k=='early_home':
                    outcomes[k+'/'+y['outcome']]+=1
                    if y['outcome']=='censored':continue
                    p=predict(k,x,fit);actual=y['outcome']=='arrive';check(k,r,p,actual)
                    check(k+'/always_cancel',r,False,actual)
                    check(k+'/low_health',r,x['hp']/x['maxhp']<=.4,actual)
                    if x['hp']/x['maxhp']<=.4:check(k+'/injured_subset',r,p,actual)
                elif k=='incoming':
                    p=predict(k,x,fit);actual=y['joined'];check(k,r,p,actual)
                    check(k+'/rank',r,x['self_rank']<x['best_rank'],actual)
                    check(k+'/never_join',r,False,actual)
                    check(k+('/better_rank' if x['self_rank']<x['best_rank'] else '/worse_rank'),r,p,actual)
                    if y['settled'] is not None:
                        p=tree(fit['incoming_settled'],features(k,x));actual=y['settled']
                        check('incoming_settled',r,p,actual)
                        check('incoming_settled/rank',r,x['self_rank']<x['best_rank'],actual)
                        check('incoming_settled/never_join',r,False,actual)
                        if y['joined']:check('incoming_settled/among_entries',r,p,actual)
    for m in metrics.values():
        m['accuracy']=m['correct']/m['n']
        m['game_mean_accuracy']=sum(a/b for a,b in m['games'].values())/len(m['games'])
    hashes={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [source,model,'tools/fish/routes_model.py']}
    with Path(out).open('x') as f:json.dump(dict(hashes=hashes,counts=counts,outcomes=outcomes,metrics=metrics),f,indent=2);f.write('\n')
    for k,m in metrics.items():
        if k.count('/')<=1:print(k,m['correct'],m['n'],round(m['accuracy'],4))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('source','model','out'):p.add_argument(a)
    a=p.parse_args();main(a.source,a.model,a.out)
