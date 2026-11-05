"""Evaluate frozen action, holder, recall and new-destination hypotheses; retain every error."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

from breadth import RANGED
from decision_model import lower_holder, predict


def main(source, fitted_path, out):
    fitted=json.loads(Path(fitted_path).read_text())
    metrics={}; counts=collections.Counter(); outcomes=collections.Counter(); destinations=collections.Counter()
    error_path=Path(out).with_suffix('.errors.jsonl.gz')
    with gzip.open(error_path,'wt') as errors, gzip.open(source,'rt') as f:
        def check(name, row, predicted, actual, baselines, eligible=True):
            if not eligible:return
            m=metrics.setdefault(name,dict(opportunities=0,predicted=0,correct=0,positive=0,confusion=collections.Counter(),
                                          baselines=collections.Counter(),games=collections.defaultdict(lambda:[0,0])))
            m['opportunities']+=1
            if predicted is None:return
            m['predicted']+=1; m['correct']+=predicted==actual
            if isinstance(actual,bool):
                m['positive']+=actual
                m['confusion'][f'{int(actual)}->{int(predicted)}']+=1
            for k,v in baselines.items():m['baselines'][k]+=v==actual
            m['games'][row['game']][0]+=predicted==actual; m['games'][row['game']][1]+=1
            if predicted!=actual:
                errors.write(json.dumps(dict(metric=name,predicted=predicted,actual=actual,observation=row),separators=(',',':'))+'\n')

        for line in f:
            row=json.loads(line); kind=row['kind'];x=row['x'];y=row['y'];counts[kind]+=1
            if kind=='destination':
                destinations[x['reason']+':'+y['status']]+=1
                if x['reason']=='opening' or y['status']!='hit':continue
                actual=y['targets'][0]
                new=[c for c in x['candidates'] if c['id'] != x['own_group']] or x['candidates']
                baselines=dict(nearest_new=min(new,key=lambda c:(c['walk'],c['id']))['id'])
                for model in ('destination','destination_ready'):
                    p=predict(model,x,fitted)
                    check(model,row,p,actual,baselines)
                    check(model+'/'+x['reason'],row,p,actual,baselines)
                continue
            target={'holder':'left','recall_final':'keep','enemy_attack':'attack','heal':'cast','damage_spell':'cast'}[kind]
            actual=y[target];baselines=dict(always_yes=True,always_no=False)
            p=predict(kind,x,fitted)
            check(kind,row,p,actual,baselines)
            check(kind+'/type_'+str(x['type']),row,p,actual,baselines)
            if kind=='enemy_attack':
                p=predict('melee_attack',x,fitted)
                check('melee_attack',row,p,actual,baselines)
                check('melee_attack_first',row,p,y['first']=='Attack',baselines)
            if kind=='heal':
                p=predict('heal_any_injury',x,fitted)
                check('heal_any_injury',row,p,actual,baselines)
                check('heal_injured_only',row,predict(kind,x,fitted),actual,baselines,eligible=p)
                missing=max(c['maxHp']-c['hp'] for c in x['allies'])
                check('heal_small_injury',row,p,actual,baselines,eligible=0 < missing <= 20)
            if kind=='holder':
                check('holder_wait',row,predict('holder_wait',x,fitted),actual,baselines,eligible=lower_holder(x))
                check('solo_holder_leave',row,False,actual,baselines,eligible=not x['holders'])
            if kind=='recall_final':
                outcomes[y['outcome']]+=1
                for model in ('recall_capture','recall_lowhp'):
                    check(model,row,predict(model,x,fitted),actual,baselines)
                if y['outcome']!='censored':
                    check('recall_arrival',row,p,y['outcome']=='arrive',baselines)
    for m in metrics.values():
        m['accuracy']=m['correct']/m['predicted'] if m['predicted'] else None
        m['coverage']=m['predicted']/m['opportunities'] if m['opportunities'] else None
        m['game_mean_accuracy']=sum(a/b for a,b in m['games'].values())/len(m['games']) if m['games'] else None
    result=dict(source=source,source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                fitted_sha256=hashlib.sha256(Path(fitted_path).read_bytes()).hexdigest(),
                model_sha256=hashlib.sha256(Path('tools/fish/decision_model.py').read_bytes()).hexdigest(),
                counts=counts,destination_outcomes=destinations,recall_outcomes=outcomes,metrics=metrics)
    Path(out).write_text(json.dumps(result,indent=2)+'\n')
    for k,m in metrics.items():
        if '/' not in k:print(k,m['correct'],m['predicted'],m['accuracy'], 'coverage',m['coverage'],dict(m['baselines']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source');p.add_argument('fitted');p.add_argument('out')
    a=p.parse_args();main(a.source,a.fitted,a.out)
