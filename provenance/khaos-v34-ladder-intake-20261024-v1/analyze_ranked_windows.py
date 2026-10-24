from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]; ART=Path(__file__).resolve().parent
TEAM='547efb5b-57e5-4355-8501-3b331f506d62'; SUB='2026-10-24T10:17:24Z'; CUTOFF=datetime.fromisoformat(SUB.replace('Z','+00:00'))
SRC=[
 'provenance/astraeus-regression-history-intake-20261024-v1/raw/ranked-first100.json',
 'provenance/astraeus-regression-history-refresh-20261024-v2/ranked-first30.json',
 'provenance/khaos-v34-ladder-intake-20261024-v1/raw/ranked-latest30.stdout.json']
byid={}; pins=[]
for rel in SRC:
 b=(ROOT/rel).read_bytes(); d=json.loads(b); pins.append({'path':rel,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'rows':len(d.get('matches',[]))})
 for m in d.get('matches',[]):
  teams=m.get('teams',[]); own=next((t for t in teams if t.get('teamId')==TEAM),None)
  if not own: continue
  opp=next(t for t in teams if t is not own)
  picks=own.get('draftPicks') or []
  e={'match_id':m['matchId'],'group_id':m.get('groupId'),'position':m.get('position'),'created_at':m.get('createdAt'),'finished_at':m.get('finishedAt'),'status':m.get('status'),'map':m.get('map'),'kind':m.get('kind'),'our_side':own.get('side'),'result':own.get('result'),'our_draft':picks,'our_first_pick':picks[0] if picks else None,'opponent_id':opp.get('teamId'),'opponent':opp.get('name'),'opponent_draft':opp.get('draftPicks')}
  old=byid.get(e['match_id'])
  if old is None or (e['status']=='finished' and old['status']!='finished'): byid[e['match_id']]=e
rows=list(byid.values())
for e in rows:
 c=datetime.fromisoformat(e['created_at'].replace('Z','+00:00')) if e.get('created_at') else None
 f=datetime.fromisoformat(e['finished_at'].replace('Z','+00:00')) if e.get('finished_at') else None
 e['created_post']=bool(c and c>CUTOFF); e['finished_post']=bool(f and f>CUTOFF); e['straddles']=bool(c and f and c<=CUTOFF<f)
 e['eligibility']='excluded_willow_first' if e['our_first_pick']==7 else 'eligible' if e['our_first_pick'] is not None else 'unknown_first_pick'
finished=[e for e in rows if e['status']=='finished' and e['result'] in ('win','loss')]
eligible=[e for e in finished if e['eligibility']=='eligible']
def summ(seq):
 c=Counter(x['result'] for x in seq); return {'n':len(seq),'wins':c['win'],'losses':c['loss'],'latest_created':max((x['created_at'] for x in seq if x['created_at']),default=None),'latest_finished':max((x['finished_at'] for x in seq if x['finished_at']),default=None)}
pre=[e for e in eligible if not e['created_post'] and not e['finished_post']]
post=[e for e in eligible if e['created_post'] and e['finished_post']]
straddles=[e for e in eligible if e['straddles']]
# Latest-30 cohort separate; API result includes only this snapshot, not a continuous feed.
latest_ids={e['matchId'] for e in json.loads((ROOT/SRC[-1]).read_text())['matches']}
latest=[e for e in eligible if e['match_id'] in latest_ids]
latest_post=[e for e in latest if e['created_post'] and e['finished_post']]
# Map/opponent/our-side cells compared across the cutoff. Keep both sample counts and ordered drafts.
grp=lambda seq: defaultdict(list)
precells=grp(pre); postcells=grp(post)
for seq, out in [(pre,precells),(post,postcells)]:
 for e in seq: out[(e['kind'],e['map'],e['opponent_id'],e['our_side'])].append(e)
