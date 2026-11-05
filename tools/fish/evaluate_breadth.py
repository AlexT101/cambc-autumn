"""Evaluate frozen farming/stun hypotheses and the Prism necessary condition."""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
from farm_model import camp_target,opening_target
from tactical_model import cassi_stun_target,prism_bank_ready


def main(features,out,altar_cache=None):
    with gzip.open(features) as f:data=json.load(f)
    counts=collections.defaultdict(lambda:[0,0]);per_game=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]));errors=[]
    def add(metric,row,predicted,actual):
        ok=predicted==actual
        counts[metric][0]+=ok;counts[metric][1]+=1
        per_game[row['game']][metric][0]+=ok;per_game[row['game']][metric][1]+=1
        if not ok:errors.append(dict(metric=metric,predicted=predicted,actual=actual,observation=row))
    for r in data['rows']['camp_attack']:
        cs=r['candidates'];previous=r['previous_group'];pred=camp_target(cs,previous)
        actual=r['target'];target=next((c for c in cs if c['id']==actual),None)
        chosen=next(c for c in cs if c['id']==pred)
        add('camp_all',r,pred,actual)
        if len(cs)>1:
            add('camp_multiple_targets',r,pred,actual)
            add('baseline_hp_id',r,min(cs,key=lambda c:(c['hp'],c['id']))['id'],actual)
            add('baseline_hp_yx',r,camp_target(cs),actual)
            if len({c['group'] for c in cs})==1:
                add('camp_one_group_multiple_targets',r,pred,actual)
            else:
                add('camp_multiple_groups_target',r,pred,actual)
                add('camp_multiple_groups_group',r,chosen['group'],target['group'] if target else None)
                if any(c['group']==previous for c in cs):
                    add('camp_previous_group_available',r,chosen['group'],target['group'] if target else None)
                else:
                    add('camp_previous_group_unavailable',r,chosen['group'],target['group'] if target else None)
    for r in data['rows']['opening']:
        if len(r['targets'])!=1 or r['enemies_before_hit'] or r['round']>60:continue
        cs=r['candidates'];actual=r['targets'][0]
        add('opening_rate',r,opening_target(cs),actual)
        add('opening_nearest_walk',r,min(cs,key=lambda c:(c['walk'],c['id']))['id'],actual)
    for r in data['rows']['unit_spell']:
        if r['type']!=3 or r['slot']!=1:continue
        pred=cassi_stun_target(r['candidates'])
        if pred is None:continue
        add('cassi_stun_all',r,pred,r['target'])
        if len(r['candidates'])>1:
            add('cassi_stun_multiple_visible',r,pred,r['target'])
            add('cassi_stun_baseline_hp',r,min(r['candidates'],key=lambda c:(c['hp'],c['id']))['id'],r['target'])
        cs=[c for c in r['candidates'] if c['type']!=7 and not any(b['type']==1 and b['timer']>0 for b in c['buffs'])]
        if len(cs)>1:add('cassi_stun_multiple_eligible',r,pred,r['target'])
    for r in data['rows']['bank']:
        if r['type']!=6:continue
        ready=prism_bank_ready(r['me'],r['score'],r['allies'])
        if r['attempted']:add('prism_starts_satisfy_gate',r,ready,True)
        if not ready:add('prism_gate_predicts_refusal',r,False,r['attempted'])
        # This deliberately tests (and can refute) treating the gate as a full trigger.
        add('prism_gate_as_full_trigger',r,ready,r['attempted'])
    if altar_cache:
        context={}
        for p in Path(altar_cache).glob('*.json'):
            d=json.loads(p.read_text())
            for r in d['rows']:context[d['game'],r['round'],r['actor']]=dict(r,side=d['side'])
        for r in data['rows']['bank']:
            c=context[r['game'],r['round'],r['actor']]
            locked=all(any(l['team']!=c['side'] and [l['x'],l['y']]==p for l in c['locks']) for p in c['altars'])
            if locked:
                add('locked_altar_refusal',r,False,r['attempted'])
                if r['me']['roundFlags'] & 2:
                    add('locked_altar_refusal_attack_ready',r,False,r['attempted'])
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('breadth.py'),Path(__file__).with_name('farm_model.py'),Path(__file__).with_name('tactical_model.py')]}
    result=dict(features=features,games=data['games'],counts=data['counts'],hashes=hashes,
                metrics={k:dict(correct=v[0],total=v[1],accuracy=v[0]/v[1]) for k,v in counts.items()},per_game=per_game)
    Path(out).write_text(json.dumps(result,indent=2)+'\n')
    with gzip.open(str(Path(out).with_suffix('.errors.json.gz')),'wt') as f:json.dump(errors,f,separators=(',',':'))
    print(json.dumps(result['metrics'],indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('features');p.add_argument('out');p.add_argument('--altar-cache')
    a=p.parse_args();main(a.features,a.out,a.altar_cache)
