#!/usr/bin/env python3
"""Deduplicate saved own-team match-list snapshots and summarize draft-eligible outcomes."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[2]
ART = Path(__file__).resolve().parent
TEAM = '547efb5b-57e5-4355-8501-3b331f506d62'
CUTOFF = datetime.fromisoformat('2026-10-24T10:17:24+00:00')
SOURCES = [
    'provenance/astraeus-regression-history-intake-20261024-v1/raw/ranked-first100.json',
    'provenance/astraeus-regression-history-intake-20261024-v1/raw/unranked-first100.json',
    'provenance/astraeus-regression-history-refresh-20261024-v2/ranked-first30.json',
    'provenance/fish-regression-history/pantheon-page-01.json',
    'provenance/fish-regression-history/pantheon-page-02.json',
]

def dt(v):
    return datetime.fromisoformat(v.replace('Z','+00:00')) if v else None

def counts(rows):
    c=Counter()
    for r in rows:
        c[r['result']] += 1
    return dict(sorted(c.items()))

byid={}
source_info=[]
for rel in SOURCES:
    p=ROOT/rel
    if not p.exists():
        continue
    raw=p.read_bytes()
    obj=json.loads(raw)
    source_info.append({'path':rel,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'rows':len(obj.get('matches',[]))})
    for m in obj.get('matches',[]):
        teams=m.get('teams') or []
        own=[t for t in teams if t.get('teamId')==TEAM]
        if len(own)!=1:
            continue
        t=own[0]
        opp=next((x for x in teams if x.get('teamId')!=TEAM),{})
        picks=t.get('draftPicks')
        first=picks[0] if isinstance(picks,list) and picks else None
        entry={
            'match_id':m.get('matchId'),'group_id':m.get('groupId'),'position':m.get('position'),
            'kind':m.get('kind'),'status':m.get('status'),'map':m.get('map'),'map_id':m.get('mapId'),
            'created_at':m.get('createdAt'),'finished_at':m.get('finishedAt'),'end_reason':m.get('endReason'),
            'our_side':t.get('side'),'result':t.get('result'),'our_team_name':t.get('name'),
            'our_draft_picks':picks,'our_first_pick':first,'opponent_id':opp.get('teamId'),
            'opponent_name':opp.get('name'),'opponent_draft_picks':opp.get('draftPicks'),
            'source_snapshots':[rel]
        }
        mid=entry['match_id']
        if mid in byid:
            old=byid[mid]
            old['source_snapshots'].append(rel)
            # Prefer completed data over a queued snapshot; otherwise keep latest timestamps/details.
            rank=lambda x:(x['status']=='finished', bool(x['finished_at']),x['created_at'] or '')
            if rank(entry)>rank(old):
                entry['source_snapshots']=old['source_snapshots']
                byid[mid]=entry
        else:
            byid[mid]=entry

rows=sorted(byid.values(),key=lambda r:(r['created_at'] or '',r['match_id'] or ''),reverse=True)
for r in rows:
    created=dt(r['created_at']); finished=dt(r['finished_at'])
    r['timestamp_cohort']={
      'created_after_submission': bool(created and created>CUTOFF),
      'finished_after_submission': bool(finished and finished>CUTOFF),
      'created_before_finished_after': bool(created and finished and created<=CUTOFF<finished),
      'created_and_finished_before': bool(created and (finished is None or finished<=CUTOFF) and created<=CUTOFF),
    }
    r['source_version']='unknown; CLI match rows do not identify uploaded bot version'
    r['draft_filter']='excluded_willow_first' if r['our_first_pick']==7 else ('eligible' if r['our_first_pick'] is not None else 'unknown_first_pick')

finished=[r for r in rows if r['status']=='finished' and r['result'] in ('win','loss')]
eligible=[r for r in finished if r['draft_filter']=='eligible']
excluded=[r for r in finished if r['draft_filter']=='excluded_willow_first']
cohort={}
for key, test in [
 ('created_post_submission',lambda r:r['timestamp_cohort']['created_after_submission']),
 ('finished_post_submission',lambda r:r['timestamp_cohort']['finished_after_submission']),
 ('straddles_submission',lambda r:r['timestamp_cohort']['created_before_finished_after']),
 ('both_pre_submission',lambda r:r['timestamp_cohort']['created_and_finished_before']),
]:
    z=[r for r in finished if test(r)]
    cohort[key]={'rows':len(z),'outcomes':counts(z),'newest_created_at':max((r['created_at'] for r in z if r['created_at']),default=None),'newest_finished_at':max((r['finished_at'] for r in z if r['finished_at']),default=None),'eligible_not_willow_first':len([r for r in z if r['draft_filter']=='eligible'])}

matrix=defaultdict(list)
for r in eligible:
    key=(r['kind'],r['map'],r['opponent_id'],r['opponent_name'],r['our_side'])
    matrix[key].append(r)
mat=[]
for key, vals in sorted(matrix.items(), key=lambda kv:(-len(kv[1]),kv[0])):
    mat.append({'kind':key[0],'map':key[1],'opponent_id':key[2],'opponent':key[3],'our_side':key[4],
                'n':len(vals),'wins':sum(r['result']=='win' for r in vals),'losses':sum(r['result']=='loss' for r in vals),
                'match_ids':[r['match_id'] for r in vals],
                'created_range':[min(r['created_at'] for r in vals),max(r['created_at'] for r in vals)],
                'drafts':[r['our_draft_picks'] for r in vals]})

loss_candidates=[r for r in eligible if r['result']=='loss']
# Evidence-only selection score: repeated exact map/opponent/side losses; normal five-pick Prism-first rows; recency.
key_loss=Counter((r['kind'],r['map'],r['opponent_id'],r['our_side']) for r in loss_candidates)
for r in loss_candidates:
    r['_priority']=(key_loss[(r['kind'],r['map'],r['opponent_id'],r['our_side'])],
                    len(r['our_draft_picks'] or []),
                    1 if r['our_first_pick']==5 else 0,
                    r['created_at'] or '')
loss_candidates.sort(key=lambda r:r['_priority'],reverse=True)
selected=[]
seen=set()
for r in loss_candidates:
    if (r['match_id']) in seen: continue
    selected.append({k:v for k,v in r.items() if not k.startswith('_')})
    seen.add(r['match_id'])
    if len(selected)==3: break

result={
 'schema':'local-own-history-merge/v1','team_id':TEAM,'submitted_server_version':48,
 'submission_time_utc':'2026-10-24T10:17:24Z','source_identity_note':'Timestamp cohorts are provisional; CLI match rows do not include a submission/version identity. Khaos_v34 is only a known submission event, not proof that any match used it.',
 'willow_first_exclusion':'Exclude finished matches whose own ordered first draft pick is champion 7; count them separately.',
 'inputs':source_info,'deduplicated_own_rows':len(rows),'finished_rows':len(finished),'finished_outcomes':counts(finished),
 'eligible_non_willow_first_finished_rows':len(eligible),'eligible_non_willow_first_outcomes':counts(eligible),
 'excluded_willow_first_finished_rows':len(excluded),'excluded_willow_first_outcomes':counts(excluded),
 'timestamp_cohorts':cohort,
 'newest_local_created_at':max((r['created_at'] for r in rows if r['created_at']),default=None),
 'newest_local_finished_at':max((r['finished_at'] for r in rows if r['finished_at']),default=None),
 'matrix':mat,'review_candidates_no_replay_download':selected,'rows':rows
}
(ART/'local-history-merge.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('inputs','deduplicated_own_rows','finished_rows','finished_outcomes','eligible_non_willow_first_finished_rows','eligible_non_willow_first_outcomes','excluded_willow_first_finished_rows','excluded_willow_first_outcomes','timestamp_cohorts','newest_local_created_at','newest_local_finished_at')},indent=2))
print('\nTOP MATRIX')
for r in mat[:25]: print(json.dumps({k:r[k] for k in ('kind','map','opponent','our_side','n','wins','losses','match_ids')},ensure_ascii=False))
print('\nREVIEW CANDIDATES')
for r in selected: print(json.dumps({k:r[k] for k in ('match_id','kind','map','our_side','result','created_at','finished_at','our_draft_picks','opponent_id','opponent_name','opponent_draft_picks')},ensure_ascii=False))