matched=[]
for k in sorted(set(precells)&set(postcells)):
 a,b=precells[k],postcells[k]
 matched.append({'kind':k[0],'map':k[1],'opponent_id':k[2],'opponent':(a+b)[0]['opponent'],'our_side':k[3],
  'pre':summ(a),'post':summ(b),'pre_ids':[x['match_id'] for x in a],'post_ids':[x['match_id'] for x in b],
  'pre_drafts':[x['our_draft'] for x in a],'post_drafts':[x['our_draft'] for x in b],
  'pre_opponent_drafts':[x['opponent_draft'] for x in a],'post_opponent_drafts':[x['opponent_draft'] for x in b]})
# Outcome matrix only ranked, eligible, and grouped by map/opponent/side.
matrix=[]
for k, vals in sorted(precells.items(), key=lambda kv:(-len(kv[1]),kv[0])):
 matrix.append({'period':'pre','kind':k[0],'map':k[1],'opponent_id':k[2],'opponent':vals[0]['opponent'],'our_side':k[3],**summ(vals),'match_ids':[x['match_id'] for x in vals]})
for k, vals in sorted(postcells.items(), key=lambda kv:(-len(kv[1]),kv[0])):
 matrix.append({'period':'post_provisional','kind':k[0],'map':k[1],'opponent_id':k[2],'opponent':vals[0]['opponent'],'our_side':k[3],**summ(vals),'match_ids':[x['match_id'] for x in vals]})
# Concrete metadata-only review candidates: latest loss per post group/opponent cohort, no replay downloaded.
losses=[e for e in latest_post if e['result']=='loss']
latest_groups=[]
for e in sorted(losses,key=lambda x:x['created_at'],reverse=True):
 if not any(x['opponent_id']==e['opponent_id'] and x['group_id']==e['group_id'] for x in latest_groups): latest_groups.append(e)
selected=[]
for e in latest_groups:
 selected.append(e)
 if len(selected)==3: break
result={'schema':'ranked-v48-history-windows/v1','team_id':TEAM,'submission_boundary_utc':SUB,'version_identity':'Server version48 is the known submission event; match list payload has no submission ID/version, so post-cutoff cohorts are provisional only.',
 'own_willow_first_rule':'All rows where our ordered first pick is7 are excluded from outcomes. No version is inferred from draft, map, group, or timestamp.',
 'input_pins':pins,'deduplicated_rows':len(rows),'finished_all_ranked':summ(finished),'finished_willow_first_excluded':summ([e for e in finished if e['eligibility']=='excluded_willow_first']),
 'finished_eligible_non_willow_first':summ(eligible),'pre_cutoff_eligible':summ(pre),'post_cutoff_eligible_provisional':summ(post),'straddling_eligible':summ(straddles),
 'latest30_snapshot_all_finished':summ([e for e in latest if e['status']=='finished']),'latest30_non_willow_first':summ(latest),'latest30_post_cutoff_provisional':summ(latest_post),
 'matched_map_opponent_side_cells':matched,'matrix':matrix,'review_candidates_metadata_only':[{'match_id':e['match_id'],'map':e['map'],'our_side':e['our_side'],'result':e['result'],'created_at':e['created_at'],'finished_at':e['finished_at'],'our_draft':e['our_draft'],'opponent':e['opponent'],'opponent_id':e['opponent_id'],'opponent_draft':e['opponent_draft']} for e in selected],
 'rows':rows}
(ART/'ranked-window-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
# simple CSV
import csv
with (ART/'ranked-map-opponent-side.csv').open('w',newline='') as f:
 w=csv.writer(f); w.writerow(['period','kind','map','opponent_id','opponent','our_side','n','wins','losses','latest_created','latest_finished','match_ids'])
 for x in matrix:w.writerow([x[k] for k in ('period','kind','map','opponent_id','opponent','our_side','n','wins','losses','latest_created','latest_finished')]+[';'.join(x['match_ids'])])
print(json.dumps({k:result[k] for k in ('finished_all_ranked','finished_willow_first_excluded','finished_eligible_non_willow_first','pre_cutoff_eligible','post_cutoff_eligible_provisional','straddling_eligible','latest30_snapshot_all_finished','latest30_non_willow_first','latest30_post_cutoff_provisional','matched_map_opponent_side_cells','review_candidates_metadata_only')},indent=2))
