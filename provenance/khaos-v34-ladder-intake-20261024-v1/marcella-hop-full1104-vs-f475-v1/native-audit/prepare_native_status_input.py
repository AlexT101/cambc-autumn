#!/usr/bin/env python3
"""Reconstruct native-status auditor input from the reviewed row manifest and per-game native statistics."""
import csv, json, pathlib, hashlib
base=pathlib.Path(__file__).resolve().parent.parent
rows=list(csv.DictReader(open(base/'ROWS.tsv'),delimiter='\t'))
bots=[rows[0]['candidate_path'], rows[0]['opponent_source_aggregate_sha256']]
# The auditor only uses bot identifiers to attribute physical sides; preserve paths already pinned in rows.
f475=rows[0]['argv_bot_b'] if rows[0]['candidate_physical_side']=='A' else rows[0]['argv_bot_a']
candidate=rows[0]['candidate_path']
bots=[candidate, f475]
matches=[]; compact=[]
for idx,r in enumerate(rows):
    stats=json.load(open(r['statistics_output']))
    outcome=stats['match']['outcome']
    if outcome not in ('teamA','teamB'):
        raise SystemExit(f"invalid outcome at row {idx+1}: {outcome}")
    a_candidate=r['candidate_physical_side']=='A'
    order=[0,1] if a_candidate else [1,0]
    matches.append({'index':idx,'order':order,'replay':r['replay_output'],'map':r['map']})
    candidate_won=(outcome=='teamA')==a_candidate
    compact.append({'order':int(r['order']),'suite':r['suite'],'map_name':r['map_name'],'map_sha256':r['map_sha256'],'candidate_physical_side':r['candidate_physical_side'],'A_source':r['A_source'],'B_source':r['B_source'],'candidate_win':candidate_won,'winner_side':'A' if outcome=='teamA' else 'B','rounds_completed':stats['match']['roundsCompleted'],'submitted_gems_A':int(next(t['submittedGems'] for t in stats['teams'] if t['team']=='teamA')),'submitted_gems_B':int(next(t['submittedGems'] for t in stats['teams'] if t['team']=='teamB')),'bot_faults':stats['diagnostics']['botFaults'],'roster':stats['roster']['champions'],'replay':r['replay_output'],'statistics':r['statistics_output']})
    if r['A_source'] not in ('marcella-hop','f475') or r['B_source'] not in ('marcella-hop','f475'):
        raise SystemExit(f"unexpected source identity row {idx+1}")
if len(matches)!=1024 or len({m['replay'] for m in matches})!=1024: raise SystemExit('expected 1024 unique matches')
out=base/'native-audit'/'input'/'results.json'
obj={'bots':bots,'scheduled':len(matches),'completed':len(matches),'matches':matches,'release':True,'source_pins':{'candidate':'709ba31a186fb1e5b27a180ac58d50a913af10cba42ccbc31151ae36c04f26f4','f475':'f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824'},'note':'Reconstructed from the preapproved 1024-row manifest and native per-game statistics after successful run-batch; replay paths are the exact declared outputs. Used only as input to audit_native_status.mjs.'}
out.write_text(json.dumps(obj,indent=2)+'\n')
(base/'native-audit'/'STATS-COMPACT.json').write_text(json.dumps({'schema':'marcella-hop-full1104-stats-compact/v1','resultSource':'native statistics plus pinned ROWS.tsv','rows':compact},indent=2)+'\n')
print(out, len(matches), 'complete', 'candidate wins',sum(x['candidate_win'] for x in compact))
