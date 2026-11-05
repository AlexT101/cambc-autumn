"""Record descriptive recall, spell baselines, camp ties and bank-threshold sweeps."""
import argparse,collections,gzip,json
from pathlib import Path
from breadth import NAMES

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('features');p.add_argument('out');p.add_argument('--altar-cache');a=p.parse_args()
with gzip.open(a.features) as f:d=json.load(f)
rows=d['rows'];out={'counts':{k:len(v) for k,v in rows.items()}}
r=rows['recall'];out['prepared_recall']=dict(opportunities=len(r),starts=sum(x['started'] for x in r),
    next_turn_cancelled=sum(x['next_cancel'] for x in r if x['started']),
    next_turn_kept=sum(x['next_channel']==1 and not x['next_cancel'] for x in r if x['started']),
    next_turn_not_recalling=sum(x['next_channel']==0 for x in r if x['started']),
    no_next_turn=sum(x['next_channel'] is None for x in r if x['started']))
out['camp_ties']={}
for same in [True,False]:
    rr=[r for r in rows['camp_attack'] if len(r['candidates'])>1 and (len({c['group'] for c in r['candidates']})==1)==same]
    results={'total':len(rr)}
    for label,fn in [('id',lambda c:(c['id'],)),('xy',lambda c:(c['x'],c['y'])),('yx',lambda c:(c['y'],c['x']))]:
        results[label]=sum(min(r['candidates'],key=lambda c:(c['hp'],)+fn(c))['id']==r['target'] for r in rr)
    out['camp_ties']['one_group' if same else 'multiple_groups']=results
out['spell_baselines']={}
for typ,slot in sorted({(r['type'],r['slot']) for r in rows['unit_spell']}):
    rr=[r for r in rows['unit_spell'] if (r['type'],r['slot'])==(typ,slot) and len(r['candidates'])>1]
    results={'total':len(rr)}
    for filt in ['all','immune','both']:
        for value in ['hp','ehp','strength']:
            correct=0
            for r in rr:
                cs=[c for c in r['candidates'] if (filt=='all' or c['type']!=7) and (filt!='both' or not any(b['type']==1 and b['timer']>0 for b in c['buffs']))] or r['candidates']
                fn=lambda c:c['hp'] if value=='hp' else c['hp']+sum(b['mag'] for b in c['buffs'] if b['type']==0) if value=='ehp' else -c['strength']
                correct+=min(cs,key=lambda c:(fn(c),c['id']))['id']==r['target']
            results[filt+'_'+value]=correct
    out['spell_baselines'][NAMES[typ]+'/'+str(slot)]=results
if a.altar_cache:
    context={}
    for p in Path(a.altar_cache).glob('*.json'):
        dd=json.loads(p.read_text())
        for r in dd['rows']:context[dd['game'],r['round'],r['actor']]=dict(r,side=dd['side'])
    unlocked=[];locked=0
    for r in rows['bank']:
        c=context[r['game'],r['round'],r['actor']]
        if all(any(l['team']!=c['side'] and [l['x'],l['y']]==p for l in c['locks']) for p in c['altars']):locked+=1
        else:unlocked.append(r)
    out['bank']={'locked_opportunities':locked,'unlocked_opportunities':len(unlocked),'successful_starts':sum(r['attempted'] for r in unlocked),'quiet_by_type':{}}
    for typ in sorted({r['type'] for r in unlocked}):
        rr=[r for r in unlocked if r['type']==typ and not r['enemies']]
        if not rr:continue
        scores=[(sum((r['me']['gems']>=n)==r['attempted'] for r in rr),n) for n in range(1,1201)]
        best=max(x[0] for x in scores)
        out['bank']['quiet_by_type'][NAMES[typ]]=dict(total=len(rr),starts=sum(r['attempted'] for r in rr),
            best_correct=best,best_thresholds=[n for score,n in scores if score==best],
            minimum_start_bag=min((r['me']['gems'] for r in rr if r['attempted']),default=None),
            maximum_declined_bag=max((r['me']['gems'] for r in rr if not r['attempted']),default=None))
Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
print(a.out)
