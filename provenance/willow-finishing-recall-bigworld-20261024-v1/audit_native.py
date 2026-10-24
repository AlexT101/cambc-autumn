#!/usr/bin/env python3
import gzip,json,collections,hashlib
from pathlib import Path
base=Path('provenance/willow-finishing-recall-bigworld-20261024-v1/extracted/bcddd6777bd59929')
meta=json.loads((base/'meta.json').read_text())
rounds=json.load(gzip.open(base/'rounds.json.gz','rt'))
champions=[]
for c in rounds['champions']:
    counts=collections.Counter(c['turn'])
    champions.append({'id':c['id'],'team':c['team'],'name':meta['champions'][c['id']]['name'],
      'native_turn_rollovers':counts.get(6,0),'native_bot_errors':counts.get(7,0),
      'turn_status_counts':{str(k):v for k,v in sorted(counts.items()) if v},
      'final':{'alive':bool(c['alive'][-1]),'position':[c['x'][-1],c['y'][-1]],'hp':c['hp'][-1], 'gems':c['gems'][-1], 'channel_type':c['chan'][-1], 'channel_time':c['chanT'][-1]}})
relevant=[]; recall_counts=collections.Counter(); causes=collections.Counter(); p_actions=[]
for line in gzip.open(base/'events.jsonl.gz','rt'):
    e=json.loads(line)
    if e.get('a')==5:
        k=e.get('k')
        if k in ('recall_start','recall_cancel','recall_end'):
            recall_counts[k]+=1
            if k=='recall_cancel': causes[e.get('cause','?')]+=1
            if e.get('r',0) in range(735,742) or e.get('r',0)>=868: relevant.append(e)
        if k in ('move','attack','cast','recall_start','recall_cancel','recall_end','tribute_start','tribute_end','death','respawn') and (e.get('r',0) in range(735,742) or e.get('r',0)>=868): p_actions.append(e)
res={
 'schema':'finishing-recall-native-audit/v1','source_bundle_sha256':hashlib.sha256(Path('provenance/willow-finishing-recall-bigworld-20261024-v1/outputs/finishing-recall-B-vs-v33-big-world.repl26a').read_bytes()).hexdigest(),
 'validation':meta['validation'],'result':meta['result'],'draft':meta['draft']['picks'],'champions':champions,
 'native_status_totals':{'team_a_rollovers':sum(c['native_turn_rollovers'] for c in champions if c['team']==0),'team_b_rollovers':sum(c['native_turn_rollovers'] for c in champions if c['team']==1),'team_a_errors':sum(c['native_bot_errors'] for c in champions if c['team']==0),'team_b_errors':sum(c['native_bot_errors'] for c in champions if c['team']==1)},
 'candidate_prism':{'actor_id':5,'name':'Prism','deaths':meta['champions'][5]['deaths'],'collected_gems':meta['champions'][5]['stats']['collectedGems'],'submitted_gems':meta['champions'][5]['stats']['submittedGems'],'champion_damage_done':meta['champions'][5]['stats']['championDamageDone'],'champion_damage_taken':meta['champions'][5]['stats']['championDamageTaken'],'recall_counts':dict(recall_counts),'recall_cancel_causes':dict(causes),'selected_events_r735_741_and_868_end':p_actions},
 'scope':'Native statuses are decoded from each champion round snapshot: turn code 6=fuel rollover, code 7=bot error. Team-level summary faults bytes are intentionally not used.'
}
Path('provenance/willow-finishing-recall-bigworld-20261024-v1/native-audit.json').write_text(json.dumps(res,indent=2)+'\n')
