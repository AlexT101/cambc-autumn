"""Retrospective endpoint audit: does an incoming champion hold through payout?

This endpoint was defined after fourth-cohort errors were inspected. It is not a
new untouched confirmation, and does not refit the frozen entry predictors.
"""
import argparse
import collections
import gzip
import json
from pathlib import Path
from breadth import static_groups,xy
from decision_data import contexts
from routes_model import features,tree


def main(manifest,cache,source,model,out):
    rows=collections.defaultdict(list)
    for line in gzip.open(source,'rt'):
        r=json.loads(line)
        if r['kind']=='incoming':rows[r['game']].append(r)
    fit=json.loads(Path(model).read_text());counts=collections.Counter();metrics={};examples=[]
    with gzip.open(Path(out).with_suffix('.rows.jsonl.gz'),'xt') as output:
        for e in json.loads(Path(manifest).read_text()):
            key=e['sha256'][:16]
            with gzip.open(Path(cache)/(key+'.json.gz')) as f:g=json.load(f)
            _,at=static_groups(g['map']);live={};actors=collections.defaultdict(list)
            for t in g['turns']:
                actors[t['id']].append(t)
                for s in contexts(t):
                    for c in s['camps']:live[at[xy(c)]]=c['group']
            indexes={t['step']:(ts,i) for ts in actors.values() for i,t in enumerate(ts)}
            for r in rows[key]:
                x=r['x'];y=r['y'];k=x['group'];turns,i=indexes[r['step']]
                status='not_entered' if not y['joined'] else 'censored'
                if y['joined']:
                    for t in turns[i+1:i+10]:
                        s=t['start'];m=s['me']
                        if t['round']>r['round']+8:break
                        if not m['alive'] or at.get(xy(m))!=k:
                            status='arrival_or_death_censored';break
                        q=next((q for q in s['groups'] if q[0]==live[k]),None)
                        if q and q[1]==3:
                            status='paid';break
                        if 'end' not in t:break
                        end=t['end']['me']
                        if not end['alive']:
                            status='arrival_or_death_censored';break
                        if at.get(xy(end))!=k:
                            status='left_before_observed_payout';break
                counts[status]+=1
                record=dict(**r,endpoint=status)
                output.write(json.dumps(record,separators=(',',':'))+'\n')
                if status not in ('paid','not_entered','left_before_observed_payout'):continue
                actual=status=='paid'
                for name,p in [('rank',x['self_rank']<x['best_rank']),
                               ('frozen_entry_tree',tree(fit['incoming_settled'],features('incoming',x))),
                               ('never_paid',False)]:
                    m=metrics.setdefault(name,dict(n=0,correct=0,confusion=collections.Counter(),games=collections.defaultdict(lambda:[0,0])))
                    m['n']+=1;m['correct']+=p==actual;m['confusion'][f'{actual}->{p}']+=1
                    m['games'][key][0]+=p==actual;m['games'][key][1]+=1
                if y['settled'] and not actual and len(examples)<10:examples.append(record)
    with Path(out).open('x') as f:json.dump(dict(counts=counts,metrics=metrics,examples=examples,
        note='Retrospective endpoint audit after fourth-cohort inspection; no new fit. Paid means observed respawning state while still standing on the same camp after continuous end-turn occupation. Arrival/death and match-end/8-round timeouts are censored, because a payout before a recall arrival may be unobserved.'),f,indent=2);f.write('\n')
    print(dict(counts));print(json.dumps(metrics,default=dict)[:1200])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('manifest','cache','source','model','out'):p.add_argument(a)
    a=p.parse_args();main(a.manifest,a.cache,a.source,a.model,a.out)
